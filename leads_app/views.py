import logging
import requests
import pandas as pd
import io
from products.models import Category, Subcategory
from leads_app.models import Lead, Reason, LeadSource, Product, LeadProduct
from customers_app.models import Contact
from accounts_app.models import Account
from deals_app.models import Deal
from crm_app.forms import LeadForm, ContactForm, AccountForm, DealForm, ActivityLogForm
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.conf import settings
from django.db.models import Q, ProtectedError
from django.db import IntegrityError
from datetime import datetime, timedelta
from .models import Lead, FollowUp
from outbound_app.models import OutboundActivity
from activities_app.models import ActivityLog
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import FollowUpForm, FollowUpStatusForm

def google_drive_url(url):
    """
    Convert Google Drive sharing link to thumbnail URL for better embedding reliability.
    Input: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    Output: https://drive.google.com/thumbnail?id=FILE_ID&sz=w400 (thumbnail format)
    """
    import logging
    logger = logging.getLogger(__name__)

    if not url or not isinstance(url, str):
        logger.warning(f"Invalid URL provided: {url}")
        return url

    # Skip invalid entries like "No Photo"
    if url.strip().lower() in ['no photo', 'n/a', 'none', '']:
        logger.warning(f"Skipping invalid image URL entry: {url}")
        return None  # Return None to indicate invalid URL

    logger.info(f"Processing Google Drive URL: {url}")

    # Check if it's a Google Drive sharing link
    if 'drive.google.com/file/d/' in url and '/view?usp=sharing' in url:
        # Extract file ID from the URL
        start = url.find('/file/d/') + 8
        end = url.find('/view?usp=sharing')
        if start != -1 and end != -1 and start < end:
            file_id = url[start:end]

            # Use thumbnail URL instead of uc?export=view for better embedding
            # Thumbnail URLs are more reliable for web embedding
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
            logger.info(f"✅ Converted Google Drive URL to thumbnail: {url} -> {thumbnail_url}")
            return thumbnail_url

    # Check if it's already a thumbnail URL
    if 'drive.google.com/thumbnail?' in url and 'id=' in url:
        logger.info(f"✅ Already a thumbnail URL: {url}")
        return url

    # Check if it's already a direct Google Drive URL (convert to thumbnail)
    if 'drive.google.com/uc?' in url and 'id=' in url:
        # Extract file ID and convert to thumbnail
        id_start = url.find('id=') + 3
        id_end = url.find('&', id_start) if '&' in url[id_start:] else len(url)
        if id_start != -1:
            file_id = url[id_start:id_end]
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
            logger.info(f"✅ Converted uc URL to thumbnail: {url} -> {thumbnail_url}")
            return thumbnail_url

    # Return original URL if not a Google Drive link
    logger.warning(f"❌ Not a recognized Google Drive URL format: {url}")
    return url

logger = logging.getLogger(__name__)


def get_or_create_reasons():
    reasons_qs = Reason.objects.all()
    if reasons_qs.exists():
        return reasons_qs

    default_names = [
        'Price too high',
        'Chose competitor',
        'No response from customer',
        'Budget constraints',
        'Product not suitable',
        'Other',
    ]

    for name in default_names:
        Reason.objects.get_or_create(name=name, defaults={'description': ''})

    return Reason.objects.all()


def get_or_create_lead_sources():
    """Ensure default lead sources exist"""
    sources_qs = LeadSource.objects.filter(is_active=True)
    if sources_qs.exists():
        return sources_qs

    default_sources = [
        {'name': 'WhatsApp', 'description': 'Leads from WhatsApp messages'},
        {'name': 'Call', 'description': 'Phone call enquiries'},
        {'name': 'Email', 'description': 'Email enquiries'},
        {'name': 'Website', 'description': 'Website contact form'},
        {'name': 'Referral', 'description': 'Customer referrals'},
        {'name': 'Social Media', 'description': 'Facebook, Instagram, LinkedIn'},
        {'name': 'Walk-in', 'description': 'Walk-in customers'},
        {'name': 'Other', 'description': 'Other sources'},
    ]

    for source_data in default_sources:
        LeadSource.objects.get_or_create(
            name=source_data['name'],
            defaults={'description': source_data['description'], 'is_active': True}
        )

    return LeadSource.objects.filter(is_active=True)


