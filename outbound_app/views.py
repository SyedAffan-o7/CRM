from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Prefetch, Avg
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.paginator import Paginator
from datetime import datetime, timedelta, time
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_datetime, parse_date
from django.urls import reverse
from urllib.parse import urlencode

from .models import OutboundActivity, Campaign
from customers_app.models import Contact
from leads_app.models import Lead
from .forms import OutboundActivityForm, SimpleOutboundActivityForm
import csv


@login_required
def campaign_list(request):
    """List all outbound activities (main outbound page)"""
    activities = OutboundActivity.objects.select_related(
        'contact', 'created_by', 'lead', 'campaign'
    ).order_by('-created_at')

    # Apply role-based filtering
    if request.user.is_superuser:
        # Super admin sees all activities
        pass
    else:
        # Regular users see only their own activities
        activities = activities.filter(created_by=request.user)

    # Search functionality
    search = request.GET.get('search', '').strip()
    if search:
        activities = activities.filter(
            Q(contact__full_name__icontains=search) |
            Q(summary__icontains=search) |
            Q(contact__phone_number__icontains=search)
        )

    # Pagination
    paginator = Paginator(activities, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'title': 'Outbound Activities'
    }

    return render(request, 'outbound_app/outbound_list.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def log_activity(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        form = OutboundActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.contact = contact
            if not activity.created_by:
                activity.created_by = request.user if request.user.is_authenticated else None
            activity.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"ok": True, "id": activity.id})
            return redirect('outbound_app:outbound_detail', pk=activity.pk)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    else:
        form = OutboundActivityForm(initial={'contact': contact.pk})
    return render(request, 'outbound_app/activity_form.html', {"form": form, "contact": contact})


@login_required
@require_http_methods(["GET", "POST"])
def outbound_add(request):
    """Add a new outbound activity from scratch"""
    from django.db import connection
    from django.contrib import messages
    
    # Check if we should use simple form (fallback)
    use_simple_form = request.GET.get('simple', False)
    
    try:
        # Handle potential database connection issues (backend-agnostic)
        try:
            connection.close_if_unusable_or_obsolete()
        except Exception:
            try:
                if connection.connection and hasattr(connection.connection, 'closed') and connection.connection.closed:
                    connection.close()
            except Exception:
                pass
            
        if use_simple_form:
            # Use simple form that doesn't rely on database relationships
            if request.method == 'POST':
                form = SimpleOutboundActivityForm(request.POST)
                if form.is_valid():
                    activity = form.save(user=request.user)
                    messages.success(request, f'Outbound activity for {activity.contact.full_name} has been saved successfully!')
                    return redirect('outbound_app:outbound_detail', pk=activity.pk)
                else:
                    messages.error(request, 'Please correct the errors below.')
            else:
                form = SimpleOutboundActivityForm()
            
            return render(request, 'outbound_app/outbound_simple_form.html', {"form": form, "mode": "add"})
        
        else:
            # Use regular form with database relationships
            if request.method == 'POST':
                form = OutboundActivityForm(request.POST)
                if form.is_valid():
                    try:
                        # Now that FK is fixed, use standard Django form save
                        activity = form.save(commit=False)
                        if not activity.created_by:
                            activity.created_by = request.user if request.user.is_authenticated else None
                        activity.save()
                        messages.success(request, f'Outbound activity for {activity.contact.full_name} has been saved successfully!')
                        return redirect('outbound_app:outbound_detail', pk=activity.pk)
                    except Exception as save_err:
                        # Attach a non-field error so it's visible in the form
                        form.add_error(None, f"Failed to save activity: {str(save_err)}")
                        messages.error(request, 'Could not save the activity. Please review inputs and try again.')
                else:
                    messages.error(request, 'Please correct the errors below.')
            else:
                form = OutboundActivityForm()
                
            return render(request, 'outbound_app/outbound_add_form.html', {"form": form, "mode": "add"})
        
    except Exception as e:
        from django.urls import reverse
        # Suppress user-facing error message to keep simple form clean
        # If we're already in simple mode, do NOT redirect again; render simple form directly
        if use_simple_form:
            if request.method == 'POST':
                form = SimpleOutboundActivityForm(request.POST)
                if form.is_valid():
                    activity = form.save(user=request.user)
                    messages.success(request, f'Outbound activity for {activity.contact.full_name} has been saved successfully!')
                    return redirect('outbound_app:outbound_detail', pk=activity.pk)
            else:
                form = SimpleOutboundActivityForm()
            return render(request, 'outbound_app/outbound_simple_form.html', {"form": form, "mode": "add"})
        # Otherwise, redirect once to simple mode (no error banner)
        try:
            url = reverse('outbound_app:outbound_add') + '?simple=1'
        except Exception:
            url = request.path + '?simple=1'
        return redirect(url)


