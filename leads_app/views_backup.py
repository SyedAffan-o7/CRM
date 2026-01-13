from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError

from products.models import Category, Subcategory
from leads_app.models import Lead, Reason, LeadSource, Product, LeadProduct
from accounts_app.models import Account
from deals_app.models import Deal
from activities_app.models import ActivityLog
from crm_app.forms import LeadForm, ContactForm, AccountForm, DealForm, ActivityLogForm
from django.views.decorators.http import require_http_methods, require_POST
from django.template.loader import render_to_string

from .models import Lead, FollowUp
from outbound_app.models import OutboundActivity
from .forms import FollowUpForm, FollowUpStatusForm


# Dashboard
@login_required
def dashboard(request):
    # Get filters from request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    month_filter = request.GET.get('month_filter')
    year_filter = request.GET.get('year_filter')

    # Handle month filter
    if month_filter:
        selected_month = int(month_filter)
        selected_year = int(year_filter) if year_filter else timezone.now().year
        from_date = datetime(selected_year, selected_month, 1).date()
        if selected_month == 12:
            to_date = datetime(selected_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            to_date = datetime(selected_year, selected_month + 1, 1).date() - timedelta(days=1)
    elif from_date and to_date:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        selected_month = None
        selected_year = None
    else:
        now = timezone.now()
        from_date = now.replace(day=1).date()
        to_date = now.date()
        selected_month = now.month
        selected_year = now.year

    # Filter enquiries by date range
    if request.user.is_superuser:
        enquiries_in_range = Lead.objects.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date
        )
        salesmen = User.objects.filter(assigned_leads__isnull=False).distinct().order_by('id')
    else:
        enquiries_in_range = Lead.objects.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date,
            created_by=request.user
        )
        salesmen = User.objects.filter(id=request.user.id)

    total_enquiries_month = enquiries_in_range.count()
    fulfilled_month = enquiries_in_range.filter(lead_status='fulfilled').count()
    not_fulfilled_month = enquiries_in_range.filter(lead_status='not_fulfilled').count()
    fulfillment_rate = round((fulfilled_month / total_enquiries_month) * 100, 1) if total_enquiries_month > 0 else 0

    sales1_total = sales1_fulfilled = sales1_not_fulfilled = sales1_fulfillment_rate = 0
    sales2_total = sales2_fulfilled = sales2_not_fulfilled = sales2_fulfillment_rate = 0
    sales1_name = "Sales Person 1"
    sales2_name = "Sales Person 2"
    sales1_user_id = None
    sales2_user_id = None

    if salesmen.exists():
        sales1 = salesmen[0]
        sales1_name = sales1.get_full_name() or sales1.username
        sales1_user_id = sales1.id
        sales1_enquiries = enquiries_in_range.filter(created_by=sales1)
        sales1_total = sales1_enquiries.count()
        sales1_fulfilled = sales1_enquiries.filter(lead_status='fulfilled').count()
        sales1_not_fulfilled = sales1_enquiries.filter(lead_status='not_fulfilled').count()
        sales1_fulfillment_rate = round((sales1_fulfilled / sales1_total) * 100, 1) if sales1_total > 0 else 0

        if len(salesmen) > 1:
            sales2 = salesmen[1]
            sales2_name = sales2.get_full_name() or sales2.username
            sales2_user_id = sales2.id
            sales2_enquiries = enquiries_in_range.filter(created_by=sales2)
            sales2_total = sales2_enquiries.count()
            sales2_fulfilled = sales2_enquiries.filter(lead_status='fulfilled').count()
            sales2_not_fulfilled = sales2_enquiries.filter(lead_status='not_fulfilled').count()
            sales2_fulfillment_rate = round((sales2_fulfilled / sales2_total) * 100, 1) if sales2_total > 0 else 0

    current_month_name = from_date.strftime('%B %Y')

    # Get follow-ups (only pending for dashboard display)
    if request.user.is_superuser:
        followups = FollowUp.objects.filter(status='pending')
    else:
        followups = FollowUp.objects.filter(
            Q(assigned_to=request.user) | Q(created_by=request.user),
            status='pending'
        ).distinct()

    overdue_followups = [f for f in followups if f.is_overdue]
    today_followups = [f for f in followups if f.is_due_today]
    upcoming_followups = [f for f in followups if f.is_upcoming]

    context = {
        'total_enquiries_month': total_enquiries_month,
        'fulfilled_month': fulfilled_month,
        'not_fulfilled_month': not_fulfilled_month,
        'fulfillment_rate': fulfillment_rate,
        'sales1_name': sales1_name,
        'sales1_total': sales1_total,
        'sales1_fulfilled': sales1_fulfilled,
        'sales1_not_fulfilled': sales1_not_fulfilled,
        'sales1_fulfillment_rate': sales1_fulfillment_rate,
        'sales2_name': sales2_name,
        'sales2_total': sales2_total,
        'sales2_fulfilled': sales2_fulfilled,
        'sales2_not_fulfilled': sales2_not_fulfilled,
        'sales2_fulfillment_rate': sales2_fulfillment_rate,
        'sales1_user_id': sales1_user_id,
        'sales2_user_id': sales2_user_id,
        'from_date': from_date,
        'to_date': to_date,
        'selected_month': selected_month if 'selected_month' in locals() else None,
        'selected_year': selected_year if 'selected_year' in locals() else None,
        'date_range_display': f"{from_date.strftime('%B %d, %Y')} - {to_date.strftime('%B %d, %Y')}",
        'timezone': getattr(settings, 'TIME_ZONE', 'UTC'),
        'current_month_name': current_month_name,
        'overdue_followups': overdue_followups,
        'today_followups': today_followups,
        'upcoming_followups': upcoming_followups,
    }
    return render(request, 'crm_app/dashboard.html', context)


