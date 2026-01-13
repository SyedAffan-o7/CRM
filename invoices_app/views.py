from decimal import Decimal
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from customers_app.models import Contact
from leads_app.models import Lead, LeadProduct

from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('contact', 'created_by').order_by('-created_at')
    search = request.GET.get('search', '').strip()
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search)
            | Q(contact__full_name__icontains=search)
        )
    paginator = Paginator(invoices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    return render(request, 'invoices_app/invoice_list.html', context)


def _ensure_contacts_for_leads() -> None:
    """Ensure every lead with a phone number has a linked Contact.

    This mirrors the auto-create logic in leads_app when enquiries are created/edited,
    but also backfills older enquiries that were created before that logic existed.
    """
    # Only process leads that currently have no contact but do have a phone number.
    leads_without_contact = Lead.objects.filter(contact__isnull=True).exclude(phone_number='')

    for lead in leads_without_contact.select_related('created_by'):
        try:
            # Reuse the same matching rule as enquiry creation: by phone number.
            existing_contact = Contact.objects.filter(phone_number=lead.phone_number).first()
            if existing_contact:
                if lead.contact_id != existing_contact.id:
                    lead.contact = existing_contact
                    lead.save(update_fields=['contact'])
                continue

            # No existing contact with this phone - create a new one.
            new_contact = Contact.objects.create(
                full_name=lead.contact_name or lead.phone_number,
                phone_number=lead.phone_number,
                email='',
                created_by=lead.created_by,
            )
            lead.contact = new_contact
            lead.save(update_fields=['contact'])
        except Exception:
            # Fail silently; missing contacts for a few leads should not break invoices.
            continue


def _build_contact_meta(form: InvoiceForm):
    try:
        qs = form.fields['contact'].queryset
    except Exception:
        return {}

    meta = {}
    contact_ids = list(qs.values_list('pk', flat=True))

    # Prefetch existing contacts' latest lead fallback data
    fallback_by_contact = {}
    if contact_ids:
        lead_qs = (
            Lead.objects.filter(contact_id__in=contact_ids)
            .order_by('-created_date')
            .values('contact_id', 'phone_number', 'country', 'contact_name')
        )
        seen = set()
        for lead in lead_qs:
            cid = lead['contact_id']
            if cid in seen:
                continue
            fallback_by_contact[cid] = lead
            seen.add(cid)

    # For contacts without linked leads, match loose leads by phone/name
    missing_phone = qs.filter(Q(phone_number__isnull=True) | Q(phone_number='')).values_list('pk', 'full_name')
    phone_to_contact = {contact.phone_number: contact.pk for contact in qs if contact.phone_number}

    loose_lead_qs = (
        Lead.objects.filter(contact__isnull=True)
        .exclude(phone_number='')
        .order_by('-created_date')
        .values('phone_number', 'country', 'contact_name')
    )

    loose_leads_map = {}
    for lead in loose_lead_qs:
        phone = (lead.get('phone_number') or '').strip()
        if not phone:
            continue
        if phone not in loose_leads_map:
            loose_leads_map[phone] = lead

    for contact in qs:
        phone = contact.phone_number or ''
        address = contact.address or ''
        fallback = fallback_by_contact.get(contact.pk)

        if not fallback:
            # try to match loose lead by contact phone
            key_phone = (contact.phone_number or '').strip()
            if key_phone and key_phone in loose_leads_map:
                fallback = loose_leads_map[key_phone]
            else:
                # match by name if phone missing
                for lead in loose_leads_map.values():
                    if contact.full_name and lead.get('contact_name'):
                        if lead['contact_name'].strip().lower() == contact.full_name.strip().lower():
                            fallback = lead
                            break

        if fallback:
            phone = phone or (fallback.get('phone_number') or '')
            address = address or (fallback.get('country') or '')

        meta[str(contact.pk)] = {
            'name': contact.full_name or (fallback.get('contact_name') if fallback else '') or '',
            'phone': phone,
            'address': address,
        }
    return meta


@login_required
def invoice_create(request):
    # Before showing the form, make sure all enquiries have corresponding contacts,
    # so every enquiry customer can appear in the Customer Name dropdown.
    _ensure_contacts_for_leads()

    lead_id = request.GET.get('lead')
    pi_number = ''

    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        posted_pi = (request.POST.get('pi_number') or '').strip()

        selected_lead_id = request.POST.get('lead')
        if selected_lead_id:
            try:
                selected_lead = Lead.objects.only('id', 'proforma_invoice_number').get(pk=selected_lead_id)
                pi_number = selected_lead.proforma_invoice_number or ''
            except (Lead.DoesNotExist, ValueError, TypeError):
                selected_lead = None

        # Prefer what the user typed in the PI input (so it persists on validation errors)
        if posted_pi:
            pi_number = posted_pi

        # Allow completely empty item rows to be ignored (only validate rows with data).
        # We look only at description, quantity and unit_price, because discount may
        # have a default value (0) even on otherwise empty rows.
        for f in formset.forms:
            field_names = ['description', 'quantity', 'unit_price']
            if all(not f.data.get(f.add_prefix(name)) for name in field_names):
                f.empty_permitted = True
                # Ensure Django treats this form as unchanged so validation is skipped
                try:
                    f._changed_data = []
                except Exception:
                    pass
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)

            # Business rule: do not allow invoice creation for a linked enquiry
            # unless the enquiry has a PI number.
            if invoice.lead_id:
                try:
                    lead = Lead.objects.get(pk=invoice.lead_id)
                except Lead.DoesNotExist:
                    lead = None

                if lead is not None:
                    current_pi = (lead.proforma_invoice_number or '').strip()
                    desired_pi = (posted_pi or current_pi).strip()

                    if not desired_pi:
                        form.add_error('lead', 'PI Number is required for this enquiry. Please add PI first.')
                        messages.error(request, 'Please add a Proforma Invoice (PI) number to the enquiry before saving the invoice.')
                        context = {
                            'form': form,
                            'formset': formset,
                            'invoice': None,
                            'pi_number': '',
                        }
                        return render(request, 'invoices_app/invoice_form.html', context)

                    # If enquiry has no PI yet, save what the user typed.
                    if not current_pi and posted_pi:
                        lead.proforma_invoice_number = posted_pi
                        lead.save(update_fields=['proforma_invoice_number'])
                        pi_number = lead.proforma_invoice_number

            if not invoice.created_by:
                invoice.created_by = request.user
            invoice.save()
            formset.instance = invoice
            formset.save()
            _update_invoice_total(invoice)
            if invoice.lead:
                try:
                    lead = invoice.lead
                    lead.invoice_number = invoice.invoice_number
                    lead.enquiry_stage = 'invoice_sent'
                    # Mirror fulfillment behavior: when stage is invoice_sent and
                    # invoice number is present, auto-set status to fulfilled and lock.
                    if (
                        lead.enquiry_stage == 'invoice_sent'
                        and lead.invoice_number
                        and lead.invoice_number.strip()
                        and lead.lead_status != 'fulfilled'
                    ):
                        lead.lead_status = 'fulfilled'
                        lead.is_locked = True
                    lead.save()
                except ValidationError as e:
                    error_messages = []
                    if hasattr(e, 'message_dict'):
                        for msgs in e.message_dict.values():
                            error_messages.extend(msgs)
                    elif hasattr(e, 'messages'):
                        error_messages.extend(e.messages)
                    else:
                        error_messages.append(str(e))
                    if error_messages:
                        messages.warning(request, 'Invoice saved but enquiry not updated: ' + ' '.join(error_messages))
            messages.success(request, 'Invoice created successfully.')
            return redirect('invoices_app:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors in the invoice form and items before saving.')
            if form.errors:
                messages.error(request, f"Form errors: {form.errors.as_text()}")
            if formset.non_form_errors():
                messages.error(request, f"Item errors: {formset.non_form_errors().as_text()}")
            if formset.errors:
                messages.error(request, f"Item form errors: {formset.errors}")
    else:
        # Manual invoice number entry; start with an empty instance
        draft_invoice = Invoice()

        initial_formset = None
        if lead_id:
            try:
                lead = Lead.objects.select_related('contact').get(pk=lead_id)

                pi_number = lead.proforma_invoice_number or ''

                if lead.contact_id:
                    draft_invoice.contact = lead.contact
                draft_invoice.lead = lead

                if not draft_invoice.issue_date:
                    draft_invoice.issue_date = timezone.now().date()

                lead_products = (
                    LeadProduct.objects.filter(lead=lead)
                    .select_related('category', 'subcategory')
                    .order_by('created_date')
                )

                items_initial = []
                for lp in lead_products:
                    parts = []
                    if lp.category:
                        parts.append(lp.category.name)
                    if lp.subcategory:
                        parts.append(lp.subcategory.name)
                    description = ' - '.join(parts) if parts else (lp.category.name if lp.category else 'Item')
                    items_initial.append({
                        'description': description,
                        'quantity': lp.quantity or 1,
                        'unit_price': lp.price or None,
                        'discount_percent': 0,
                    })

                if lead.notes:
                    draft_invoice.notes = lead.notes

                initial_formset = items_initial

            except Lead.DoesNotExist:
                lead = None

        form = InvoiceForm(instance=draft_invoice)

        if initial_formset:
            formset = InvoiceItemFormSet(initial=initial_formset)
        else:
            formset = InvoiceItemFormSet()
    context = {
        'form': form,
        'formset': formset,
        'invoice': None,
        'pi_number': pi_number,
    }
    context['contact_meta_json'] = json.dumps(_build_contact_meta(form))
    return render(request, 'invoices_app/invoice_form.html', context)