@login_required
@require_http_methods(["GET", "POST"])
def outbound_edit(request, pk: int):
    activity = get_object_or_404(OutboundActivity.objects.select_related('contact'), pk=pk)

    # Check permissions: only superuser or activity creator can edit
    if not (request.user.is_superuser or activity.created_by == request.user):
        messages.error(request, "You don't have permission to edit this activity.")
        return redirect('outbound_app:outbound_detail', pk=activity.pk)

    if request.method == 'POST':
        form = OutboundActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return redirect('outbound_app:outbound_detail', pk=activity.pk)
    else:
        form = OutboundActivityForm(instance=activity)
    return render(request, 'outbound_app/outbound_form.html', {"form": form, "activity": activity, "mode": "edit"})


@login_required
@require_http_methods(["GET"])
def outbound_convert_to_enquiry(request, pk: int):
    activity = get_object_or_404(OutboundActivity.objects.select_related('contact'), pk=pk)

    if not (request.user.is_superuser or activity.created_by == request.user):
        messages.error(request, "You don't have permission to convert this activity to an enquiry.")
        return redirect('outbound_app:outbound_detail', pk=activity.pk)

    contact = activity.contact

    if contact:
        request.session['prefill_contact_id'] = contact.pk

    request.session['from_outbound_activity_id'] = activity.pk

    lead_add_url = reverse('crm_app:lead_add')
    params = {}
    if contact:
        params['contact_id'] = contact.pk

    if params:
        redirect_url = f"{lead_add_url}?{urlencode(params)}"
    else:
        redirect_url = lead_add_url

    return redirect(redirect_url)


@login_required
@require_http_methods(["POST"])  # Delete via POST only
def outbound_delete(request, pk: int):
    activity = get_object_or_404(OutboundActivity, pk=pk)

    # Check permissions: only superuser or activity creator can delete
    if not (request.user.is_superuser or activity.created_by == request.user):
        messages.error(request, "You don't have permission to delete this activity.")
        return redirect('outbound_app:outbound_detail', pk=activity.pk)

    activity.delete()
    return redirect('outbound_app:outbound_list')


def outbound_detail(request, pk: int):
    """Server-rendered detail page for a single outbound record."""
    activity = (
        OutboundActivity.objects.select_related('contact', 'campaign', 'lead', 'created_by')
        .filter(pk=pk)
        .first()
    )
    if not activity:
        return render(request, 'outbound_app/outbound_detail.html', {"not_found": True, "pk": pk})

    # Check permissions: superuser, activity creator, or has related leads with the same contact
    has_permission = False
    if request.user.is_superuser:
        has_permission = True
    elif activity.created_by == request.user:
        has_permission = True
    else:
        # Check if user has any leads with the same contact (same contact access)
        from leads_app.models import Lead
        same_contact_exists = Lead.objects.filter(
            contact=activity.contact
        ).filter(
            Q(created_by=request.user) | Q(assigned_sales_person=request.user)
        ).exists()
        if same_contact_exists:
            has_permission = True

    if not has_permission:
        messages.error(request, "You don't have permission to view this activity.")
        return redirect('outbound_app:outbound_list')

    # Derive status from contact.outbound_status if available
    outbound_status = getattr(activity.contact, 'outbound_status', None)

    context = {
        "activity": activity,
        "outbound_status": outbound_status,
        "pk": pk,
    }
    return render(request, 'outbound_app/outbound_detail.html', context)