def get_leadproduct_attribute_suggestions():
    def distinct_values(field_name):
        return list(
            LeadProduct.objects
            .exclude(**{f"{field_name}__isnull": True})
            .exclude(**{field_name: ""})
            .values_list(field_name, flat=True)
            .distinct()
            .order_by(field_name)
        )

    return {
        'size_options': distinct_values('size'),
        'color_options': distinct_values('color'),
        'model_options': distinct_values('model'),
        'brand_options': distinct_values('brand'),
        'ankle_options': distinct_values('ankle'),
        'material_options': distinct_values('material'),
        'people_options': distinct_values('people'),
    }


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
    try:
        if request.user.is_superuser:
            leads = Lead.objects.select_related('assigned_sales_person', 'created_by').all()
        else:
            leads = Lead.objects.select_related('assigned_sales_person', 'created_by').filter(assigned_sales_person=request.user)

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

        # Date filtering
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            leads = leads.filter(created_date__date__gte=from_date)
        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            leads = leads.filter(created_date__date__lte=to_date)

        # Tab filter: main vs fulfilled vs pending_requests (salesperson) vs assigned (admin)
        current_tab = request.GET.get('tab') or 'main'
        if current_tab == 'fulfilled':
            leads = leads.filter(lead_status='fulfilled')
        elif current_tab == 'pending_requests' and not request.user.is_superuser:
            leads = leads.filter(assignment_status='pending', assigned_sales_person=request.user)
        elif current_tab == 'assigned' and request.user.is_superuser:
            # Show all enquiries that have ever been assigned a status
            leads = Lead.objects.select_related('assigned_sales_person', 'created_by').filter(
                assignment_status__isnull=False
            )
        else:
            # Main tab: exclude fulfilled enquiries
            # For sales users, also hide those awaiting their acceptance
            q = ~Q(lead_status='fulfilled')
            if not request.user.is_superuser:
                q &= ~Q(assignment_status='pending', assigned_sales_person=request.user)
            leads = leads.filter(q)

        leads = leads.order_by('-created_date')

        paginator = Paginator(leads, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        owners = User.objects.filter(created_leads__isnull=False).distinct().order_by('first_name', 'last_name', 'username')

        if request.user.is_superuser:
            countries = Lead.objects.exclude(country='').values_list('country', flat=True).distinct().order_by('country')
        else:
            countries = Lead.objects.filter(assigned_sales_person=request.user).exclude(country='').values_list('country', flat=True).distinct().order_by('country')

        # Counts for tabs
        if request.user.is_superuser:
            fulfilled_count = Lead.objects.filter(lead_status='fulfilled').count()
            main_count = Lead.objects.filter(is_pending_review=False).exclude(lead_status='fulfilled').count()
            assigned_count = Lead.objects.filter(assignment_status__isnull=False).count()
            pending_requests_count = 0
        else:
            fulfilled_count = Lead.objects.filter(lead_status='fulfilled', assigned_sales_person=request.user).count()
            main_count = Lead.objects.filter(is_pending_review=False, assigned_sales_person=request.user).exclude(lead_status='fulfilled').exclude(
                assignment_status='pending'
            ).count()
            pending_requests_count = Lead.objects.filter(assignment_status='pending', assigned_sales_person=request.user).count()
            assigned_count = 0

        # Get follow-ups (only pending for sidebar display)
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
            'leads': page_obj,
            'page_obj': page_obj,
            'status_choices': Lead.STATUS_CHOICES,
            'stage_choices': Lead.ENQUIRY_STAGE_CHOICES,
            'owners': owners,
            'countries': countries,
            'reasons': get_or_create_reasons(),
            'from_date': from_date.strftime('%Y-%m-%d') if from_date else '',
            'to_date': to_date.strftime('%Y-%m-%d') if to_date else '',
            'current_tab': current_tab,
            'fulfilled_count': fulfilled_count,
            'main_count': main_count,
            'pending_requests_count': pending_requests_count,
            'assigned_count': assigned_count,
            'overdue_followups': overdue_followups,
            'today_followups': today_followups,
            'upcoming_followups': upcoming_followups,
            'overdue_followups_count': len(overdue_followups),
            'today_followups_count': len(today_followups),
        }
        return render(request, 'crm_app/lead_list.html', context)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in lead_list view: {str(e)}", exc_info=True)
        # Return a simple error page instead of 503
        return render(request, 'crm_app/error.html', {
            'error_title': 'Database Error',
            'error_message': f'An error occurred while loading the enquiries: {str(e)}'
        })


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
    
    # Get other enquiries for the same contact (enquiry history)
    if lead.contact:
        enquiry_history = Lead.objects.filter(
            contact=lead.contact
        ).select_related('assigned_sales_person', 'created_by').order_by('-created_date')
    else:
        enquiry_history = Lead.objects.none()

    # Get activities for this lead
    activities = ActivityLog.objects.filter(
        content_type__model='lead',
        object_id=lead.pk
    ).select_related('user').order_by('-activity_date')[:10]
    
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
    
    # Dropdown data
    reasons = get_or_create_reasons()
    # Show active users for assignment dropdown
    sales_users = User.objects.filter(is_active=True).order_by('first_name', 'username')

    # Dropdown data for quick-add modal (categories/subcategories)
    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True).select_related('category')

    # Get current enquiry products (combine old and new product systems)
    current_products = []

    # Get products from new LeadProduct model (with images, detailed info)
    lead_products = LeadProduct.objects.filter(lead=lead).select_related('category', 'subcategory')
    for lp in lead_products:
        current_products.append({
            'id': lp.id,
            'category': lp.category,
            'subcategory': lp.subcategory,
            'quantity': lp.quantity,
            'price': lp.price,
            'image': lp.image,
            'size': lp.size,
            'color': lp.color,
            'model': lp.model,
            'brand': lp.brand,
            'ankle': lp.ankle,
            'material': lp.material,
            'people': lp.people,
            'source': 'lead_product'
        })

    # Get products from old products_enquired ManyToManyField
    for product in lead.products_enquired.all():
        # Only add if not already present from LeadProduct
        if not any(cp.get('category') and cp['category'].name == product.name for cp in current_products):
            current_products.append({
                'id': product.id,
                'category': None,  # Old Product model doesn't have category FK
                'subcategory': None,
                'quantity': None,  # Old model doesn't have quantity
                'price': None,     # Old model doesn't have price
                'image': None,     # Old model doesn't have images
                'product_name': product.name,  # Use name from old model
                'source': 'old_product'
            })

    # Process Google Drive URL if present
    processed_image_url = google_drive_url(lead.image_url) if lead.image_url else None

    context = {
        'lead': lead,
        'follow_ups': follow_ups,
        'followup_form': followup_form,
        'status_form': status_form,
        'outbound_activities': outbound_activities,
        'enquiry_history': enquiry_history,
        'activities': activities,
        'reasons': reasons,
        'sales_users': sales_users,
        'categories': categories,
        'subcategories': subcategories,
        'current_products': current_products,
        'processed_image_url': processed_image_url,
    }
    
    return render(request, 'crm_app/lead_detail.html', context)


@login_required
@require_POST
def lead_quick_add(request, pk):
    """
    Create a new enquiry for the SAME contact/person as the given lead (pk),
    without asking for contact fields. Accepts only product fields and optional notes.
    """
    source_lead = get_object_or_404(Lead, pk=pk)

    # Permissions: superuser or assigned_sales_person matches current user
    if not request.user.is_superuser and source_lead.assigned_sales_person != request.user:
        messages.error(request, 'You do not have permission to create an enquiry for this contact.')
        return redirect('crm_app:lead_detail', pk=source_lead.pk)

    # Create a new lead copying identity details from the source lead/contact
    new_lead = Lead(
        contact=source_lead.contact,
        contact_name=source_lead.contact_name,
        phone_number=source_lead.phone_number,
        company_name=source_lead.company_name,
        created_by=request.user,
        assigned_sales_person=source_lead.assigned_sales_person or request.user,
        lead_source=source_lead.lead_source,
    )

    # Attempt to infer country from phone number similar to lead_add
    phone_number = new_lead.phone_number
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
            new_lead.country = country

    # Save the new lead first (mark as pending review)
    new_lead.is_pending_review = True
    new_lead.enquiry_stage = 'enquiry_received'
    new_lead.lead_status = 'not_fulfilled'
    new_lead.save()

    # Parse product fields (single or multiple entries arrays)
    categories_list = request.POST.getlist('categories[]') or request.POST.getlist('categories')
    subcategories_list = request.POST.getlist('subcategories[]') or request.POST.getlist('subcategories')
    quantities_list = request.POST.getlist('quantities[]') or request.POST.getlist('quantities')
    prices_list = request.POST.getlist('prices[]') or request.POST.getlist('prices')

    # Collect newly uploaded images by index (product_images_0, product_images_1, ...)
    images_by_index = {}
    for i in range(len(categories_list)):
        file_key = f'product_images_{i}'
        if file_key in request.FILES:
            images_by_index[i] = request.FILES[file_key]

    # Create LeadProduct entries
    for i, category_id in enumerate(categories_list):
        # Gather potential fields for this row
        qty_val = quantities_list[i] if i < len(quantities_list) else ''
        price_val = prices_list[i] if i < len(prices_list) else ''
        img_val = images_by_index.get(i)

        # Decide whether this row has any meaningful content
        has_any_content = bool((category_id and str(category_id).strip()) or (qty_val and str(qty_val).strip()) or (price_val and str(price_val).strip()) or img_val)

        if not has_any_content:
            continue

        lp = LeadProduct(lead=new_lead)

        # Optional category
        if category_id:
            try:
                lp.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass

        # Optional subcategory
        if i < len(subcategories_list) and subcategories_list[i]:
            try:
                lp.subcategory = Subcategory.objects.get(id=subcategories_list[i])
            except Subcategory.DoesNotExist:
                pass

        # Optional quantity
        if i < len(quantities_list) and quantities_list[i]:
            try:
                lp.quantity = int(quantities_list[i])
            except ValueError:
                lp.quantity = None

        # Optional price
        if i < len(prices_list) and prices_list[i]:
            lp.price = prices_list[i]

        # Optional image
        if img_val:
            lp.image = img_val

        lp.save()

    # Optional quick notes
    quick_notes = request.POST.get('notes')
    if quick_notes:
        new_lead.notes = quick_notes
        new_lead.save(update_fields=['notes'])

    ActivityLog.objects.create(
        lead=new_lead,
        activity_type='note',
        subject='Lead created (quick add)',
        description=f'Quick enquiry created for {new_lead.contact_name}',
        user=request.user
    )

    messages.success(request, 'New enquiry created for this contact!')
    return redirect('crm_app:lead_list')