# Enquiries
@login_required
def lead_list(request):
    if request.user.is_superuser:
        leads = Lead.objects.select_related('assigned_sales_person', 'created_by').all()
    else:
        leads = Lead.objects.select_related('assigned_sales_person', 'created_by').filter(created_by=request.user)

    owner_filter = request.GET.get('owner')
    if owner_filter:
        leads = leads.filter(created_by_id=owner_filter)

    enquiry_status_filter = request.GET.get('enquiry_status')
    if enquiry_status_filter:
        leads = leads.filter(lead_status=enquiry_status_filter)

    enquiry_stage_filter = request.GET.get('enquiry_stage')
    if enquiry_stage_filter:
        leads = leads.filter(enquiry_stage=enquiry_stage_filter)

    country_filter = request.GET.get('country')
    if country_filter:
        leads = leads.filter(country__icontains=country_filter)

    search_query = request.GET.get('search')
    if search_query:
        leads = leads.filter(
            Q(contact_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )

    leads = leads.order_by('-created_date')

    paginator = Paginator(leads, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    owners = User.objects.filter(created_leads__isnull=False).distinct().order_by('first_name', 'last_name', 'username')

    if request.user.is_superuser:
        countries = Lead.objects.exclude(country='').values_list('country', flat=True).distinct().order_by('country')
    else:
        countries = Lead.objects.filter(created_by=request.user).exclude(country='').values_list('country', flat=True).distinct().order_by('country')

    context = {
        'leads': page_obj,
        'page_obj': page_obj,
        'status_choices': Lead.STATUS_CHOICES,
        'stage_choices': Lead.ENQUIRY_STAGE_CHOICES,
        'owners': owners,
        'countries': countries,
        'reasons': Reason.objects.filter(is_active=True),
    }
    return render(request, 'crm_app/lead_list.html', context)


@login_required
def lead_detail(request, pk):
    """
    View for displaying lead details and handling follow-ups
    """
    lead = get_object_or_404(Lead, pk=pk)
    
    # Check permissions - only allow assigned user or admin to view
    if not request.user.is_superuser and lead.assigned_sales_person != request.user:
        messages.error(request, 'You do not have permission to view this lead.')
        return redirect('crm_app:lead_list')
    
    # Get follow-ups for this lead
    follow_ups = lead.follow_ups.all().order_by('-scheduled_date')
    # Get outbound activities linked to this lead
    outbound_activities = (
        OutboundActivity.objects.select_related('contact', 'campaign', 'created_by')
        .filter(lead=lead)
        .order_by('-created_at')
    )
    
    # Handle follow-up form submission
    if request.method == 'POST' and 'add_followup' in request.POST:
        followup_form = FollowUpForm(request.POST, request=request, lead=lead)
        if followup_form.is_valid():
            followup = followup_form.save(commit=False)
            followup.lead = lead
            followup.created_by = request.user
            followup.save()
            
            # Log activity
            ActivityLog.objects.create(
                lead=lead,
                user=request.user,
                activity_type='followup_created',
                details=f'Follow-up scheduled for {followup.scheduled_date.strftime("%Y-%m-%d %H:%M")}'
            )
            
            messages.success(request, 'Follow-up added successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        followup_form = FollowUpForm(request=request, lead=lead)
    
    # Handle follow-up status update
    if request.method == 'POST' and 'update_followup_status' in request.POST:
        followup_id = request.POST.get('followup_id')
        followup = get_object_or_404(FollowUp, id=followup_id, lead=lead)
        status_form = FollowUpStatusForm(request.POST, instance=followup)
        
        if status_form.is_valid():
            old_status = followup.status
            followup = status_form.save()
            
            # Log status change
            if 'status' in status_form.changed_data:
                ActivityLog.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='followup_status_changed',
                    details=f'Follow-up status changed from {old_status} to {followup.status}'
                )
            
            messages.success(request, 'Follow-up status updated successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        status_form = FollowUpStatusForm()
    
    context = {
        'lead': lead,
        'follow_ups': follow_ups,
        'followup_form': followup_form,
        'status_form': status_form,
        'outbound_activities': outbound_activities,
    }
    
    return render(request, 'crm_app/lead_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def followup_create(request, lead_id):
    """
    Handle follow-up creation via AJAX
    """
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if not request.user.is_superuser and lead.assigned_sales_person != request.user:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to add follow-ups for this lead.'
        }, status=403)
    
    if request.method == 'POST':
        form = FollowUpForm(request.POST, request=request, lead=lead)
        if form.is_valid():
            followup = form.save(commit=False)
            followup.lead = lead
            followup.created_by = request.user
            followup.save()
            
            # Log activity
            ActivityLog.objects.create(
                lead=lead,
                user=request.user,
                activity_type='followup_created',
                details=f'Follow-up scheduled for {followup.scheduled_date.strftime("%Y-%m-%d %H:%M")}'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Follow-up added successfully!',
                'followup_id': followup.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Please correct the errors below.'
            }, status=400)
    
    # GET request - return the form HTML
    form = FollowUpForm(request=request, lead=lead)
    form_html = render_to_string('crm_app/partials/followup_form.html', {
        'form': form,
        'lead': lead
    }, request=request)
    
    return JsonResponse({
        'success': True,
        'form_html': form_html
    })

@login_required
@require_POST
def followup_update_status(request, followup_id):
    """
    Update follow-up status via AJAX
    """
    followup = get_object_or_404(FollowUp, id=followup_id)
    
    # Check permissions
    if not request.user.is_superuser and followup.assigned_to != request.user:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to update this follow-up.'
        }, status=403)
    
    form = FollowUpStatusForm(request.POST, instance=followup)
    
    if form.is_valid():
        old_status = followup.status
        followup = form.save()
        
        # Log status change
        if 'status' in form.changed_data:
            ActivityLog.objects.create(
                lead=followup.lead,
                user=request.user,
                activity_type='followup_status_changed',
                details=f'Follow-up status changed from {old_status} to {followup.status}'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Follow-up status updated successfully!',
            'status': followup.get_status_display(),
            'status_class': followup.status
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors,
        'message': 'Please correct the errors below.'
    }, status=400)