@require_http_methods(["GET"])
def outbound_detail_api(request, pk: int):
    """Return JSON details for a single OutboundActivity."""
    try:
        activity = (
            OutboundActivity.objects.select_related('contact', 'lead', 'created_by')
            .filter(pk=pk)
            .first()
        )
        if not activity:
            return JsonResponse({"error": "Outbound record not found"}, status=404)

        contact = activity.contact
        created_by = activity.created_by
        status = getattr(contact, 'outbound_status', None) if contact else None

        data = {
            "id": activity.id,
            "customer": getattr(contact, 'full_name', None),
            "status": status,
            "time": activity.created_at.isoformat() if activity.created_at else None,
            "method": activity.method,
            "summary": activity.summary,
            "next_step": activity.next_step,
            "next_step_date": activity.next_step_date.isoformat() if activity.next_step_date else None,
            "created_by": getattr(created_by, 'username', None),
            "lead": getattr(activity.lead, 'contact_name', None),
            "lead_id": activity.lead_id,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def outbound_list_api(request):
    """Return JSON array of outbound activities with basic filters."""
    qs = OutboundActivity.objects.select_related('contact', 'lead', 'created_by').order_by('-created_at')

    # Apply role-based filtering
    if request.user.is_superuser:
        # Super admin sees all activities
        pass
    else:
        # Regular users see only their own activities
        qs = qs.filter(created_by=request.user)

    # Filters: contact, campaign, method, status
    contact_q = request.GET.get('contact')
    if contact_q:
        qs = qs.filter(contact__full_name__icontains=contact_q)
    campaign_q = request.GET.get('campaign')
    if campaign_q:
        qs = qs.filter(campaign__name__icontains=campaign_q)
    method_q = request.GET.get('method')
    if method_q:
        qs = qs.filter(method=method_q)
    status_q = request.GET.get('status')
    if status_q:
        qs = qs.filter(contact__outbound_status__iexact=status_q)

    # Salesperson
    salesperson_q = request.GET.get('salesperson')
    if salesperson_q:
        qs = qs.filter(created_by__username__icontains=salesperson_q)

    # Date range: date_from, date_to (accepts ISO datetime or YYYY-MM-DD)
    def _parse_dt(val, is_end=False):
        if not val:
            return None
        dt = parse_datetime(val)
        if dt:
            return dt
        d = parse_date(val)
        if d:
            return datetime.combine(d, time.max if is_end else time.min)
        return None

    date_from = _parse_dt(request.GET.get('date_from'))
    date_to = _parse_dt(request.GET.get('date_to'), is_end=True)
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)

    data = []
    for a in qs[:500]:  # cap for safety
        data.append({
            "_id": a.id,
            "contact_id": a.contact_id,
            "customer": getattr(a.contact, 'full_name', None),
            "phone": getattr(a.contact, 'phone_number', None),
            "status": getattr(a.contact, 'outbound_status', None),
            "time": a.created_at.isoformat() if a.created_at else None,
            "lead": getattr(a.lead, 'contact_name', None),
            "lead_id": a.lead_id,
            "method": a.method,
            "summary": a.summary,
            "next_step": a.next_step,
            "salesperson": getattr(a.created_by, 'username', None),
            "last_contacted": getattr(a.contact, 'last_contacted', None).isoformat() if getattr(a.contact, 'last_contacted', None) else None,
        })
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["GET"]) 
def customer_outbound(request, contact_id: str):
    """Show a contact's 360° view with info card, outbound timeline, and related enquiries."""
    # Support URLs that pass phone_number (string) by default
    try:
        contact = Contact.objects.get(phone_number=contact_id)
    except Contact.DoesNotExist:
        contact = get_object_or_404(Contact, pk=contact_id)
    
    # Get all activities with related data
    activities = (
        OutboundActivity.objects.select_related('created_by', 'lead', 'campaign')
        .filter(contact=contact)
        .order_by('-created_at')
    )
    
    # Related enquiries (Leads) with products
    try:
        from leads_app.models import Lead
        related_leads = (
            Lead.objects.filter(contact=contact)
            .select_related('lead_source', 'assigned_sales_person')
            .prefetch_related('products_enquired')
            .order_by('-created_date')[:10]  # Limit to recent 10
        )
    except Exception:
        related_leads = []
    
    # Calculate additional stats
    total_interactions = activities.count()
    last_activity = activities.first()
    pending_follow_ups = activities.filter(
        follow_up_reminder__isnull=False,
        follow_up_reminder__gte=timezone.now()
    ).count()
    
    # Check for overdue follow-ups
    overdue_follow_ups = activities.filter(
        follow_up_reminder__isnull=False,
        follow_up_reminder__lt=timezone.now()
    ).exists()
    
    # Get next scheduled action
    next_action = activities.filter(
        next_step_date__isnull=False,
        next_step_date__gte=timezone.now()
    ).order_by('next_step_date').first()
    
    context = {
        'contact': contact,
        'activities': activities,
        'related_leads': related_leads,
        'total_interactions': total_interactions,
        'last_activity': last_activity,
        'pending_follow_ups': pending_follow_ups,
        'overdue_follow_ups': overdue_follow_ups,
        'next_action': next_action,
    }
    
    return render(request, 'outbound_app/customer_outbound.html', context)