@login_required
@require_POST
def lead_accept(request, pk):
    """Accept a pending enquiry and move it to main enquiries."""
    lead = get_object_or_404(Lead, pk=pk)
    # Permission: superuser or creator
    if not (request.user.is_superuser or lead.created_by == request.user or lead.assigned_sales_person == request.user):
        messages.error(request, 'You do not have permission to accept this enquiry.')
        return redirect('crm_app:lead_list')
    lead.is_pending_review = False
    lead.save(update_fields=['is_pending_review'])
    ActivityLog.objects.create(
        lead=lead,
        user=request.user,
        activity_type='note',
        subject='Enquiry accepted',
        description='Pending enquiry approved and moved to main list.'
    )
    messages.success(request, 'Enquiry accepted and moved to main list.')
    return redirect('crm_app:lead_list')


@login_required
@require_POST
def lead_reject(request, pk):
    """Reject a pending enquiry. Currently deletes it."""
    lead = get_object_or_404(Lead, pk=pk)
    if not (request.user.is_superuser or lead.created_by == request.user or lead.assigned_sales_person == request.user):
        messages.error(request, 'You do not have permission to reject this enquiry.')
        return redirect('crm_app:lead_list')
    # Log and delete
    ActivityLog.objects.create(
        user=request.user,
        activity_type='note',
        subject='Enquiry rejected',
        description=f'Pending enquiry for {lead.contact_name} was rejected.'
    )
    lead.delete()
    messages.success(request, 'Enquiry rejected and removed.')
    return redirect('crm_app:lead_list')


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
        form = LeadForm(request.POST, request.FILES, user=request.user)
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
                    logger.warning(f"Failed to auto-create contact for lead {lead.contact_name}: {str(e)}")

            # If superuser assigns a salesperson on create, mark as pending assignment
            if request.user.is_superuser:
                if lead.assigned_sales_person_id:
                    if lead.assigned_sales_person != request.user:
                        lead.assignment_status = 'pending'
                    else:
                        lead.assignment_status = None
                else:
                    lead.assignment_status = None

            # Persist lead with defensive FK validation to avoid FK constraint failures
            try:
                lead.save()
            except IntegrityError as e:
                logger.warning(f"Lead save FK failure, attempting to sanitize FKs: {e}")
                # Validate each optional FK; if target doesn't exist, null it and retry once
                try:
                    if lead.contact_id and not Contact.objects.filter(pk=getattr(lead.contact, 'pk', None) or lead.contact_id).exists():
                        lead.contact = None
                    if lead.lead_source_id and not LeadSource.objects.filter(pk=lead.lead_source_id).exists():
                        lead.lead_source = None
                    if lead.reason_id and not Reason.objects.filter(pk=lead.reason_id).exists():
                        lead.reason = None
                    if lead.category_id and not Category.objects.filter(pk=lead.category_id).exists():
                        lead.category = None
                    if lead.subcategory_id and not Subcategory.objects.filter(pk=lead.subcategory_id).exists():
                        lead.subcategory = None
                    if lead.assigned_sales_person_id and not User.objects.filter(pk=lead.assigned_sales_person_id).exists():
                        lead.assigned_sales_person = None
                except Exception as v_err:
                    logger.error(f"Error while validating FKs before retrying lead save: {v_err}")
                
                try:
                    lead.save()
                except IntegrityError as e2:
                    logger.error(f"Lead save failed after FK sanitization: {e2}")
                    messages.error(request, 'Could not save the enquiry due to invalid references. Please review selected dropdowns and try again.')
                    attr_suggestions = get_leadproduct_attribute_suggestions()
                    context = {
                        'form': form,
                        'title': 'Add New Enquiry',
                        'categories': Category.objects.filter(is_active=True),
                        'subcategories': Subcategory.objects.filter(is_active=True).select_related('category'),
                    }
                    context.update(attr_suggestions)
                    return render(request, 'crm_app/lead_form.html', context)

            activity_id = request.session.pop('from_outbound_activity_id', None)
            if activity_id:
                try:
                    activity = OutboundActivity.objects.select_related('contact').get(pk=activity_id)
                    activity.lead = lead
                    try:
                        activity.save(update_fields=['lead'])
                    except Exception:
                        activity.save()
                except OutboundActivity.DoesNotExist:
                    pass

            # Handle post-save operations with error handling
            try:
                categories = request.POST.getlist('categories[]')
                categories_text = request.POST.getlist('categories_text[]')
                subcategories = request.POST.getlist('subcategories[]')
                quantities = request.POST.getlist('quantities[]')
                prices = request.POST.getlist('prices[]')
                attr_sizes = request.POST.getlist('attr_size[]')
                attr_colors = request.POST.getlist('attr_color[]')
                attr_models = request.POST.getlist('attr_model[]')
                attr_brands = request.POST.getlist('attr_brand[]')
                attr_ankles = request.POST.getlist('attr_ankle[]')
                attr_materials = request.POST.getlist('attr_material[]')
                attr_peoples = request.POST.getlist('attr_people[]')

                # Determine total rows by max length across arrays to avoid skipping rows without category
                total_rows = max(
                    len(categories),
                    len(categories_text),
                    len(subcategories),
                    len(quantities),
                    len(prices),
                    len(attr_sizes),
                    len(attr_colors),
                    len(attr_models),
                    len(attr_brands),
                    len(attr_ankles),
                    len(attr_materials),
                    len(attr_peoples),
                    1,
                )

                # Collect newly uploaded images (product_images_0..N)
                images_by_index = {}
                logger.debug(f"Request FILES on add: {request.FILES}")
                for i in range(total_rows):
                    file_key = f'product_images_{i}'
                    if file_key in request.FILES:
                        images_by_index[i] = request.FILES[file_key]
                        logger.debug(f"Found image for index {i} on add: {request.FILES[file_key].name}")

                for i in range(total_rows):
                    category_id = categories[i] if i < len(categories) else ''
                    category_text = categories_text[i].strip() if i < len(categories_text) and categories_text[i] is not None else ''
                    subcat_id = subcategories[i] if i < len(subcategories) else ''
                    qty_val = quantities[i] if i < len(quantities) else ''
                    price_val = prices[i] if i < len(prices) else ''
                    size_val = attr_sizes[i] if i < len(attr_sizes) else ''
                    color_val = attr_colors[i] if i < len(attr_colors) else ''
                    model_val = attr_models[i] if i < len(attr_models) else ''
                    brand_val = attr_brands[i] if i < len(attr_brands) else ''
                    ankle_val = attr_ankles[i] if i < len(attr_ankles) else ''
                    material_val = attr_materials[i] if i < len(attr_materials) else ''
                    people_val = attr_peoples[i] if i < len(attr_peoples) else ''
                    img_val = images_by_index.get(i)

                    has_any_content = bool(
                        (category_id and str(category_id).strip())
                        or (subcat_id and str(subcat_id).strip())
                        or (qty_val and str(qty_val).strip())
                        or (price_val and str(price_val).strip())
                        or (size_val and str(size_val).strip())
                        or (color_val and str(color_val).strip())
                        or (model_val and str(model_val).strip())
                        or (brand_val and str(brand_val).strip())
                        or (ankle_val and str(ankle_val).strip())
                        or (material_val and str(material_val).strip())
                        or (people_val and str(people_val).strip())
                        or img_val
                    )
                    if not has_any_content:
                        continue

                    lead_product = LeadProduct(lead=lead)
                    # Optional category: prefer typed name over dropdown when provided
                    if category_text:
                        try:
                            category_obj, _created = Category.objects.get_or_create(name=category_text, defaults={'created_by': request.user})
                            lead_product.category = category_obj
                        except Exception:
                            pass
                    elif category_id:
                        try:
                            lead_product.category = Category.objects.get(id=category_id)
                        except Category.DoesNotExist:
                            pass
                    # Optional subcategory
                    if subcat_id:
                        try:
                            lead_product.subcategory = Subcategory.objects.get(id=subcat_id)
                        except Subcategory.DoesNotExist:
                            pass
                    # Optional fields
                    if qty_val:
                        try:
                            lead_product.quantity = int(qty_val)
                        except ValueError:
                            lead_product.quantity = None
                    if price_val:
                        lead_product.price = price_val
                    if size_val:
                        lead_product.size = size_val
                    if color_val:
                        lead_product.color = color_val
                    if model_val:
                        lead_product.model = model_val
                    if brand_val:
                        lead_product.brand = brand_val
                    if ankle_val:
                        lead_product.ankle = ankle_val
                    if material_val:
                        lead_product.material = material_val
                    if people_val:
                        lead_product.people = people_val
                    if img_val:
                        lead_product.image = img_val
                        logger.debug(f"Assigning image {lead_product.image.name} to product {i} on add")
                    try:
                        lead_product.save()
                    except Exception as e:
                        logger.error(f"S3 PutObject failed for product row {i}: {str(e)}", exc_info=True)
                        messages.warning(request, f"Image upload failed for product {i+1}: {str(e)}")
                        # Save entry without image so other data persists
                        try:
                            lead_product.image = None
                            lead_product.save()
                        except Exception as e2:
                            logger.error(f"Failed to save LeadProduct without image for row {i}: {str(e2)}", exc_info=True)

                ActivityLog.objects.create(
                    lead=lead,
                    activity_type='note',
                    subject='Lead created',
                    description=f'New enquiry created for {lead.contact_name}',
                    user=request.user
                )

                messages.success(request, 'Enquiry created successfully!')
                return redirect('crm_app:lead_list')
            
            except Exception as e:
                logger.error(f"Error during post-save operations for lead: {str(e)}", exc_info=True)
                messages.error(request, 'Enquiry was created but some operations failed. Please check the enquiry details.')
                return redirect('crm_app:lead_detail', pk=lead.pk)
    else:
        # Ensure default lead sources exist
        get_or_create_lead_sources()
        
        # Prefill form from Contact when contact_id provided
        contact_id = request.GET.get('contact_id')
        initial = {}
        if contact_id:
            try:
                contact_obj = Contact.objects.select_related('company').get(pk=contact_id)
                company_name = ''
                try:
                    if contact_obj.company:
                        company_name = contact_obj.company.company_name
                except Account.DoesNotExist:
                    company_name = ''  # Handle broken foreign key

                initial.update({
                    'contact_name': contact_obj.full_name,
                    'phone_number': contact_obj.phone_number,
                    'company_name': company_name,
                })
                # Persist for POST handling
                request.session['prefill_contact_id'] = contact_obj.pk
            except Contact.DoesNotExist:
                pass

        activity_id = request.session.get('from_outbound_activity_id')
        if activity_id:
            try:
                activity = OutboundActivity.objects.select_related('contact').get(pk=activity_id)

                if activity.summary and 'notes' not in initial:
                    initial['notes'] = activity.summary

                if activity.next_step and activity.next_step != 'NONE' and 'next_action' not in initial:
                    initial['next_action'] = activity.get_next_step_display()

                if activity.contact and 'phone_number' not in initial:
                    if not initial.get('contact_name'):
                        initial['contact_name'] = activity.contact.full_name
                    initial['phone_number'] = activity.contact.phone_number
            except OutboundActivity.DoesNotExist:
                pass

        if initial:
            form = LeadForm(initial=initial, user=request.user)
        else:
            form = LeadForm(user=request.user)

    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True).select_related('category')
    attr_suggestions = get_leadproduct_attribute_suggestions()

    context = {
        'form': form,
        'title': 'Add New Enquiry',
        'categories': categories,
        'subcategories': subcategories,
    }
    context.update(attr_suggestions)

    return render(request, 'crm_app/lead_form.html', context)