@login_required
def get_followups(request):
    """
    Get follow-ups for the current user or a specific lead
    """
    lead_id = request.GET.get('lead_id')
    
    # Base queryset with permission check
    if request.user.is_superuser:
        followups = FollowUp.objects.all()
    else:
        followups = FollowUp.objects.filter(
            Q(created_by=request.user) | 
            Q(assigned_to=request.user) |
            Q(lead__assigned_sales_person=request.user)
        )
    
    # Filter by lead if specified
    if lead_id:
        followups = followups.filter(lead_id=lead_id)
    
    # Get follow-ups by status
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    overdue = followups.filter(
        scheduled_date__lt=now,
        status__in=['pending', 'overdue']
    ).order_by('scheduled_date')
    
    today = followups.filter(
        scheduled_date__range=(today_start, today_end),
        status='pending'
    ).order_by('scheduled_date')
    
    tomorrow_start = today_end
    tomorrow_end = tomorrow_start + timedelta(days=1)
    
    tomorrow = followups.filter(
        scheduled_date__range=(tomorrow_start, tomorrow_end),
        status='pending'
    ).order_by('scheduled_date')
    
    upcoming = followups.filter(
        scheduled_date__gt=tomorrow_end,
        status='pending'
    ).order_by('scheduled_date')
    
    # Prepare data for JSON response
    def prepare_followup_data(qs):
        return [{
            'id': f.id,
            'lead_id': f.lead_id,
            'lead_name': str(f.lead.contact_name),
            'scheduled_date': f.scheduled_date.strftime('%Y-%m-%d %H:%M'),
            'notes': f.notes,
            'status': f.status,
            'status_display': f.get_status_display(),
            'is_overdue': f.is_overdue,
            'is_due_today': f.is_due_today,
            'is_upcoming': f.is_upcoming,
            'assigned_to': str(f.assigned_to.get_full_name() or f.assigned_to.username) if f.assigned_to else None,
            'created_by': str(f.created_by.get_full_name() or f.created_by.username) if f.created_by else None,
            'can_edit': request.user.is_superuser or f.created_by == request.user or f.assigned_to == request.user,
            'can_delete': request.user.is_superuser or f.created_by == request.user,
        } for f in qs]
    
    data = {
        'overdue': prepare_followup_data(overdue),
        'today': prepare_followup_data(today),
        'tomorrow': prepare_followup_data(tomorrow),
        'upcoming': prepare_followup_data(upcoming)
    }
    
    return JsonResponse(data)