@login_required
@require_http_methods(["GET"]) 
def customer_outbound_drawer(request, contact_id: str):
    """Return drawer HTML for customer 360° view - used for AJAX loading."""
    try:
        contact = Contact.objects.get(phone_number=contact_id)
    except Contact.DoesNotExist:
        contact = get_object_or_404(Contact, pk=contact_id)
    
    # Get activities (limit for drawer)
    activities = (
        OutboundActivity.objects.select_related('created_by', 'lead', 'campaign')
        .filter(contact=contact)
        .order_by('-created_at')[:10]  # Limit for drawer performance
    )
    
    # Related enquiries (limit for drawer)
    try:
        from leads_app.models import Lead
        related_leads = (
            Lead.objects.filter(contact=contact)
            .select_related('lead_source', 'assigned_sales_person')
            .prefetch_related('products_enquired')
            .order_by('-created_date')[:5]  # Limit to recent 5 for drawer
        )
    except Exception:
        related_leads = []
    
    # Calculate stats
    total_interactions = OutboundActivity.objects.filter(contact=contact).count()
    pending_follow_ups = activities.filter(
        follow_up_reminder__isnull=False,
        follow_up_reminder__gte=timezone.now()
    ).count()
    
    overdue_follow_ups = OutboundActivity.objects.filter(
        contact=contact,
        follow_up_reminder__isnull=False,
        follow_up_reminder__lt=timezone.now()
    ).exists()
    
    context = {
        'contact': contact,
        'activities': activities,
        'related_leads': related_leads,
        'total_interactions': total_interactions,
        'pending_follow_ups': pending_follow_ups,
        'overdue_follow_ups': overdue_follow_ups,
    }
    
    return render(request, 'outbound_app/customer_drawer.html', context)


@login_required
@require_http_methods(["GET"])
def outbound_export_csv(request):
    """Export outbound activities to CSV with optional filters (same as list API)."""
    qs = OutboundActivity.objects.select_related('contact', 'campaign', 'created_by').order_by('-created_at')

    # Apply role-based filtering
    if request.user.is_superuser:
        # Super admin sees all activities
        pass
    else:
        # Regular users see only their own activities
        qs = qs.filter(created_by=request.user)

    contact_q = request.GET.get('contact')
    if contact_q:
        qs = qs.filter(contact__full_name__icontains=contact_q)
    campaign_q = request.GET.get('campaign')
    if campaign_q:
        qs = qs.filter(campaign__name__icontains=campaign_q)
    method_q = request.GET.get('method')
    if method_q:
        qs = qs.filter(method=method_q)
    status_q = request.GET.get('status')
    if status_q:
        qs = qs.filter(contact__outbound_status__iexact=status_q)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="outbound_activities.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Customer', 'Campaign', 'Lead', 'Status', 'Method', 'Summary', 'Next Step', 'Next Step Date', 'Created By', 'Created At'])
    for a in qs.iterator():
        writer.writerow([
            a.id,
            getattr(a.contact, 'full_name', ''),
            getattr(a.campaign, 'name', ''),
            getattr(a.lead, 'contact_name', ''),
            getattr(a.contact, 'outbound_status', ''),
            a.get_method_display(),
            a.summary.replace('\r', ' ').replace('\n', ' ') if a.summary else '',
            a.get_next_step_display(),
            a.next_step_date.isoformat() if a.next_step_date else '',
            getattr(a.created_by, 'username', ''),
            a.created_at.isoformat() if a.created_at else '',
        ])
    return response