@login_required
def lead_edit(request, pk):
    if request.user.is_superuser:
        lead = get_object_or_404(Lead, pk=pk)
    else:
        lead = get_object_or_404(Lead, pk=pk, created_by=request.user)

    if request.method == 'POST':
        # Add extensive logging for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"=== LEAD EDIT POST DEBUG ===")
        logger.error(f"POST data keys: {list(request.POST.keys())}")
        logger.error(f"FILES keys: {list(request.FILES.keys()) if request.FILES else 'No files'}")
        logger.error(f"User: {request.user}")
        
        try:
            # Capture previous assignee before binding form
            previous_assignee_id = lead.assigned_sales_person_id
            form = LeadForm(request.POST, request.FILES, instance=lead, user=request.user)
            logger.error(f"Form is_valid: {form.is_valid()}")
            if not form.is_valid():
                logger.error(f"Form errors: {form.errors}")
                logger.error(f"Non-field errors: {form.non_field_errors()}")
                attr_suggestions = get_leadproduct_attribute_suggestions()
                context = {
                    'form': form,
                    'title': 'Edit Enquiry',
                    'lead': lead,
                    'categories': Category.objects.filter(is_active=True),
                    'subcategories': Subcategory.objects.filter(is_active=True).select_related('category'),
                }
                context.update(attr_suggestions)
                return render(request, 'crm_app/lead_form.html', context)
            
            logger.error("Form is valid, proceeding with save...")
            lead = form.save(commit=False)

            # Handle product data (similar to lead_add)
            logger.error("Processing LeadProduct data...")
            categories = request.POST.getlist('categories[]')
            categories_text = request.POST.getlist('categories_text[]')
            subcategories = request.POST.getlist('subcategories[]')
            quantities = request.POST.getlist('quantities[]')
            prices = request.POST.getlist('prices[]')
            attr_sizes = request.POST.getlist('attr_size[]')
            attr_colors = request.POST.getlist('attr_color[]')
            attr_models = request.POST.getlist('attr_model[]')
            attr_brands = request.POST.getlist('attr_brand[]')
            attr_ankles = request.POST.getlist('attr_ankle[]')
            attr_materials = request.POST.getlist('attr_material[]')
            attr_peoples = request.POST.getlist('attr_people[]')
            existing_ids = request.POST.getlist('lead_product_ids[]')
            # Collect newly uploaded images by index (product_images_0, product_images_1, ...)
            images_by_index = {}
            for i in range(max(len(categories), len(categories_text))):
                file_key = f'product_images_{i}'
                if file_key in request.FILES:
                    images_by_index[i] = request.FILES[file_key]

            logger.error(f"Categories: {categories}")
            logger.error(f"Existing IDs: {existing_ids}")
            logger.error(f"Images: {list(images_by_index.keys())}")

            # Map previous images by index from existing LeadProduct IDs BEFORE deletion
            prev_images_by_index = {}
            for i, lp_id in enumerate(existing_ids):
                if lp_id:
                    try:
                        prev_lp = LeadProduct.objects.get(id=lp_id, lead=lead)
                        if getattr(prev_lp, 'image', None):
                            prev_images_by_index[i] = prev_lp.image
                    except LeadProduct.DoesNotExist:
                        pass

            # Clear existing LeadProduct entries for this lead
            logger.error("Deleting existing LeadProduct objects...")
            LeadProduct.objects.filter(lead=lead).delete()

            # Process each product entry based on max row count
            total_rows = max(
                len(categories),
                len(categories_text),
                len(subcategories),
                len(quantities),
                len(prices),
                len(attr_sizes),
                len(attr_colors),
                len(attr_models),
                len(attr_brands),
                len(attr_ankles),
                len(attr_materials),
                len(attr_peoples),
                1,
            )
            logger.error(f"Processing {total_rows} product rows...")
            for i in range(total_rows):
                category_id = categories[i] if i < len(categories) else ''
                category_text = categories_text[i].strip() if i < len(categories_text) and categories_text[i] is not None else ''
                subcat_id = subcategories[i] if i < len(subcategories) else ''
                qty_val = quantities[i] if i < len(quantities) else ''
                price_val = prices[i] if i < len(prices) else ''
                size_val = attr_sizes[i] if i < len(attr_sizes) else ''
                color_val = attr_colors[i] if i < len(attr_colors) else ''
                model_val = attr_models[i] if i < len(attr_models) else ''
                brand_val = attr_brands[i] if i < len(attr_brands) else ''
                ankle_val = attr_ankles[i] if i < len(attr_ankles) else ''
                material_val = attr_materials[i] if i < len(attr_materials) else ''
                people_val = attr_peoples[i] if i < len(attr_peoples) else ''

                has_any_content = bool(
                    (category_id and str(category_id).strip())
                    or (subcat_id and str(subcat_id).strip())
                    or (qty_val and str(qty_val).strip())
                    or (price_val and str(price_val).strip())
                    or (size_val and str(size_val).strip())
                    or (color_val and str(color_val).strip())
                    or (model_val and str(model_val).strip())
                    or (brand_val and str(brand_val).strip())
                    or (ankle_val and str(ankle_val).strip())
                    or (material_val and str(material_val).strip())
                    or (people_val and str(people_val).strip())
                    or images_by_index.get(i)
                    or prev_images_by_index.get(i)
                )
                if not has_any_content:
                    continue

                logger.error(f"Creating LeadProduct for row {i}...")
                lead_product = LeadProduct(lead=lead)
                if category_text:
                    try:
                        category_obj, _created = Category.objects.get_or_create(name=category_text, defaults={'created_by': request.user})
                        lead_product.category = category_obj
                    except Exception:
                        pass
                elif category_id:
                    try:
                        lead_product.category = Category.objects.get(id=category_id)
                    except Category.DoesNotExist:
                        pass
                if subcat_id:
                    try:
                        lead_product.subcategory = Subcategory.objects.get(id=subcat_id)
                    except Subcategory.DoesNotExist:
                        pass
                if qty_val:
                    try:
                        lead_product.quantity = int(qty_val)
                    except ValueError:
                        lead_product.quantity = None
                if price_val:
                    lead_product.price = price_val
                if size_val:
                    lead_product.size = size_val
                if color_val:
                    lead_product.color = color_val
                if model_val:
                    lead_product.model = model_val
                if brand_val:
                    lead_product.brand = brand_val
                if ankle_val:
                    lead_product.ankle = ankle_val
                if material_val:
                    lead_product.material = material_val
                if people_val:
                    lead_product.people = people_val
                # Prefer new uploaded image; otherwise reuse previous image for this index
                if images_by_index.get(i):
                    lead_product.image = images_by_index[i]
                    logger.error(f"Assigning new image {lead_product.image.name} to product {i} on edit")
                elif prev_images_by_index.get(i):
                    lead_product.image = prev_images_by_index[i]
                    logger.error(f"Re-assigning existing image {lead_product.image.name} to product {i} on edit")
                try:
                    lead_product.save()
                    logger.error(f"LeadProduct saved with ID: {lead_product.id}")
                except Exception as e:
                    logger.error(f"S3 PutObject failed on edit for row {i}: {str(e)}", exc_info=True)
                    messages.warning(request, f"Image upload failed for product {i+1}: {str(e)}")
                    # Try save without image so the row is not lost
                    try:
                        lead_product.image = None
                        lead_product.save()
                    except Exception as e2:
                        logger.error(f"Failed to save LeadProduct without image for row {i}: {str(e2)}", exc_info=True)

            logger.error("LeadProduct processing complete, proceeding with country detection...")

            # Handle phone number and country detection
            phone_number = request.POST.get('phone_number')
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
                    logger.warning(f"Failed to auto-create contact for lead {lead.contact_name}: {str(e)}")

            # If superuser changed the assignment, mark as pending or clear if unassigned
            if request.user.is_superuser:
                if lead.assigned_sales_person_id:
                    if lead.assigned_sales_person != request.user:
                        lead.assignment_status = 'pending'
                    else:
                        lead.assignment_status = None
                else:
                    lead.assignment_status = None

            lead.save()
            # Note: form.save_m2m() removed as LeadForm doesn't have m2m fields

            messages.success(request, 'Enquiry updated successfully!')
            return redirect('crm_app:lead_detail', pk=lead.pk)
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error in lead_edit: {str(e)}\n{error_trace}")
            messages.error(request, f'An error occurred while updating the enquiry: {str(e)}')
            attr_suggestions = get_leadproduct_attribute_suggestions()
            context = {
                'form': LeadForm(instance=lead, user=request.user),
                'title': 'Edit Enquiry',
                'lead': lead,
                'categories': Category.objects.filter(is_active=True),
                'subcategories': Subcategory.objects.filter(is_active=True).select_related('category'),
            }
            context.update(attr_suggestions)
            return render(request, 'crm_app/lead_form.html', context)
    
    else:
        form = LeadForm(instance=lead, user=request.user)

    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True).select_related('category')
    attr_suggestions = get_leadproduct_attribute_suggestions()

    context = {
        'form': form,
        'title': 'Edit Enquiry',
        'lead': lead,
        'categories': categories,
        'subcategories': subcategories,
    }
    context.update(attr_suggestions)

    return render(request, 'crm_app/lead_form.html', context)


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
        logger.info(f"Found lead: {lead.pk}, current status: {lead.lead_status}")
        
        # Check permissions: allow superuser, creator, assigned_sales_person, or staff
        if not request.user.is_superuser:
            is_creator = (lead.created_by == request.user)
            is_assigned = (lead.assigned_sales_person == request.user)
            is_staff = request.user.is_staff
            if not (is_creator or is_assigned or is_staff):
                logger.warning(f"Permission denied for user {request.user} on lead {lead.pk}")
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        new_status = request.POST.get('status')
        logger.info(f"New status: {new_status}")
        
        if not new_status:
            logger.warning("No status provided in request")
            return JsonResponse({'success': False, 'error': 'Missing status'})

        # Check if lead is locked (cannot change status after fulfillment)
        if lead.is_locked:
            logger.warning(f"Attempted to change status of locked lead {lead.pk}")
            return JsonResponse({
                'success': False,
                'error': 'This enquiry is locked and cannot be modified after fulfillment.'
            })

        # Get the display value for the status
        status_display = dict(Lead.STATUS_CHOICES).get(new_status, new_status)
        
        # Update the lead status and optional reason
        lead.lead_status = new_status
        # Handle reason when marking as not fulfilled
        if new_status == 'not_fulfilled':
            # Accept both 'reason' and 'reason_id' from different UIs
            reason_id = request.POST.get('reason') or request.POST.get('reason_id')
            if reason_id:
                try:
                    lead.reason = Reason.objects.get(pk=reason_id)
                except Reason.DoesNotExist:
                    logger.warning(f"Invalid reason id provided: {reason_id}")
                    return JsonResponse({'success': False, 'error': 'Invalid reason selected'})
        else:
            # Clear reason if status is fulfilled
            lead.reason = None
        lead.save(update_fields=['lead_status', 'reason', 'updated_date'])
        
        # Log the status update
        logger.info(f"Lead {lead.pk} status updated to {new_status} by {request.user}")
        
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
        
        # Log request data for debugging
        logger.info(f"Request data: {request.POST}")
        logger.info(f"Request user: {request.user}")
        
        lead = get_object_or_404(Lead, pk=pk)
        logger.info(f"Found lead: {lead.pk}, created by: {lead.created_by}")
        
        # Check permissions: allow superuser, creator, assigned_sales_person, or staff
        if not request.user.is_superuser:
            is_creator = (lead.created_by == request.user)
            is_assigned = (lead.assigned_sales_person == request.user)
            is_staff = request.user.is_staff
            if not (is_creator or is_assigned or is_staff):
                logger.warning(f"Permission denied for user {request.user} on lead {lead.pk}")
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

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

        # Check if lead is locked (cannot change stage after fulfillment)
        if lead.is_locked and lead.enquiry_stage != new_stage:
            logger.warning(f"Attempted to change stage of locked lead {lead.pk}")
            return JsonResponse({
                'success': False,
                'error': 'This enquiry is locked and cannot be modified after fulfillment.'
            })

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
        elif new_stage in ('invoice_sent'):
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
                    'success': False, 
                    'error': error_msg
                })
            lead.invoice_number = inv_no

        # Save the changes
        lead.enquiry_stage = new_stage

        # Check if this is a stage change that should trigger fulfillment
        if (new_stage == 'invoice_sent' and
            lead.invoice_number and
            lead.invoice_number.strip() and
            lead.lead_status != 'fulfilled'):
            # Auto-set status to fulfilled when stage is invoice_sent and invoice is provided
            lead.lead_status = 'fulfilled'
            # Lock the lead to prevent further stage changes
            lead.is_locked = True
            logger.info(f"Lead {lead.pk} automatically set to fulfilled and locked")
        elif new_stage == 'invoice_sent' and lead.lead_status == 'fulfilled':
            # If lead is already fulfilled but stage is being set to invoice_sent, ensure it's locked
            lead.is_locked = True
            logger.info(f"Lead {lead.pk} already fulfilled, ensuring it's locked")
        elif lead.enquiry_stage == 'invoice_sent' and lead.lead_status == 'fulfilled':
            # If lead is already in invoice_sent stage and fulfilled, ensure it's locked
            lead.is_locked = True
            logger.info(f"Lead {lead.pk} already in invoice_sent stage and fulfilled, ensuring it's locked")

        lead.save(update_fields=['enquiry_stage', 'proforma_invoice_number', 'invoice_number', 'lead_status', 'is_locked', 'updated_date'])
        logger.info(f"Successfully updated lead {lead.pk} to stage {new_stage}")
        
        # Verify persistence
        persisted_stage = Lead.objects.filter(pk=lead.pk).values_list('enquiry_stage', flat=True).first()
        if persisted_stage != new_stage:
            logger.error(
                f"Stage persistence verification failed for lead {lead.pk}. Expected {new_stage}, got {persisted_stage}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Stage update failed to persist. Please try again or contact support.',
                'expected_stage': new_stage,
                'persisted_stage': persisted_stage
            })

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
            'stage_display': stage_display,
            'lead_status': lead.lead_status,
            'status_display': dict(Lead.STATUS_CHOICES).get(lead.lead_status, lead.lead_status),
            'is_locked': lead.is_locked,
            'proforma_invoice_number': lead.proforma_invoice_number or '',
            'invoice_number': lead.invoice_number or '',
            'message': 'Stage updated successfully' + (' - Status automatically set to fulfilled' if new_stage == 'invoice_sent' and lead.lead_status == 'fulfilled' else '')
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating lead stage: {str(e)}\n{error_trace}")
        # Return 200 with success False so frontend can show message without throwing
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}',
            'traceback': error_trace
        })

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
            # Mark as pending assignment for the selected salesperson
            if user != request.user:
                lead.assignment_status = 'pending'
            else:
                lead.assignment_status = None
        else:
            lead.assigned_sales_person = None
            lead.assignment_status = None
        lead.save(update_fields=['assigned_sales_person', 'assignment_status', 'updated_date'])
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
@require_POST
def assignment_accept(request, pk):
    """Salesperson accepts an assigned enquiry."""
    lead = get_object_or_404(Lead, pk=pk)
    if lead.assigned_sales_person != request.user:
        messages.error(request, 'You are not allowed to accept this assignment.')
        return redirect('crm_app:lead_list')
    lead.assignment_status = 'accepted'
    lead.save(update_fields=['assignment_status', 'updated_date'])
    ActivityLog.objects.create(
        user=request.user,
        activity_type='note',
        subject='Assignment accepted',
        description=f'Assignment accepted by {request.user.get_full_name() or request.user.username}',
        lead=lead,
    )
    messages.success(request, 'Enquiry assignment accepted.')
    return redirect(f"{reverse('crm_app:lead_list')}?tab=pending_requests")