@login_required
def followup_edit(request, followup_id):
    """
    Edit a follow-up linked to a lead.
    """
    followup = get_object_or_404(FollowUp, id=followup_id)
    lead = followup.lead
    
    # Permissions: superuser, creator, assigned user, or lead's assigned_sales_person
    if not (
        request.user.is_superuser or
        followup.created_by == request.user or
        followup.assigned_to == request.user or
        lead.assigned_sales_person == request.user
    ):
        messages.error(request, 'You do not have permission to edit this follow-up.')
        return redirect('crm_app:lead_detail', pk=lead.pk)
    
    if request.method == 'POST':
        form = FollowUpForm(request.POST, instance=followup, request=request, lead=lead)
        if form.is_valid():
            form.save()
            messages.success(request, 'Follow-up updated successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        form = FollowUpForm(instance=followup, request=request, lead=lead)
    
    return render(request, 'crm_app/followup_edit.html', {
        'lead': lead,
        'form': form,
        'followup': followup,
    })

@login_required
def lead_add(request):
    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.created_by = request.user

            # Link to a Contact if user initiated from a contact profile/list
            contact_id_prefill = request.session.pop('prefill_contact_id', None)
            if contact_id_prefill:
                try:
                    contact_obj = Contact.objects.get(pk=contact_id_prefill)
                    lead.contact = contact_obj
                    # If company name not provided, try to pull from contact's company
                    if not lead.company_name and getattr(contact_obj, 'company', None):
                        lead.company_name = getattr(contact_obj.company, 'company_name', '')
                    # If phone missing, use contact phone
                    if not lead.phone_number:
                        lead.phone_number = contact_obj.phone_number
                    # If contact_name missing, use contact name
                    if not lead.contact_name:
                        lead.contact_name = contact_obj.full_name
                except Contact.DoesNotExist:
                    pass

            phone_number = lead.phone_number
            if phone_number:
                if phone_number.startswith('+1'):
                    country = 'United States'
                elif phone_number.startswith('+44'):
                    country = 'United Kingdom'
                elif phone_number.startswith('+91'):
                    country = 'India'
                elif phone_number.startswith('+86'):
                    country = 'China'
                elif phone_number.startswith('+49'):
                    country = 'Germany'
                elif phone_number.startswith('+33'):
                    country = 'France'
                elif phone_number.startswith('+81'):
                    country = 'Japan'
                elif phone_number.startswith('+61'):
                    country = 'Australia'
                elif phone_number.startswith('+971'):
                    country = 'UAE'
                elif phone_number.startswith('+966'):
                    country = 'Saudi Arabia'
                else:
                    country = 'Unknown'
                if country and country != 'Unknown':
                    lead.country = country

            # Auto-create Contact when enquiry is received (if not already linked)
            if not lead.contact and lead.phone_number:
                try:
                    # Try to find existing contact by phone number
                    existing_contact = Contact.objects.filter(phone_number=lead.phone_number).first()
                    if existing_contact:
                        lead.contact = existing_contact
                    else:
                        # Create new contact automatically
                        new_contact = Contact.objects.create(
                            full_name=lead.contact_name,
                            phone_number=lead.phone_number,
                            email='',  # Will be empty initially
                            created_by=request.user
                        )
                        # Link company if we have company name
                        if lead.company_name:
                            from accounts_app.models import Account
                            company, created = Account.objects.get_or_create(
                                company_name=lead.company_name,
                                defaults={'created_by': request.user}
                            )
                            new_contact.company = company
                            new_contact.save()
                        
                        lead.contact = new_contact
                        
                        # Log the auto-creation
                        ActivityLog.objects.create(
                            contact=new_contact,
                            activity_type='note',
                            subject='Contact auto-created',
                            description=f'Contact automatically created from enquiry: {lead.contact_name}',
                            user=request.user
                        )
                except Exception as e:
                    # If contact creation fails, continue without it
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to auto-create contact for lead {lead.contact_name}: {str(e)}")

            lead.save()
            form.save_m2m()

            categories = request.POST.getlist('categories[]')
            subcategories = request.POST.getlist('subcategories[]')
            descriptions = request.POST.getlist('product_descriptions[]')
            images = request.FILES.getlist('product_images[]')

            for i, category_id in enumerate(categories):
                if category_id:
                    lead_product = LeadProduct(lead=lead)
                    try:
                        lead_product.category = Category.objects.get(id=category_id)
                    except Category.DoesNotExist:
                        pass
                    if i < len(subcategories) and subcategories[i]:
                        try:
                            lead_product.subcategory = Subcategory.objects.get(id=subcategories[i])
                        except Subcategory.DoesNotExist:
                            pass
                    if i < len(descriptions):
                        lead_product.description = descriptions[i]
                    if i < len(images) and images[i]:
                        lead_product.image = images[i]
                    lead_product.save()

            ActivityLog.objects.create(
                lead=lead,
                activity_type='note',
                subject='Lead created',
                description=f'New enquiry created for {lead.contact_name}',
                user=request.user
            )

            messages.success(request, 'Enquiry created successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        # Prefill form from Contact when contact_id provided
        contact_id = request.GET.get('contact_id')
        if contact_id:
            try:
                contact_obj = Contact.objects.select_related('company').get(pk=contact_id)
                company_name = ''
                try:
                    if contact_obj.company:
                        company_name = contact_obj.company.company_name
                except Account.DoesNotExist:
                    company_name = '' # Handle broken foreign key

                initial = {
                    'contact_name': contact_obj.full_name,
                    'phone_number': contact_obj.phone_number,
                    'company_name': company_name,
                }
                form = LeadForm(initial=initial)
                # Persist for POST handling
                request.session['prefill_contact_id'] = contact_obj.pk
            except Contact.DoesNotExist:
                form = LeadForm()
        else:
            form = LeadForm()

    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True).select_related('category')

    return render(request, 'crm_app/lead_form.html', {
        'form': form,
        'title': 'Add New Enquiry',
        'categories': categories,
        'subcategories': subcategories
    })


@login_required
def lead_edit(request, pk):
    if request.user.is_superuser:
        lead = get_object_or_404(Lead, pk=pk)
    else:
        lead = get_object_or_404(Lead, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enquiry updated successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        form = LeadForm(instance=lead)

    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True).select_related('category')

    return render(request, 'crm_app/lead_form.html', {
        'form': form,
        'title': 'Edit Enquiry',
        'lead': lead,
        'categories': categories,
        'subcategories': subcategories
    })


@login_required
def lead_convert(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    if not request.user.is_superuser and lead.created_by != request.user:
        messages.error(request, "You don't have permission to convert this lead.")
        return redirect('crm_app:lead_list')

    if request.method == 'POST':
        try:
            contact, created = Contact.objects.get_or_create(
                phone_number=lead.phone_number,
                defaults={
                    'full_name': lead.contact_name,
                    'company': None,
                    'created_by': request.user
                }
            )
            lead.contact = contact
            lead.lead_status = 'fulfilled'
            lead.save()

            ActivityLog.objects.create(
                lead=lead,
                contact=contact,
                activity_type='note',
                subject='Lead converted',
                description=f'Lead converted to contact: {contact.full_name}',
                user=request.user
            )

            create_deal = request.POST.get('create_deal')
            if create_deal:
                deal = Deal.objects.create(
                    deal_name=f"Deal for {contact.full_name}",
                    contact=contact,
                    deal_stage='prospecting',
                    deal_value=0,
                    created_by=request.user
                )
                messages.success(request, 'Lead converted successfully! Contact and Deal created.')
                return redirect('crm_app:deal_detail', pk=deal.pk)
            else:
                messages.success(request, 'Lead converted successfully! Contact created.')
                return redirect('crm_app:contact_detail', pk=contact.pk)
        except Exception as e:
            messages.error(request, f'Error converting lead: {str(e)}')
            return redirect('crm_app:lead_detail', pk=pk)

    return render(request, 'crm_app/lead_convert.html', {
        'lead': lead,
        'title': f'Convert Lead: {lead.contact_name}'
    })


@login_required
def get_subcategories(request, category_id):
    try:
        category = Category.objects.get(pk=category_id, is_active=True)
        subcategories = Subcategory.objects.filter(category=category, is_active=True)
        subcategory_data = [{'id': sub.id, 'name': sub.name} for sub in subcategories]
        return JsonResponse({'subcategories': subcategory_data})
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)


@login_required
def lead_update_status(request, pk):
    """Update lead status via AJAX with validation and logging"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Log request data for debugging
        logger.info(f"Status update request data: {request.POST}")
        logger.info(f"Request user: {request.user}")
        
        lead = get_object_or_404(Lead, pk=pk)
        logger.info(f"Found lead: {lead.phone_number}, current status: {lead.lead_status}")
        
        # Check permissions: allow superuser, creator, assigned_sales_person, or staff
        if not request.user.is_superuser:
            is_creator = (lead.created_by == request.user)
            is_assigned = (lead.assigned_sales_person == request.user)
            is_staff = request.user.is_staff
            if not (is_creator or is_assigned or is_staff):
                logger.warning(f"Permission denied for user {request.user} on lead {lead.phone_number}")
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        new_status = request.POST.get('status')
        logger.info(f"New status: {new_status}")
        
        if not new_status:
            logger.warning("No status provided in request")
            return JsonResponse({'success': False, 'error': 'Missing status'})

        # Business Logic: Prevent changing from fulfilled back to not_fulfilled
        if lead.lead_status == 'fulfilled' and new_status == 'not_fulfilled':
            logger.warning(f"Cannot change fulfilled lead {lead.phone_number} back to not_fulfilled")
            return JsonResponse({
                'success': False,
                'error': 'Cannot change status from Fulfilled back to Not Fulfilled. Once fulfilled, status is locked.'
            })

        # Validate status is in choices
        if new_status not in dict(Lead.STATUS_CHOICES):
            logger.warning(f"Invalid status: {new_status}")
            return JsonResponse({'success': False, 'error': 'Invalid status'})

        # Get the display value for the status
        status_display = dict(Lead.STATUS_CHOICES).get(new_status, new_status)
        
        # Update the lead status
        lead.lead_status = new_status
        lead.save(update_fields=['lead_status', 'updated_date'])
        
        # Log the status update
        logger.info(f"Lead {lead.phone_number} status updated to {new_status} by {request.user}")
        
        # Create activity log
        ActivityLog.objects.create(
            user=request.user,
            activity_type='status_change',
            content_object=lead,
            details=f'Status changed to {status_display}'
        )
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': status_display,
            'message': 'Status updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating lead status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': f'Error updating status: {str(e)}'
        })

@login_required
def lead_update_stage(request, pk):
    """Update enquiry stage via AJAX with invoice validation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Request data: {request.POST}")
        logger.info(f"Request user: {request.user}")
        
        lead = get_object_or_404(Lead, pk=pk)
        logger.info(f"Found lead: {lead.phone_number}, created by: {lead.created_by}")
        
        # Check permissions
        if not request.user.is_superuser and lead.created_by != request.user:
            logger.warning(f"Permission denied for user {request.user} on lead {lead.phone_number}")
            if not request.user.is_staff:
                return JsonResponse({'success': False, 'error': 'Permission denied'})

        # Accept both 'stage' and 'enquiry_stage' parameter names for compatibility
        new_stage = request.POST.get('enquiry_stage') or request.POST.get('stage')
        logger.info(f"New stage: {new_stage}")
        
        if not new_stage:
            logger.warning("No stage provided in request")
            return JsonResponse({'success': False, 'error': 'Missing stage'})

        # Validate stage is in choices
        if new_stage not in dict(Lead.ENQUIRY_STAGE_CHOICES):
            logger.warning(f"Invalid stage: {new_stage}")
            return JsonResponse({'success': False, 'error': 'Invalid stage'})

        # Get the display value for the stage
        stage_display = dict(Lead.ENQUIRY_STAGE_CHOICES).get(new_stage, new_stage)
        
        # Validation: enforce numbers for specific stages
        if new_stage == 'proforma_invoice_sent':
            pi_no = request.POST.get('proforma_invoice_number')
            logger.info(f"Proforma invoice number: {pi_no}")
            if not pi_no:
                error_msg = 'Proforma Invoice Number is required for Proforma Invoice Sent'
                logger.warning(error_msg)
                return JsonResponse({
                    'success': False, 
                    'error': error_msg
                })
            lead.proforma_invoice_number = pi_no
        elif new_stage in ('invoice_made', 'invoice_sent', 'won'):
            inv_no = request.POST.get('invoice_number')
            logger.info(f"Invoice number: {inv_no}")
            
            # Check if PI number exists first
            if not lead.proforma_invoice_number:
                error_msg = 'Enter PI first. Invoice Number can only be entered after Proforma Invoice (PI) is created.'
                logger.warning(error_msg)
                return JsonResponse({
                    'success': False, 
                    'error': error_msg
                })
            
            if not inv_no:
                error_msg = f'Invoice Number is required for {stage_display}'
                logger.warning(error_msg)
                return JsonResponse({
            lead.invoice_number = inv_no

        # Business Logic: Auto-fulfill when stage becomes 'won'
        old_status = lead.lead_status
        if new_stage == 'won' and lead.lead_status != 'fulfilled':
            lead.lead_status = 'fulfilled'
            logger.info(f"Auto-fulfilling lead {lead.phone_number} because stage changed to 'won'")
        
        # Save the changes
        lead.enquiry_stage = new_stage
        lead.save(update_fields=['enquiry_stage', 'lead_status', 'proforma_invoice_number', 'invoice_number', 'updated_date'])
        logger.info(f"Successfully updated lead {lead.phone_number} to stage {new_stage} (status: {lead.lead_status})")
                f"Stage persistence verification failed for lead {lead.phone_number}. Expected {new_stage}, got {persisted_stage}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Stage update failed to persist. Please try again or contact support.',
                'expected_stage': new_stage,
                'persisted_stage': persisted_stage
            }, status=500)

        # Log the stage change
        try:
            ActivityLog.objects.create(
                user=request.user,
                activity_type='stage_change',
                content_object=lead,
                details=f'Stage changed to {stage_display}'
            )
        except Exception as e:
            logger.error(f"Error creating activity log: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'enquiry_stage': new_stage,
            'stage_display': stage_display
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating lead stage: {str(e)}\n{error_trace}")
        return JsonResponse({
            'success': False, 
            'error': f'Server error: {str(e)}',
            'traceback': error_trace
        }, status=500)


@login_required
def lead_update_assignment(request, pk):
    if request.method == 'POST':
        lead = get_object_or_404(Lead, pk=pk)
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            lead.assigned_sales_person = user
        else:
            lead.assigned_sales_person = None
        lead.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def lead_delete(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if not request.user.is_superuser and lead.created_by != request.user:
        messages.error(request, "You don't have permission to delete this lead.")
        return redirect('crm_app:lead_list')
    if request.method == 'POST':
        lead.delete()
        messages.success(request, 'Lead deleted successfully.')
        return redirect('crm_app:lead_list')


# Enquiry Stages
@login_required
def enquiry_stages(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    month_filter = request.GET.get('month_filter')
    year_filter = request.GET.get('year_filter')

    # Initialize date variables
    selected_month = None
    selected_year = None

    if month_filter:
        try:
            selected_month = int(month_filter)
            selected_year = int(year_filter) if year_filter else timezone.now().year
            from_date = datetime(selected_year, selected_month, 1).date()
            if selected_month == 12:
                to_date = datetime(selected_year + 1, 1, 1).date() - timedelta(days=1)
            else:
                to_date = datetime(selected_year, selected_month + 1, 1).date() - timedelta(days=1)
        except (ValueError, TypeError):
            # Fallback to current month if invalid
            now = timezone.now()
            from_date = now.replace(day=1).date()
            to_date = now.date()
            selected_month = now.month
            selected_year = now.year
    elif from_date and to_date:
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Fallback to current month if invalid dates
            now = timezone.now()
            from_date = now.replace(day=1).date()
            to_date = now.date()
            selected_month = now.month
            selected_year = now.year
    else:
        # Default to no date filtering
        from_date = None
        to_date = None

    # Get leads with proper prefetching
    base_leads_qs = Lead.objects.select_related(
        'assigned_sales_person', 'created_by'
    ).prefetch_related('products_enquired')

    # Apply date filtering only if dates are provided
    if from_date and to_date:
        base_leads_qs = base_leads_qs.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date
        )

    # Apply user-based filtering
    if not request.user.is_superuser:
        base_leads_qs = base_leads_qs.filter(
            Q(created_by=request.user) | Q(assigned_sales_person=request.user)
        )

    # Build stages dictionary with lists instead of QuerySets
    stages = {}
    for key, name in Lead.ENQUIRY_STAGE_CHOICES:
        stage_leads = list(base_leads_qs.filter(enquiry_stage=key).order_by('-created_date'))
        stages[key] = {
            'name': name,
            'leads': stage_leads
        }

    # Get all reasons for the 'Lost' modal
    reasons = Reason.objects.filter(is_active=True)

    return render(request, 'crm_app/enquiry_stages.html', {
        'stages': stages,
        'reasons': reasons,
        'page_title': 'Enquiry Stages',
        'from_date': from_date,
        'to_date': to_date,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })


# Settings & management
@login_required
def settings(request):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to access settings.")
        return redirect('crm_app:dashboard')
    return render(request, 'crm_app/settings.html', {'title': 'Settings'})


@login_required
def user_list(request):
    """Redirect to new role-based user management system"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to manage users.")
        return redirect('crm_app:dashboard')

    # Redirect to the new role-based user management system
    return redirect('accounts_app:user_management')


@login_required
def user_add(request):
    """Redirect to new role-based user management system"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to add users.")
        return redirect('crm_app:dashboard')

    # Redirect to the new role-based user management system
    return redirect('accounts_app:user_management')


@login_required
def user_toggle_status(request, pk):
    """Redirect to new role-based user management system"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    # Redirect to the new role-based user management system
    return redirect('accounts_app:user_management')


@login_required
def user_delete(request, pk):
    """Redirect to new role-based user management system"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete users.")
        return redirect('crm_app:dashboard')

    # Redirect to the new role-based user management system
    return redirect('accounts_app:user_management')
@login_required
def lead_source_list(request):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to manage lead sources.")
        return redirect('crm_app:dashboard')
    lead_sources = LeadSource.objects.all()
    return render(request, 'crm_app/lead_source_list.html', {
        'lead_sources': lead_sources,
        'title': 'Lead Sources'
    })


@login_required
def lead_source_add(request):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to add lead sources.")
        return redirect('crm_app:dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            LeadSource.objects.create(
                name=name,
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'Lead source created successfully.')
            return redirect('crm_app:lead_source_list')
    return render(request, 'crm_app/lead_source_form.html', {'title': 'Add Lead Source'})


@login_required
def lead_source_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit lead sources.")
        return redirect('crm_app:dashboard')
    lead_source = get_object_or_404(LeadSource, pk=pk)
    if request.method == 'POST':
        lead_source.name = request.POST.get('name', lead_source.name)
        lead_source.description = request.POST.get('description', lead_source.description)
        lead_source.save()
        messages.success(request, 'Lead source updated successfully.')
        return redirect('crm_app:lead_source_list')
    return render(request, 'crm_app/lead_source_form.html', {
        'lead_source': lead_source,
        'title': f'Edit Lead Source: {lead_source.name}'
    })


@login_required
def lead_source_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete lead sources.")
        return redirect('crm_app:lead_source_list')
    lead_source = get_object_or_404(LeadSource, pk=pk)
    if request.method == 'POST':
        try:
            # To avoid DB-level constraints when managed=False models may not match schema,
            # first detach this lead source from any related leads.
            Lead.objects.filter(lead_source=lead_source).update(lead_source=None)

            lead_source.delete()
            messages.success(request, 'Lead source deleted successfully.')
            return redirect('crm_app:lead_source_list')
        except ProtectedError:
            messages.error(
                request,
                'Cannot delete this lead source because it is referenced by other records.'
            )
            return redirect('crm_app:lead_source_list')
        except IntegrityError as e:
            messages.error(
                request,
                f'Deletion failed due to database constraints: {str(e)}'
            )
            return redirect('crm_app:lead_source_list')
    return render(request, 'crm_app/lead_source_confirm_delete.html', {'lead_source': lead_source})


# Reasons
@login_required
def reason_list(request):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to manage reasons.")
        return redirect('crm_app:dashboard')
    reasons = Reason.objects.all()
    return render(request, 'crm_app/reason_list.html', {
        'reasons': reasons,
        'title': 'Reasons'
    })


@login_required
def reason_add(request):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to add reasons.")
        return redirect('crm_app:dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Reason.objects.create(
                name=name,
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'Reason created successfully.')
            return redirect('crm_app:reason_list')
    return render(request, 'crm_app/reason_form.html', {'title': 'Add Reason'})


@login_required
def reason_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit reasons.")
        return redirect('crm_app:dashboard')
    reason = get_object_or_404(Reason, pk=pk)
    if request.method == 'POST':
        reason.name = request.POST.get('name', reason.name)
        reason.description = request.POST.get('description', reason.description)
        reason.save()
        messages.success(request, 'Reason updated successfully.')
        return redirect('crm_app:reason_list')
    return render(request, 'crm_app/reason_form.html', {
        'reason': reason,
        'title': f'Edit Reason: {reason.name}'
    })


@login_required
def reason_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete reasons.")
        return redirect('crm_app:reason_list')
    reason = get_object_or_404(Reason, pk=pk)
    if request.method == 'POST':
        reason.delete()
        messages.success(request, 'Reason deleted successfully.')
        return redirect('crm_app:reason_list')
    return render(request, 'crm_app/reason_confirm_delete.html', {'reason': reason})


@login_required
def lead_update_reason(request, pk):
    """Update lead reason via AJAX with validation and logging"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Log request data for debugging
        logger.info(f"Reason update request data: {request.POST}")
        logger.info(f"Request user: {request.user}")
        
        lead = get_object_or_404(Lead, pk=pk)
        logger.info(f"Found lead: {lead.phone_number}, current reason: {lead.reason}")
        
        # Check permissions
        if not request.user.is_superuser and lead.created_by != request.user:
            logger.warning(f"Permission denied for user {request.user} on lead {lead.phone_number}")
            if not request.user.is_staff:
                return JsonResponse({'success': False, 'error': 'Permission denied'})

        reason_id = request.POST.get('reason_id')
        logger.info(f"New reason ID: {reason_id}")
        
        if not reason_id:
            logger.warning("No reason_id provided in request")
            return JsonResponse({'success': False, 'error': 'Missing reason ID'})
        
        try:
            reason = Reason.objects.get(pk=reason_id)
        except Reason.DoesNotExist:
            logger.warning(f"Reason with ID {reason_id} does not exist")
            return JsonResponse({'success': False, 'error': 'Invalid reason'})
        
        # Update the lead reason
        old_reason = lead.reason
        lead.reason = reason
        lead.save(update_fields=['reason', 'updated_date'])
        
        # Log the reason update
        logger.info(f"Lead {lead.phone_number} reason updated from {old_reason} to {reason} by {request.user}")
        
        # Create activity log
        ActivityLog.objects.create(
            user=request.user,
            activity_type='reason_update',
            content_object=lead,
            details=f'Reason updated to {reason.name}'
        )
        
        return JsonResponse({
            'success': True,
            'reason_id': reason.id,
            'reason_name': reason.name,
            'message': 'Reason updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating lead reason: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error updating reason: {str(e)}'
        })