@login_required
def outbound_dashboard(request):
    """Outbound dashboard with analytics - accessible to all users but with role-based filtering"""
    # Get date filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    salesperson_filter = request.GET.get('salesperson')

    # Default to current month if no dates provided
    if not from_date or not to_date:
        now = timezone.now()
        from_date = now.replace(day=1).date()
        to_date = now.date()
    else:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

    # Base queryset for activities in date range
    activities_qs = OutboundActivity.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
        created_by__isnull=False  # Exclude activities with no creator (data integrity)
    ).select_related('contact', 'created_by', 'lead')

    # Apply role-based filtering
    if request.user.is_superuser:
        # Super admin sees all activities, but can filter by salesperson
        if salesperson_filter:
            activities_qs = activities_qs.filter(created_by_id=salesperson_filter)
    else:
        # Regular users see only their own activities
        activities_qs = activities_qs.filter(created_by=request.user)
    
    # Overall statistics
    total_activities = activities_qs.count()
    unique_customers_contacted = activities_qs.values('contact').distinct().count()
    total_enquiries_generated = activities_qs.filter(lead__isnull=False).count()
    
    # Method breakdown
    method_stats = activities_qs.values('method').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Salesperson performance
    if request.user.is_superuser:
        # Super admin sees performance stats for all users in the filtered data
        salesperson_stats = activities_qs.values(
            'created_by__id',
            'created_by__first_name',
            'created_by__last_name',
            'created_by__username'
        ).annotate(
            total_activities=Count('id'),
            unique_customers=Count('contact', distinct=True),
            enquiries_generated=Count('lead', distinct=True)
        ).order_by('-total_activities')
    else:
        # Regular users see only their own performance stats
        salesperson_stats = activities_qs.filter(created_by=request.user).values(
            'created_by__id',
            'created_by__first_name',
            'created_by__last_name',
            'created_by__username'
        ).annotate(
            total_activities=Count('id'),
            unique_customers=Count('contact', distinct=True),
            enquiries_generated=Count('lead', distinct=True)
        ).order_by('-total_activities')
    
    # Recent activities (last 10)
    recent_activities = activities_qs.order_by('-created_at')[:10]
    
    # Daily activity trend (last 7 days)
    daily_stats = []
    for i in range(7):
        date = to_date - timedelta(days=i)
        count = activities_qs.filter(created_at__date=date).count()
        daily_stats.append({
            'date': date,
            'count': count
        })
    daily_stats.reverse()
    
    # Get all salespeople for filter dropdown
    # Note: OutboundActivity.created_by has related_name='outbound_created'
    salespeople = User.objects.filter(
        outbound_created__isnull=False
    ).distinct().order_by('first_name', 'last_name', 'username')
    
    # Next steps due soon
    upcoming_next_steps = OutboundActivity.objects.filter(
        next_step_date__gte=timezone.now(),
        next_step_date__lte=timezone.now() + timedelta(days=7)
    ).select_related('contact', 'created_by').order_by('next_step_date')[:10]
    
    context = {
        'total_activities': total_activities,
        'unique_customers_contacted': unique_customers_contacted,
        'total_enquiries_generated': total_enquiries_generated,
        'method_stats': method_stats,
        'salesperson_stats': salesperson_stats,
        'recent_activities': recent_activities,
        'daily_stats': daily_stats,
        'upcoming_next_steps': upcoming_next_steps,
        'salespeople': salespeople,
        'from_date': from_date,
        'to_date': to_date,
        'selected_salesperson': salesperson_filter,
        'date_range_display': f"{from_date.strftime('%B %d, %Y')} - {to_date.strftime('%B %d, %Y')}",
    }
    
    return render(request, 'outbound_app/outbound_dashboard.html', context)


@login_required
def send_catalog(request, contact_id):
    """Send catalog to a specific customer"""
    try:
        contact = Contact.objects.get(phone_number=contact_id)
    except Contact.DoesNotExist:
        contact = get_object_or_404(Contact, pk=contact_id)
    
    if request.method == 'POST':
        catalog_type = request.POST.get('catalog_type')
        method = request.POST.get('method', 'whatsapp')
        message = request.POST.get('message', '')
        
        # Create outbound activity for catalog sending
        activity = OutboundActivity.objects.create(
            contact=contact,
            method=method,
            summary=f"Sent {catalog_type} catalog via {method.title()}",
            details=message,
            next_step='follow_up',
            next_step_date=timezone.now() + timedelta(days=3),  # Follow up in 3 days
            created_by=request.user
        )
        
        # You can add actual catalog sending logic here
        # For now, we'll just log the activity
        
        messages.success(request, f'Catalog sent to {contact.full_name} successfully!')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'activity_id': activity.id})
        
        return redirect('outbound_app:customer_outbound', contact_id=contact.pk)
    
    # Available catalog types (you can make this configurable)
    catalog_types = [
        ('safety_equipment', 'Safety Equipment Catalog'),
        ('new_arrivals', 'New Arrivals Catalog'),
        ('seasonal_offers', 'Seasonal Offers Catalog'),
        ('complete_catalog', 'Complete Product Catalog'),
    ]
    
    context = {
        'contact': contact,
        'catalog_types': catalog_types,
    }
    
    return render(request, 'outbound_app/send_catalog.html', context)
