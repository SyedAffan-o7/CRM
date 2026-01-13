from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from customers_app.models import Contact
from accounts_app.models import Account
from django.db.models import Q
from crm_app.forms import ContactForm
from .forms import CustomerImportForm
from django.db import transaction
from django.http import HttpResponse, JsonResponse
import csv
from django.views.decorators.http import require_POST
from activities_app.models import ActivityLog


# Customers (Contacts)
@login_required
def contact_list(request):
    """List all contacts"""
    if request.user.is_superuser:
        contacts = Contact.objects.all()
        print(f"DEBUG: Superuser viewing all {contacts.count()} contacts")
    else:
        # For non-superusers, show contacts they created OR contacts created by import (no created_by set)
        contacts = Contact.objects.filter(
            Q(created_by=request.user) |
            Q(created_by__isnull=True)
        )
        print(f"DEBUG: Regular user viewing {contacts.count()} contacts (created by them or imported)")

    # Search by name, phone, or company name
    search = request.GET.get('search', '').strip()
    if search:
        contacts = contacts.filter(
            Q(full_name__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(whatsapp_number__icontains=search) |
            Q(email__icontains=search) |
            Q(company__company_name__icontains=search)
        )
        print(f"DEBUG: Search '{search}' returned {contacts.count()} results")

    contacts = contacts.order_by('full_name')

    return render(request, 'crm_app/contact_list.html', {
        'contacts': contacts,
        'title': 'Contacts'
    })


@login_required
def contact_add(request):
    """Add new contact"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            # Template provides a standalone email input that's not part of ContactForm
            contact.email = request.POST.get('email', '').strip()
            contact.created_by = request.user
            contact.save()
            messages.success(request, 'Contact created successfully.')
            return redirect('crm_app:contact_list')
    else:
        form = ContactForm()

    return render(request, 'crm_app/contact_form.html', {
        'title': 'Add Contact',
        'form': form,
    })


@login_required
def contact_detail(request, pk):
    """Contact detail view"""
    contact = get_object_or_404(Contact, pk=pk)
    # Recent activities for sidebar (ActivityLog)
    activities = ActivityLog.objects.filter(contact=contact).order_by('-activity_date')[:10]
    return render(request, 'crm_app/contact_detail.html', {
        'contact': contact,
        'activities': activities,
        'title': f'Contact: {contact.full_name}'
    })


@login_required
def contact_edit(request, pk):
    """Edit contact"""
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        contact.full_name = request.POST.get('name', contact.full_name)
        contact.phone_number = request.POST.get('phone_number', contact.phone_number)
        contact.email = request.POST.get('email', contact.email)
        # company update can be added later
        contact.save()
        messages.success(request, 'Contact updated successfully.')
        return redirect('crm_app:contact_detail', pk=pk)

    return render(request, 'crm_app/contact_form.html', {
        'contact': contact,
        'title': f'Edit Contact: {contact.full_name}'
    })


@login_required
def customer_import(request):
    """Import customers from CSV/Excel file"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to import customers.")
        return redirect('crm_app:contact_list')

    if request.method == 'POST':
        form = CustomerImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                customers_data, errors = form.process_file()

                # Debug logging
                print(f"DEBUG: Found {len(customers_data)} customers to process")
                print(f"DEBUG: Found {len(errors)} errors")

                if errors:
                    # Show errors but continue with valid data
                    for error in errors[:10]:  # Show first 10 errors
                        messages.warning(request, error)
                        print(f"DEBUG: Error - {error}")
                        messages.warning(request, f"... and {len(errors) - 10} more errors")

                if customers_data:
                    created_count = 0
                    updated_count = 0
                    skipped_count = 0
                    skipped_rows = []
                    skipped_details = []

                    # First pass: Check for existing data and collect warnings
                    existing_contacts = []
                    existing_companies = []

                    for i, customer_data in enumerate(customers_data):
                        try:
                            # Check if contact already exists by phone number
                            existing_contact = Contact.objects.filter(
                                phone_number=customer_data['phone_number']
                            ).first()

                            if existing_contact:
                                existing_contacts.append({
                                    'row': customer_data['row_number'],
                                    'name': customer_data['full_name'],
                                    'phone': customer_data['phone_number']
                                })
                                continue

                            # Check if company already exists (if company_name provided)
                            if customer_data['company_name']:
                                existing_company = Account.objects.filter(
                                    company_name=customer_data['company_name']
                                ).first()
                                if existing_company:
                                    existing_companies.append({
                                        'row': customer_data['row_number'],
                                        'company': customer_data['company_name']
                                    })

                        except Exception as e:
                            print(f"DEBUG: Error checking existing data for row {customer_data['row_number']}: {e}")

                    # Show warnings for existing data
                    if existing_contacts:
                        messages.warning(
                            request,
                            f"Warning: {len(existing_contacts)} contacts with existing phone numbers will be skipped. "
                            f"Rows: {', '.join([str(item['row']) for item in existing_contacts[:5]])}{'...' if len(existing_contacts) > 5 else ''}"
                        )
                        print(f"DEBUG: Found {len(existing_contacts)} existing contacts")

                    if existing_companies:
                        messages.warning(
                            request,
                            f"Warning: {len(existing_companies)} companies with existing names will be skipped. "
                            f"Rows: {', '.join([str(item['row']) for item in existing_companies[:5]])}{'...' if len(existing_companies) > 5 else ''}"
                        )
                        print(f"DEBUG: Found {len(existing_companies)} existing companies")

                    # Second pass: Process valid data
                    with transaction.atomic():
                        for i, customer_data in enumerate(customers_data):
                            try:
                                print(f"DEBUG: Processing customer {i+1}: {customer_data}")

                                # Check if contact already exists by phone number
                                existing_contact = Contact.objects.filter(
                                    phone_number=customer_data['phone_number']
                                ).first()

                                if existing_contact:
                                    # Skip this row - customer already exists
                                    skipped_count += 1
                                    skipped_rows.append(customer_data['row_number'])
                                    skipped_details.append({
                                        'row': customer_data['row_number'],
                                        'reason': f"Contact with phone number {customer_data['phone_number']} already exists"
                                    })
                                    print(f"DEBUG: Skipping existing customer: {existing_contact.full_name} (phone: {customer_data['phone_number']})")
                                    continue

                                # Check if company already exists (if company_name provided)
                                if customer_data['company_name']:
                                    existing_company = Account.objects.filter(
                                        company_name=customer_data['company_name']
                                    ).first()
                                    if existing_company:
                                        skipped_count += 1
                                        skipped_rows.append(customer_data['row_number'])
                                        skipped_details.append({
                                            'row': customer_data['row_number'],
                                            'reason': f"Company '{customer_data['company_name']}' already exists"
                                        })
                                        print(f"DEBUG: Skipping row due to existing company: {customer_data['company_name']}")
                                        continue

                                # Create new contact
                                print(f"DEBUG: Creating new customer: {customer_data['full_name']}")
                                new_contact = Contact(
                                    full_name=customer_data['full_name'],
                                    phone_number=customer_data['phone_number'],
                                    email=customer_data['email'],
                                    created_by=None  # Make imported contacts visible to all users
                                )

                                # Handle company
                                if customer_data['company_name']:
                                    # Generate a unique phone number for the Account since it's the primary key
                                    import time
                                    # Create a unique phone number based on company name and timestamp
                                    company_phone_base = customer_data['company_name'].replace(' ', '').lower()
                                    timestamp = str(int(time.time() * 1000))[-8:]  # Last 8 digits of timestamp
                                    company_phone = f"ACC{company_phone_base[:8]}{timestamp}"[:20]  # Max 20 chars

                                    # Ensure uniqueness by checking if it exists
                                    counter = 1
                                    original_phone = company_phone
                                    while Account.objects.filter(phone_number=company_phone).exists():
                                        company_phone = f"{original_phone[:17]}{counter:03d}"
                                        counter += 1
                                        if counter > 999:
                                            # Fallback to random if we somehow get too many duplicates
                                            import random
                                            company_phone = f"ACC{random.randint(100000, 999999)}"

                                    company, created = Account.objects.get_or_create(
                                        phone_number=company_phone,
                                        defaults={
                                            'company_name': customer_data['company_name'],
                                            'created_by': request.user
                                        }
                                    )
                                    new_contact.company = company

                                new_contact.save()
                                created_count += 1
                                print(f"DEBUG: Created contact {new_contact.full_name}")

                            except Exception as e:
                                error_msg = f"Error processing row {customer_data['row_number']}: {str(e)}"
                                messages.error(request, error_msg)
                                print(f"DEBUG: Exception - {error_msg}")

                    # Success messages with detailed feedback
                    if created_count > 0:
                        messages.success(request, f"Successfully created {created_count} new customers.")
                        print(f"DEBUG: Created {created_count} customers")

                    if skipped_count > 0:
                        # Show detailed information about skipped rows
                        skipped_info = []
                        for detail in skipped_details[:10]:  # Show first 10 details
                            skipped_info.append(f"Row {detail['row']}: {detail['reason']}")

                        if len(skipped_details) > 10:
                            skipped_info.append(f"... and {len(skipped_details) - 10} more")

                        messages.warning(
                            request,
                            f"Skipped {skipped_count} rows due to existing data:\n" +
                            "\n".join(skipped_info)
                        )
                        print(f"DEBUG: Skipped {skipped_count} customers due to existing data")

                    if created_count == 0 and skipped_count == 0:
                        messages.info(request, "No new data to import - all records already exist or file was empty.")

                    return redirect('crm_app:contact_list')
                else:
                    messages.error(request, "No valid customer data found in the file.")
                    print("DEBUG: No valid customer data found")
            except Exception as e:
                error_msg = f"Error processing file: {str(e)}"
                messages.error(request, error_msg)
                print(f"DEBUG: File processing error - {error_msg}")
        else:
            # Form validation errors
            print("DEBUG: Form validation errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"DEBUG: {field}: {error}")
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomerImportForm()

    return render(request, 'customers_app/customer_import.html', {
        'form': form,
        'title': 'Import Customers'
    })


@login_required
def download_sample_csv(request):
    """Download sample CSV file for customer import"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to download sample files.")
        return redirect('crm_app:contact_list')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_import_sample.csv"'

    writer = csv.writer(response)
    writer.writerow(['full_name', 'phone_number', 'email', 'company_name'])
    writer.writerow(['John Doe', '+1234567890', 'john@example.com', 'ABC Company'])
    writer.writerow(['Jane Smith', '+0987654321', 'jane@company.com', 'XYZ Corp'])
    writer.writerow(['Bob Johnson', '+1122334455', '', 'Tech Solutions'])

    return response


@require_POST
@login_required
def log_activity_for_contact(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    try:
        # Map incoming method to ActivityLog.activity_type choices
        method = (request.POST.get('method') or '').upper()
        if method == 'EMAIL':
            activity_type = 'email'
            subject_label = 'Email'
        elif method in ('MEETING', 'VIDEO_CALL'):
            activity_type = 'meeting'
            subject_label = 'Meeting'
        elif method == 'PHONE' or method == 'SMS':
            activity_type = 'call'
            subject_label = 'Phone Call'
        else:
            activity_type = 'note'
            subject_label = 'Note'

        summary = request.POST.get('summary', '')
        outcome = request.POST.get('outcome', '')
        next_step = request.POST.get('next_step', '')
        next_step_date = request.POST.get('next_step_date') or None

        details_parts = []
        if outcome:
            details_parts.append(f"Outcome: {outcome}")
        if next_step:
            details_parts.append(f"Next: {next_step}")
        if next_step_date:
            details_parts.append(f"Next date: {next_step_date}")
        details_text = ' | '.join(details_parts) if details_parts else None

        activity = ActivityLog.objects.create(
            contact=contact,
            user=request.user,
            activity_type=activity_type,
            subject=subject_label,
            description=summary or None,
            details=details_text,
        )
        return JsonResponse({'ok': True, 'message': 'Activity logged successfully.', 'activity_id': activity.id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