@login_required
@require_POST
def assignment_reject(request, pk):
    """Salesperson rejects an assigned enquiry: unassign and mark rejected."""
    lead = get_object_or_404(Lead, pk=pk)
    if lead.assigned_sales_person != request.user:
        messages.error(request, 'You are not allowed to reject this assignment.')
        return redirect('crm_app:lead_list')
    lead.assigned_sales_person = None
    lead.assignment_status = 'rejected'
    lead.save(update_fields=['assigned_sales_person', 'assignment_status', 'updated_date'])
    ActivityLog.objects.create(
        user=request.user,
        activity_type='note',
        subject='Assignment rejected',
        description=f'Assignment rejected by {request.user.get_full_name() or request.user.username}',
        lead=lead,
    )
    messages.success(request, 'Enquiry assignment rejected and returned to admin as unassigned.')
    return redirect(f"{reverse('crm_app:lead_list')}?tab=pending_requests")


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
        logger.info(f"Found lead: {lead.pk}, current reason: {lead.reason}")
        
        # Check permissions
        if not request.user.is_superuser and lead.created_by != request.user:
            logger.warning(f"Permission denied for user {request.user} on lead {lead.pk}")
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
        logger.info(f"Lead {lead.pk} reason updated from {old_reason} to {reason} by {request.user}")
        
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