@login_required
def invoice_edit(request, pk: int):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            invoice = form.save()
            formset.save()
            _update_invoice_total(invoice)
            messages.success(request, 'Invoice updated successfully.')
            return redirect('invoices_app:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)
    context = {
        'form': form,
        'formset': formset,
        'invoice': invoice,
    }
    context['contact_meta_json'] = json.dumps(_build_contact_meta(form))
    return render(request, 'invoices_app/invoice_form.html', context)


@login_required
def invoice_detail(request, pk: int):
    invoice = get_object_or_404(
        Invoice.objects.select_related('contact', 'created_by').prefetch_related('items'),
        pk=pk,
    )
    aggregate = invoice.items.aggregate(subtotal=Sum('line_total'))
    subtotal = aggregate['subtotal'] or Decimal('0')
    vat_amount = (subtotal * Decimal('0.05'))
    grand_total = subtotal + vat_amount
    context = {
        'invoice': invoice,
        'subtotal': subtotal,
        'vat_amount': vat_amount,
        'grand_total': grand_total,
    }
    return render(request, 'invoices_app/invoice_detail.html', context)


@login_required
def contact_leads_api(request, contact_id: int):
    """Return JSON list of enquiries for a given contact.

    Each item contains id and a human-friendly label combining
    enquiry name, stage, and created date.
    """
    contact = get_object_or_404(Contact, pk=contact_id)

    # Include enquiries that are:
    # - explicitly linked to this Contact via the FK, OR
    # - not linked to any Contact but share the same phone number, OR
    # - not linked but have a matching contact_name.
    #
    # Also, exclude enquiries that are already completed (stage 'invoice_sent')
    # so we don't try to create a second invoice for the same enquiry.
    leads = (
        Lead.objects.filter(
            Q(contact_id=contact_id)
            | Q(contact__isnull=True, phone_number=contact.phone_number)
            | Q(contact__isnull=True, contact_name__iexact=contact.full_name)
        )
        .exclude(enquiry_stage='invoice_sent')
        .order_by('-created_date')
        .distinct()
    )
    data = []
    for lead in leads:
        label_parts = [lead.contact_name or str(lead.pk)]
        try:
            stage_display = lead.get_enquiry_stage_display()
            if stage_display:
                label_parts.append(stage_display)
        except Exception:
            pass
        if getattr(lead, 'created_date', None):
            label_parts.append(lead.created_date.strftime('%d %b %Y'))
        data.append({
            'id': lead.id,
            'label': ' - '.join(label_parts),
            'pi_number': lead.proforma_invoice_number or '',
            'country': getattr(lead, 'country', '') or '',
            'phone': lead.phone_number or '',
        })
    return JsonResponse(data, safe=False)


@login_required
def lead_items_api(request, lead_id: int):
    """Return JSON line items for the given enquiry (lead).

    Uses LeadProduct rows when available, and falls back to the
    old products_enquired M2M if no detailed products exist.
    """
    lead = get_object_or_404(Lead, pk=lead_id)

    items = []

    # Prefer detailed LeadProduct entries
    lead_products = (
        LeadProduct.objects.filter(lead=lead)
        .select_related('category', 'subcategory')
        .order_by('created_date')
    )

    for lp in lead_products:
        parts = []
        if lp.category:
            parts.append(lp.category.name)
        if lp.subcategory:
            parts.append(lp.subcategory.name)
        description = ' - '.join(parts) if parts else (lp.category.name if lp.category else 'Item')

        items.append({
            'description': description,
            'quantity': lp.quantity or 1,
            'unit_price': str(lp.price or ''),
            'discount_percent': '0',
        })

    # Fallback to old products_enquired if no LeadProduct rows
    if not items:
        for product in lead.products_enquired.all():
            items.append({
                'description': product.name,
                'quantity': 1,
                'unit_price': '',
                'discount_percent': '0',
            })

    return JsonResponse(items, safe=False)


def _update_invoice_total(invoice: Invoice) -> None:
    aggregate = invoice.items.aggregate(subtotal=Sum('line_total'))
    subtotal = aggregate['subtotal'] or Decimal('0')
    vat_amount = (subtotal * Decimal('0.05'))
    total = subtotal + vat_amount
    invoice.total_amount = total
    invoice.save(update_fields=['total_amount'])