@login_required
def lead_bulk_import(request):
    """Bulk import leads from Google Sheets CSV"""
    print("=== BULK IMPORT VIEW CALLED ===")
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    print(f"User: {request.user}")
    print(f"CSRF token in request: {'csrfmiddlewaretoken' in request.POST}")
    
    if request.method == 'POST':
        sheet_url = request.POST.get('sheet_url', '').strip()
        print(f"Sheet URL received: {sheet_url}")
        
        if not sheet_url:
            messages.error(request, 'Please provide a Google Sheet URL.')
            return redirect('crm_app:lead_list')

        # Extract spreadsheet ID (and optional gid) from URL
        import re
        # More flexible regex to handle various Google Sheets URL formats
        id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not id_match:
            # Try alternative pattern for shared links
            id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        
        print(f"URL parsing - sheet_url: {sheet_url}")
        print(f"ID match: {id_match}")
        if not id_match:
            print(f"No spreadsheet ID found in URL: {sheet_url}")
            messages.error(request, 'Invalid Google Sheet URL format. Please use a URL like: https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit')
            return redirect('crm_app:lead_list')

        spreadsheet_id = id_match.group(1)
        print(f"Extracted spreadsheet ID: {spreadsheet_id}")
        gid_match = re.search(r'[?#&]gid=(\d+)', sheet_url)
        gid_part = f"&gid={gid_match.group(1)}" if gid_match else ''
        print(f"GID part: {gid_part}")
        csv_url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv{gid_part}'
        print(f"CSV URL generated: {csv_url}")

        try:
            # Fetch CSV data
            print("Fetching CSV data...")
            response = requests.get(csv_url, timeout=30)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 403:
                messages.error(request, 'Access denied to Google Sheet. Please make sure the sheet is publicly accessible by setting sharing to "Anyone with the link can view".')
                return redirect('crm_app:lead_list')
            elif response.status_code == 404:
                messages.error(request, 'Google Sheet not found. Please check the URL and make sure it exists.')
                return redirect('crm_app:lead_list')
            
            response.raise_for_status()

            # Parse CSV with pandas (treat all as strings, avoid NaN)
            print("Parsing CSV with pandas...")
            df = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
            print(f"DataFrame shape: {df.shape}")
            print(f"Raw DataFrame columns: {list(df.columns)}")

            # Helper: normalize Google Drive links to embeddable form for <img src>
            def _normalize_drive_url(url: str) -> str:
                try:
                    if not url:
                        return url
                    url = url.strip()
                    # Patterns we handle:
                    # - https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
                    # - https://drive.google.com/open?id=<FILE_ID>
                    # - https://drive.google.com/uc?id=<FILE_ID>
                    # Return: https://drive.google.com/uc?export=view&id=<FILE_ID>
                    import re
                    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
                    if m:
                        file_id = m.group(1)
                        return f"https://drive.google.com/uc?export=view&id={file_id}"
                    m = re.search(r"[?&#]id=([A-Za-z0-9_-]+)", url)
                    if m:
                        file_id = m.group(1)
                        return f"https://drive.google.com/uc?export=view&id={file_id}"
                    # If already uc link, ensure export=view
                    if "drive.google.com/uc" in url and "id=" in url and "export=view" not in url:
                        return url + ("&" if "?" in url else "?") + "export=view"
                    return url
                except Exception:
                    return url

            # Normalize and map headers to expected names
            print("Normalizing headers...")
            original_cols = list(df.columns)
            def norm_key(c):
                k = c.lower()
                k = re.sub(r'[#\.]', '', k)  # remove # and .
                k = re.sub(r'\s+', '', k)    # remove spaces
                return k
            alias_map = {
                'customerphone': 'Customer Phone #',
                'customerphone#': 'Customer Phone #',
                'phone': 'Customer Phone #',
                'phonenumber': 'Customer Phone #',
                'customername': 'Customer Name',
                'name': 'Customer Name',
                'companyname': 'Company Name',
                'company': 'Company Name',
                'imageurl': 'Image URL',
                'image': 'Image URL',
                'imagelink': 'Image URL',
                'item': 'Item',
                'product': 'Item',
                'category': 'Category',
                'fulfilled': 'Fulfilled',
                'salesinvoiceno': 'Sales Invoice No.',
                'invoiceno': 'Sales Invoice No.',
                'invoicenumber': 'Sales Invoice No.',
                'reason': 'Reason',
                'new/old': 'New/Old',
                'local/import': 'Local / Import',
                'qty': 'Qty',
                'price': 'Price',
                'followups': 'Follow ups',
                'comments': 'Comments',
            }
            rename_map = {}
            for c in original_cols:
                key = norm_key(c)
                if key in alias_map:
                    rename_map[c] = alias_map[key]
            if rename_map:
                df.rename(columns=rename_map, inplace=True)
                print(f"Renamed columns: {rename_map}")
            print(f"Normalized DataFrame columns: {list(df.columns)}")
            
            # Check for required columns
            required_columns = ['Customer Phone #', 'Image URL']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"Missing required columns: {missing_columns}")
                messages.error(request, f'Sheet is missing required columns: {", ".join(missing_columns)}')
                return redirect('crm_app:lead_list')
            
            print(f"First few rows:\n{df.head()}")
            print(f"Last 20 rows:\n{df.tail(20)}")

            if df.empty:
                print("DataFrame is empty")
                messages.error(request, 'The Google Sheet is empty.')
                return redirect('crm_app:lead_list')

            # Get last 20 non-empty rows with Image URL
            print("Filtering for valid rows...")
            # Consider non-empty Image URL rows only, keep last 20
            df['Image URL'] = df['Image URL'].astype(str).map(lambda x: x.strip())
            valid_rows = df[df['Image URL'] != ''].tail(20)
            print(f"Valid rows count: {len(valid_rows)}")
            print(f"Valid rows data:\n{valid_rows}")

            if valid_rows.empty:
                print("No valid rows found")
                messages.error(request, 'No valid rows found with Image URLs in the last 20 rows.')
                return redirect('crm_app:lead_list')

            imported_count = 0
            skipped_count = 0
            errors = []

            for idx, row in valid_rows.iterrows():
                print(f"\n=== Processing Row {idx+2} ===")
                print(f"Row data: {dict(row)}")
                
                try:
                    phone = str(row.get('Customer Phone #', '')).strip()
                    print(f"Phone number extracted: '{phone}'")
                    
                    if not phone:
                        print("SKIPPING: Missing phone number")
                        skipped_count += 1
                        errors.append(f"Row {idx+2}: Missing phone number")
                        continue

                    # Check for duplicate by phone
                    existing_lead = Lead.objects.filter(phone_number=phone).first()
                    print(f"Checking for duplicate phone: {existing_lead is not None}")
                    
                    if existing_lead:
                        print(f"SKIPPING: Duplicate phone number {phone}")
                        skipped_count += 1
                        errors.append(f"Row {idx+2}: Duplicate phone number {phone}")
                        continue

                    print("Phone validation passed, proceeding with import...")

                    # Map fields
                    contact_name = str(row.get('Customer Name', '')).strip()
                    company_raw = str(row.get('Company Name', '')).strip()
                    # Ensure non-null company_name to avoid DB NOT NULL error
                    company_name = company_raw or (contact_name if contact_name else 'Unknown')
                    image_url_raw = (str(row.get('Image URL', '')).strip() or None)
                    image_url = _normalize_drive_url(image_url_raw) if image_url_raw else None
                    category_name = str(row.get('Category', '')).strip()
                    product_name = str(row.get('Item', '')).strip()
                    fulfilled = str(row.get('Fulfilled', '')).strip().lower() in ['yes', 'true', '1', 'y']
                    invoice_number = (str(row.get('Sales Invoice No.', '')).strip() or None)
                    reason_name = (str(row.get('Reason', '')).strip() or None)
                    notes_parts = []

                    # Add other fields to notes
                    if row.get('New/Old'):
                        notes_parts.append(f"Type: {row.get('New/Old')}")
                    if row.get('Local / Import'):
                        notes_parts.append(f"Origin: {row.get('Local / Import')}")
                    if row.get('Qty'):
                        notes_parts.append(f"Qty: {row.get('Qty')}")
                    if row.get('Price'):
                        notes_parts.append(f"Price: {row.get('Price')}")
                    if row.get('Follow ups'):
                        notes_parts.append(f"Follow-ups: {row.get('Follow ups')}")
                    if row.get('Comments'):
                        notes_parts.append(f"Comments: {row.get('Comments')}")

                    notes = '; '.join(notes_parts) if notes_parts else None

                    # Auto-create category if not exists
                    category = None
                    if category_name:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'created_by': request.user}
                        )

                    # Auto-create product if not exists (no created_by on this model)
                    product = None
                    if product_name:
                        product, created = Product.objects.get_or_create(
                            name=product_name,
                            defaults={}
                        )

                    # Create reason if provided (no created_by on this model)
                    reason = None
                    if reason_name:
                        reason, created = Reason.objects.get_or_create(
                            name=reason_name,
                            defaults={}
                        )

                    # Determine enquiry stage
                    enquiry_stage = 'enquiry_received'
                    if fulfilled and invoice_number:
                        enquiry_stage = 'invoice_sent'

                    # Create lead
                    print(f"Creating lead with phone: {phone}, name: {contact_name}")
                    lead = Lead.objects.create(
                        contact_name=contact_name,
                        phone_number=phone,
                        company_name=company_name,
                        image_url=image_url,
                        category=category,
                        lead_status='fulfilled' if fulfilled else 'not_fulfilled',
                        enquiry_stage=enquiry_stage,
                        reason=reason,
                        invoice_number=invoice_number,
                        notes=notes,
                        created_by=request.user,
                        assigned_sales_person=request.user,  # Default to current user
                    )
                    print(f"Lead created successfully with ID: {lead.id}")

                    # Add product
                    if product:
                        lead.products_enquired.add(product)
                        print(f"Added product {product.name} to lead")

                    imported_count += 1
                    print(f"Import successful for row {idx+2}")

                except Exception as e:
                    print(f"ERROR processing row {idx+2}: {str(e)}")
                    print(f"Error type: {type(e).__name__}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    skipped_count += 1
                    errors.append(f"Row {idx+2}: {str(e)}")
                    logger.error(f"Error importing row {idx+2}: {str(e)}", exc_info=True)

            # Show results
            if imported_count > 0:
                messages.success(request, f'Successfully imported {imported_count} enquiries from Google Sheets.')
            if skipped_count > 0:
                # Surface first few skip reasons to the UI for faster debugging
                if errors:
                    details = "; ".join(errors[:10])
                    messages.warning(request, f'Skipped {skipped_count} row(s). Details: {details}')
                    if len(errors) > 10:
                        messages.info(request, f"Additional {len(errors) - 10} row(s) were skipped. See server logs for full list.")
                else:
                    messages.warning(request, f'Skipped {skipped_count} row(s).')

            return redirect('crm_app:lead_list')

        except requests.RequestException as e:
            print(f"REQUESTS ERROR: {str(e)}")
            messages.error(request, f'Error fetching Google Sheet: {str(e)}')
        except Exception as e:
            print(f"GENERAL ERROR: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            messages.error(request, f'Error processing import: {str(e)}')
            logger.error(f"Bulk import error: {str(e)}", exc_info=True)

    return redirect('crm_app:lead_list')


@login_required
def lead_bulk_export(request):
    """Export all leads to Excel"""
    from openpyxl import Workbook
    from django.http import HttpResponse

    # Get all leads (superuser sees all, others see assigned)
    if request.user.is_superuser:
        leads = Lead.objects.select_related('assigned_sales_person', 'created_by', 'category', 'reason').all()
    else:
        leads = Lead.objects.select_related('assigned_sales_person', 'created_by', 'category', 'reason').filter(assigned_sales_person=request.user)

    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Enquiries"

    # Headers matching import format
    headers = [
        'Date', 'Salesman', 'Customer Phone #', 'Customer Name', 'New/Old', 'Item', 'Category',
        'Local / Import', 'Qty', 'Price', 'Image URL', 'Fulfilled', 'Reason', 'Follow ups',
        'Comments', 'Sales Invoice No.', 'Company Name'
    ]
    ws.append(headers)

    # Add data
    for lead in leads:
        row = [
            lead.created_date.strftime('%Y-%m-%d') if lead.created_date else '',
            lead.assigned_sales_person.get_full_name() if lead.assigned_sales_person else '',
            lead.phone_number,
            lead.contact_name,
            '',  # New/Old - from notes if available
            ', '.join([p.name for p in lead.products_enquired.all()]),
            lead.category.name if lead.category else '',
            '',  # Local / Import
            '',  # Qty
            '',  # Price
            lead.image_url or '',
            'Yes' if lead.lead_status == 'fulfilled' else 'No',
            lead.reason.name if lead.reason else '',
            '',  # Follow ups
            lead.notes or '',
            lead.invoice_number or '',
            lead.company_name or '',
        ]
        ws.append(row)

    # Create response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=enquiries_export.xlsx'
    wb.save(response)
    return response


@login_required
@require_POST
def lead_bulk_delete(request):
    """Bulk delete selected leads"""
    print("=== BULK DELETE VIEW CALLED ===")
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    print(f"User: {request.user}")
    
    selected_leads = request.POST.getlist('selected_leads')
    print(f"Selected leads: {selected_leads}")
    
    if not selected_leads:
        messages.error(request, 'No enquiries selected for deletion.')
        return redirect('crm_app:lead_list')
    
    # Filter leads based on user permissions
    if request.user.is_superuser:
        leads_to_delete = Lead.objects.filter(pk__in=selected_leads)
    else:
        leads_to_delete = Lead.objects.filter(pk__in=selected_leads, assigned_sales_person=request.user)
    
    if not leads_to_delete.exists():
        messages.error(request, 'No valid enquiries found for deletion.')
        return redirect('crm_app:lead_list')
    
    deleted_count = leads_to_delete.count()
    
    # Check for locked leads that cannot be deleted
    locked_leads = leads_to_delete.filter(is_locked=True)
    if locked_leads.exists():
        locked_names = [lead.contact_name for lead in locked_leads]
        messages.error(request, f'Cannot delete locked enquiries: {", ".join(locked_names)}. These enquiries are fulfilled and cannot be modified.')
        return redirect('crm_app:lead_list')
    
    # Log deletions and delete
    for lead in leads_to_delete:
        ActivityLog.objects.create(
            lead=lead,
            activity_type='note',
            subject='Bulk deletion',
            description=f'Enquiry deleted via bulk operation',
            user=request.user
        )
    
    leads_to_delete.delete()
    
    messages.success(request, f'Successfully deleted {deleted_count} enquiry(ies).')
    return redirect('crm_app:lead_list')


@login_required
@require_POST
def upload_whatsapp_file(request):
    """Handle file upload for WhatsApp sending - uses local storage"""
    import os
    from django.core.files.storage import FileSystemStorage
    # Import Django settings under a different name to avoid collision with
    # the local settings() view defined in this module
    from django.conf import settings as django_settings
    
    try:
        # Get uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        # Validate file size (10MB limit)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File size exceeds 10MB limit'})
        
        # Get other data
        whatsapp_number = request.POST.get('whatsapp_number', '')
        message = request.POST.get('message', '')
        lead_id = request.POST.get('lead_id', '')
        
        # Use local file system storage for WhatsApp files (not S3)
        # Guard against MEDIA_ROOT being empty when S3 is enabled
        media_root = getattr(django_settings, 'MEDIA_ROOT', None)
        if not media_root:
            # Fallback to BASE_DIR / 'media' if MEDIA_ROOT is not configured
            media_root = os.path.join(str(django_settings.BASE_DIR), 'media')
        whatsapp_dir = os.path.join(media_root, 'whatsapp_files')
        
        # Create directory if it doesn't exist
        os.makedirs(whatsapp_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        original_filename = uploaded_file.name
        safe_filename = f"{timestamp}_{original_filename}"
        
        # Save file locally
        fs = FileSystemStorage(location=whatsapp_dir, base_url='/media/whatsapp_files/')
        filename = fs.save(safe_filename, uploaded_file)
        
        # Generate full URL for the file
        file_url = request.build_absolute_uri(fs.url(filename))
        
        # Log the activity
        if lead_id:
            try:
                lead = Lead.objects.get(pk=lead_id)
                ActivityLog.objects.create(
                    lead=lead,
                    activity_type='email',  # Using 'email' as closest type
                    subject=f'File sent via WhatsApp to {whatsapp_number}',
                    description=f'File "{original_filename}" uploaded and shared via WhatsApp{" with message: " + message if message else ""}',
                    user=request.user,
                    activity_date=timezone.now()
                )
            except Lead.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'file_name': original_filename,
            'file_path': filename
        })
        
    except Exception as e:
        logging.error(f'Error uploading WhatsApp file: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        })
