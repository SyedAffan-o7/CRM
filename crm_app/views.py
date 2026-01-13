from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.db import connection
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from leads_app.models import Lead, Reason, LeadSource, Product, LeadProduct, FollowUp
from accounts_app.models import Account, UserProfile
from customers_app.models import Contact
from deals_app.models import Deal
from activities_app.models import ActivityLog
from outbound_app.models import OutboundActivity
from django.contrib.auth.forms import UserCreationForm
from products.models import Category, Subcategory
from .forms import LeadForm, ContactForm, AccountForm, DealForm, ActivityLogForm


def _is_super_admin(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    profile = getattr(user, 'profile', None)
    role = getattr(profile, 'role', None) if profile else None
    return getattr(role, 'name', None) == 'SUPERUSER'


@login_required
def enquiry_stages(request):
    """Kanban-style view of enquiries sorted by stage."""
    # Get filters from request
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    month_filter = request.GET.get('month_filter')
    year_filter = request.GET.get('year_filter')

    # Initialize date variables
    from_date, to_date, selected_month, selected_year = None, None, None, None

    # Handle month filter
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
            pass  # Ignore invalid month/year
    elif from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass  # Ignore invalid date format

    # Get all stage choices from the Lead model
    stage_choices = dict(Lead.ENQUIRY_STAGE_CHOICES)
    stages = {key: {"name": name, "leads": []} for key, name in stage_choices.items()}

    # Base queryset with prefetching
    base_leads_qs = Lead.objects.select_related(
        'assigned_sales_person', 'created_by'
    ).prefetch_related('products_enquired')

    # Apply user-based filtering
    user_profile = getattr(request.user, 'profile', None)
    user_role = user_profile.role.name if user_profile and user_profile.role else None

    if not (request.user.is_superuser or user_role in ['ADMIN', 'MANAGER']):
        # Regular users see only their own leads
        base_leads_qs = base_leads_qs.filter(Q(created_by=request.user) | Q(assigned_sales_person=request.user))

    # Apply date filtering if dates are set
    if from_date and to_date:
        leads = base_leads_qs.filter(created_date__date__gte=from_date, created_date__date__lte=to_date)
    else:
        leads = base_leads_qs.all()

    # Distribute leads into their respective stages
    for lead in leads.order_by('-created_date'):
        if lead.enquiry_stage in stages:
            stages[lead.enquiry_stage]['leads'].append(lead)

    # Get all reasons for the 'Lost' modal
    reasons = Reason.objects.filter(is_active=True)

    context = {
        'stages': stages,
        'reasons': reasons,
        'page_title': 'Enquiry Stages',
        'from_date': from_date,
        'to_date': to_date,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }
    return render(request, 'crm_app/enquiry_stages.html', context)


@login_required
def dashboard(request):
    """Dashboard view with key metrics"""
    # Get filters from request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date') 
    month_filter = request.GET.get('month_filter')
    year_filter = request.GET.get('year_filter')
    
    # Handle month filter
    if month_filter:
        selected_month = int(month_filter)
        selected_year = int(year_filter) if year_filter else timezone.now().year
        
        # Set date range to the selected month
        from_date = datetime(selected_year, selected_month, 1).date()
        # Get last day of the month
        if selected_month == 12:
            to_date = datetime(selected_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            to_date = datetime(selected_year, selected_month + 1, 1).date() - timedelta(days=1)
    elif from_date and to_date:
        # Use custom date range
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        selected_month = None
        selected_year = None
    else:
        # Default to current month
        now = timezone.now()
        from_date = now.replace(day=1).date()
        to_date = now.date()
        selected_month = now.month
        selected_year = now.year
    
    # Get selected employee filter
    selected_employee = request.GET.get('employee')
    
    # Filter enquiries by date range - super admin sees all, normal users see only their own
    if request.user.is_superuser:
        enquiries_in_range = Lead.objects.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date
        )
        if selected_employee:
            enquiries_in_range = enquiries_in_range.filter(created_by__id=selected_employee)
        # Get all salesmen (users who have assigned leads)
        salesmen = User.objects.filter(assigned_leads__isnull=False).distinct().order_by('id')
        if selected_employee:
            salesmen = User.objects.filter(id=selected_employee)
    else:
        enquiries_in_range = Lead.objects.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date,
            created_by=request.user
        )
        # For normal users, only show their own data
        salesmen = User.objects.filter(id=request.user.id)
    
    # Current month metrics
    total_enquiries_month = enquiries_in_range.count()
    fulfilled_month = enquiries_in_range.filter(lead_status='fulfilled').count()
    not_fulfilled_month = enquiries_in_range.filter(lead_status='not_fulfilled').count()
    fulfillment_rate = round((fulfilled_month / total_enquiries_month) * 100, 1) if total_enquiries_month > 0 else 0
    
    # Role-based sales performance data
    user_sales_data = None
    show_all_sales = False

    # Check user role and permissions
    try:
        user_profile = request.user.profile
        user_role = user_profile.role.name if user_profile.role else None

        # Super admin and managers can see all sales data
        if request.user.is_superuser or user_role in ['ADMIN', 'MANAGER']:
            show_all_sales = True
        else:
            # Regular users see only their own data
            user_enquiries = enquiries_in_range.filter(created_by=request.user)
            user_sales_data = {
                'name': request.user.get_full_name() or request.user.username,
                'user_id': request.user.id,
                'total': user_enquiries.count(),
                'fulfilled': user_enquiries.filter(lead_status='fulfilled').count(),
                'not_fulfilled': user_enquiries.filter(lead_status='not_fulfilled').count(),
            }
            if user_sales_data['total'] > 0:
                user_sales_data['fulfillment_rate'] = round((user_sales_data['fulfilled'] / user_sales_data['total']) * 100, 1)
            else:
                user_sales_data['fulfillment_rate'] = 0
    except (UserProfile.DoesNotExist, AttributeError):
        # Fallback for users without profiles
        if request.user.is_superuser:
            show_all_sales = True
        else:
            user_enquiries = enquiries_in_range.filter(created_by=request.user)
            user_sales_data = {
                'name': request.user.get_full_name() or request.user.username,
                'user_id': request.user.id,
                'total': user_enquiries.count(),
                'fulfilled': user_enquiries.filter(lead_status='fulfilled').count(),
                'not_fulfilled': user_enquiries.filter(lead_status='not_fulfilled').count(),
            }
            if user_sales_data['total'] > 0:
                user_sales_data['fulfillment_rate'] = round((user_sales_data['fulfilled'] / user_sales_data['total']) * 100, 1)
            else:
                user_sales_data['fulfillment_rate'] = 0

    # Legacy sales data for backward compatibility (only if showing all sales)
    sales1_total = sales1_fulfilled = sales1_not_fulfilled = sales1_fulfillment_rate = 0
    sales2_total = sales2_fulfilled = sales2_not_fulfilled = sales2_fulfillment_rate = 0
    sales1_name = "Sales Person 1"
    sales2_name = "Sales Person 2"
    sales1_user_id = None
    sales2_user_id = None

    if show_all_sales and salesmen.exists():
        if selected_employee:
            # When an employee is selected, show only that employee's data
            selected_user = User.objects.get(id=selected_employee)
            sales1_name = selected_user.get_full_name() or selected_user.username
            sales1_user_id = selected_user.id
            sales1_enquiries = enquiries_in_range.filter(created_by=selected_user)
            sales1_total = sales1_enquiries.count()
            sales1_fulfilled = sales1_enquiries.filter(lead_status='fulfilled').count()
            sales1_not_fulfilled = sales1_enquiries.filter(lead_status='not_fulfilled').count()
            sales1_fulfillment_rate = round((sales1_fulfilled / sales1_total) * 100, 1) if sales1_total > 0 else 0

            # Clear sales2 data when showing single employee
            sales2_name = ""
            sales2_user_id = None
            sales2_total = 0
            sales2_fulfilled = 0
            sales2_not_fulfilled = 0
            sales2_fulfillment_rate = 0
        else:
            # Default behavior: Sales 1 (first salesman)
            sales1 = salesmen[0]
            sales1_name = sales1.get_full_name() or sales1.username
            sales1_user_id = sales1.id
            sales1_enquiries = enquiries_in_range.filter(created_by=sales1)
            sales1_total = sales1_enquiries.count()
            sales1_fulfilled = sales1_enquiries.filter(lead_status='fulfilled').count()
            sales1_not_fulfilled = sales1_enquiries.filter(lead_status='not_fulfilled').count()
            sales1_fulfillment_rate = round((sales1_fulfilled / sales1_total) * 100, 1) if sales1_total > 0 else 0

            # Sales 2 (second salesman if exists)
            if len(salesmen) > 1:
                sales2 = salesmen[1]
                sales2_name = sales2.get_full_name() or sales2.username
                sales2_user_id = sales2.id
                sales2_enquiries = enquiries_in_range.filter(created_by=sales2)
                sales2_total = sales2_enquiries.count()
                sales2_fulfilled = sales2_enquiries.filter(lead_status='fulfilled').count()
                sales2_not_fulfilled = sales2_enquiries.filter(lead_status='not_fulfilled').count()
                sales2_fulfillment_rate = round((sales2_fulfilled / sales2_total) * 100, 1) if sales2_total > 0 else 0
    
    # Get current month name for display
    current_month_name = from_date.strftime('%B %Y')
    
    # Base queryset for follow-ups with common filters and related fields
    base_followup_qs = FollowUp.objects.filter(
        Q(status='pending') | Q(status='overdue')
    ).select_related('lead', 'assigned_to')
    
    # Apply permission filters for non-superusers
    if not request.user.is_superuser:
        base_followup_qs = base_followup_qs.filter(
            Q(assigned_to=request.user) |
            Q(lead__assigned_sales_person=request.user) |
            Q(created_by=request.user)
        ).distinct()
    elif selected_employee:
        # If superuser selected an employee, filter followups for that employee
        base_followup_qs = base_followup_qs.filter(
            Q(assigned_to__id=selected_employee) |
            Q(lead__assigned_sales_person__id=selected_employee) |
            Q(created_by__id=selected_employee)
        ).distinct()

    # Apply date range to follow-ups so dashboard filters affect follow-up stats
    if from_date and to_date:
        base_followup_qs = base_followup_qs.filter(
            scheduled_date__date__gte=from_date,
            scheduled_date__date__lte=to_date,
        )
    
    # Get current time and today's date range
    now = timezone.now()
    today = now.date()
    
    # Get follow-ups for different time periods using the base queryset
    followups_overdue = base_followup_qs.filter(
        scheduled_date__lt=now
    ).order_by('scheduled_date')
    
    followups_today = base_followup_qs.filter(
        scheduled_date__date=today
    ).order_by('scheduled_date')
    
    followups_upcoming = base_followup_qs.filter(
        scheduled_date__gt=now
    ).order_by('scheduled_date')
    
    # Get follow-up statistics
    followup_stats = {
        'total': base_followup_qs.count(),
        'overdue': followups_overdue.count(),
        'today': followups_today.count(),
        'upcoming': followups_upcoming.count(),
    }
    
    # Get recent leads for the follow-up form
    if request.user.is_superuser:
        # Superusers can see global recent leads or filter by employee
        recent_leads_qs = Lead.objects.all()
        if selected_employee:
            recent_leads_qs = recent_leads_qs.filter(
                Q(assigned_sales_person__id=selected_employee) |
                Q(created_by__id=selected_employee)
            )
    else:
        # Regular users see only their own recent leads
        recent_leads_qs = Lead.objects.filter(
            Q(assigned_sales_person=request.user) |
            Q(created_by=request.user)
        )

    # Apply date range to recent leads so they follow the dashboard filters
    if from_date and to_date:
        recent_leads_qs = recent_leads_qs.filter(
            created_date__date__gte=from_date,
            created_date__date__lte=to_date,
        )

    recent_leads = recent_leads_qs.order_by('-created_date')[:20]
    
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
        'current_month_name': current_month_name,
        'followups_overdue': followups_overdue,
        'followups_today': followups_today,
        'followups_upcoming': followups_upcoming,
        'followup_stats': followup_stats,
        'recent_leads': recent_leads,
        # Role-based display data
        'show_all_sales': show_all_sales,
        'user_sales_data': user_sales_data,
        'selected_employee': selected_employee,
        'all_employees': User.objects.filter(is_active=True).order_by('username') if request.user.is_superuser else None,
    }
    return render(request, 'crm_app/dashboard.html', context)


@login_required
@user_passes_test(_is_super_admin)
def report_enquiries_pipeline(request):
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    stage_filter = request.GET.get('stage')
    status_filter = request.GET.get('status')
    lead_source_filter = request.GET.get('lead_source')
    salesperson_filter = request.GET.get('salesperson')

    if from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            from_date = None
            to_date = None
    else:
        from_date = None
        to_date = None

    if from_date is None or to_date is None:
        now = timezone.now()
        from_date = now.replace(day=1).date()
        to_date = now.date()

    leads_qs = (
        Lead.objects.select_related('lead_source', 'assigned_sales_person', 'created_by')
        .filter(created_date__date__gte=from_date, created_date__date__lte=to_date)
    )

    if stage_filter:
        leads_qs = leads_qs.filter(enquiry_stage=stage_filter)
    if status_filter:
        leads_qs = leads_qs.filter(lead_status=status_filter)
    if lead_source_filter:
        leads_qs = leads_qs.filter(lead_source_id=lead_source_filter)
    if salesperson_filter:
        leads_qs = leads_qs.filter(assigned_sales_person_id=salesperson_filter)

    total_leads = leads_qs.count()
    fulfilled_count = leads_qs.filter(lead_status='fulfilled').count()
    not_fulfilled_count = leads_qs.filter(lead_status='not_fulfilled').count()

    stage_counts = {
        row['enquiry_stage']: row['count']
        for row in leads_qs.values('enquiry_stage').annotate(count=Count('id'))
    }
    stage_stats = []
    for stage_key, stage_label in Lead.ENQUIRY_STAGE_CHOICES:
        c = stage_counts.get(stage_key, 0)
        pct = round((c / total_leads) * 100, 1) if total_leads else 0
        stage_stats.append({'stage': stage_key, 'label': stage_label, 'count': c, 'percent': pct})

    source_stats = (
        leads_qs.values('lead_source__id', 'lead_source__name')
        .annotate(
            total=Count('id'),
            fulfilled=Count('id', filter=Q(lead_status='fulfilled')),
            lost=Count('id', filter=Q(enquiry_stage='lost')),
        )
        .order_by('-total')
    )

    salesperson_stats = (
        leads_qs.values(
            'assigned_sales_person__id',
            'assigned_sales_person__username',
            'assigned_sales_person__first_name',
            'assigned_sales_person__last_name',
        )
        .annotate(
            total=Count('id'),
            fulfilled=Count('id', filter=Q(lead_status='fulfilled')),
            lost=Count('id', filter=Q(enquiry_stage='lost')),
        )
        .order_by('-total')
    )

    lead_sources = LeadSource.objects.filter(is_active=True).order_by('name')
    salespeople = User.objects.filter(is_active=True).order_by('username')

    paginator = Paginator(leads_qs.order_by('-created_date'), 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'stage_filter': stage_filter,
        'status_filter': status_filter,
        'lead_source_filter': lead_source_filter,
        'salesperson_filter': salesperson_filter,
        'lead_sources': lead_sources,
        'salespeople': salespeople,
        'total_leads': total_leads,
        'fulfilled_count': fulfilled_count,
        'not_fulfilled_count': not_fulfilled_count,
        'fulfillment_rate': round((fulfilled_count / total_leads) * 100, 1) if total_leads else 0,
        'stage_stats': stage_stats,
        'source_stats': source_stats,
        'salesperson_stats': salesperson_stats,
        'page_obj': page_obj,
        'stage_choices': Lead.ENQUIRY_STAGE_CHOICES,
        'status_choices': Lead.STATUS_CHOICES,
    }
    return render(request, 'crm_app/report_enquiries_pipeline.html', context)


@login_required
@user_passes_test(_is_super_admin)
def report_followups_compliance(request):
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    assigned_to_filter = request.GET.get('assigned_to')
    status_filter = request.GET.get('status')

    if from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            from_date = None
            to_date = None
    else:
        from_date = None
        to_date = None

    if from_date is None or to_date is None:
        now = timezone.now()
        from_date = now.replace(day=1).date()
        to_date = now.date()

    qs = (
        FollowUp.objects.select_related('lead', 'assigned_to', 'created_by')
        .filter(scheduled_date__date__gte=from_date, scheduled_date__date__lte=to_date)
    )

    if assigned_to_filter:
        qs = qs.filter(assigned_to_id=assigned_to_filter)

    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    now = timezone.now()
    today = now.date()

    overdue_qs = qs.filter(Q(status='pending') | Q(status='overdue')).filter(scheduled_date__lt=now)
    today_qs = qs.filter(Q(status='pending') | Q(status='overdue')).filter(scheduled_date__date=today)
    upcoming_qs = qs.filter(Q(status='pending') | Q(status='overdue')).filter(scheduled_date__gt=now)
    completed_qs = qs.filter(status='completed')

    stats = {
        'total': qs.count(),
        'overdue': overdue_qs.count(),
        'today': today_qs.count(),
        'upcoming': upcoming_qs.count(),
        'completed': completed_qs.count(),
    }
    stats['completion_rate'] = round((stats['completed'] / stats['total']) * 100, 1) if stats['total'] else 0

    user_stats = (
        qs.values('assigned_to__id', 'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name')
        .annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            overdue=Count('id', filter=(Q(status__in=['pending', 'overdue']) & Q(scheduled_date__lt=now))),
            due_today=Count('id', filter=(Q(status__in=['pending', 'overdue']) & Q(scheduled_date__date=today))),
            upcoming=Count('id', filter=(Q(status__in=['pending', 'overdue']) & Q(scheduled_date__gt=now))),
        )
        .order_by('-overdue', '-total')
    )

    assignees = User.objects.filter(is_active=True).order_by('username')

    paginator = Paginator(qs.order_by('scheduled_date'), 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'assigned_to_filter': assigned_to_filter,
        'status_filter': status_filter or 'all',
        'assignees': assignees,
        'stats': stats,
        'user_stats': user_stats,
        'page_obj': page_obj,
        'status_choices': FollowUp.STATUS_CHOICES,
    }
    return render(request, 'crm_app/report_followups_compliance.html', context)


@login_required
def get_subcategories(request, category_id):
    """API endpoint to get subcategories for a given category."""
    subcategories = Subcategory.objects.filter(category_id=category_id, is_active=True).order_by('name')
    data = [{'id': sub.id, 'name': sub.name} for sub in subcategories]
    return JsonResponse(data, safe=False)


def healthz(request):
    """Simple health check that verifies DB connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        return JsonResponse({"status": "ok", "db": row[0] == 1})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


@login_required
def analytics_overview(request):
    """API endpoint for dashboard analytics charts"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Get date range from query params
    from_date_str = request.GET.get('from_date') or None
    to_date_str = request.GET.get('to_date') or None
    month_filter = request.GET.get('month_filter')
    year_filter = request.GET.get('year_filter')

    # Determine date range
    from_date = to_date = None

    # 1) Explicit from/to dates take priority
    if from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            from_date = to_date = None

    # 2) Month-based filter when no valid explicit range
    if (from_date is None or to_date is None) and month_filter:
        try:
            selected_month = int(month_filter)
            selected_year = int(year_filter) if year_filter else timezone.now().year
            from_date = datetime(selected_year, selected_month, 1).date()
            # Last day of the month
            if selected_month == 12:
                to_date = datetime(selected_year + 1, 1, 1).date() - timedelta(days=1)
            else:
                to_date = datetime(selected_year, selected_month + 1, 1).date() - timedelta(days=1)
        except (ValueError, TypeError):
            from_date = to_date = None

    # 3) Fallback: last 30 days
    if from_date is None or to_date is None:
        to_date = timezone.now().date()
        from_date = to_date - timedelta(days=30)

    # Get employee filter
    employee_id = request.GET.get('employee')
    print(f"DEBUG analytics_overview: employee_id = {employee_id}, user = {request.user.username}, is_superuser = {request.user.is_superuser}")

    # Base queryset for outbound activities (for charts and leaderboard)
    activities = OutboundActivity.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
        created_by__isnull=False
    )
    print(f"DEBUG analytics_overview: Initial activities count = {activities.count()}")

    # Normalize employee_id to int if provided
    selected_emp_id = None
    if employee_id:
        try:
            selected_emp_id = int(employee_id)
        except (TypeError, ValueError):
            selected_emp_id = None

    print(f"DEBUG analytics_overview: selected_emp_id = {selected_emp_id}")

    # Apply filtering logic
    if selected_emp_id is not None:
        # When an employee is selected, always filter to that employee
        activities = activities.filter(created_by__id=selected_emp_id)
        print(f"DEBUG analytics_overview: Filtered by employee {selected_emp_id}, activities count = {activities.count()}")
    elif not request.user.is_superuser:
        # Non-superusers only see their own data
        activities = activities.filter(created_by=request.user)
        print(f"DEBUG analytics_overview: Filtered by user {request.user.username}, activities count = {activities.count()}")

    print(f"DEBUG analytics_overview: Final activities count = {activities.count()}")
    print(f"DEBUG analytics_overview: Unique created_by IDs: {list(activities.values_list('created_by__username', flat=True).distinct())}")

    # Method breakdown
    method_breakdown = activities.values('method').annotate(
        count=Count('id')
    ).order_by('-count')

    # Convert method codes to display names
    method_display_map = {
        'PHONE': 'Phone Call',
        'WHATSAPP': 'WhatsApp',
        'EMAIL': 'Email',
        'SMS': 'SMS',
        'MEETING': 'Meeting',
        'VIDEO_CALL': 'Video Call',
        'LINKEDIN': 'LinkedIn',
        'OTHER': 'Other'
    }

    method_breakdown_data = []
    for item in method_breakdown:
        method_code = item['method']
        method_breakdown_data.append({
            'method': method_display_map.get(method_code, method_code),
            'count': item['count']
        })

    # Outcome breakdown
    outcome_breakdown = activities.exclude(
        outcome=''
    ).values('outcome').annotate(
        count=Count('id')
    ).order_by('-count')

    outcome_display_map = {
        'POSITIVE': 'Positive Response',
        'NEUTRAL': 'Neutral Response',
        'NEGATIVE': 'Negative Response',
        'NO_RESPONSE': 'No Response',
        'CALLBACK_REQUESTED': 'Callback Requested',
        'NOT_INTERESTED': 'Not Interested',
        'INTERESTED': 'Showed Interest',
        'MEETING_SCHEDULED': 'Meeting Scheduled'
    }

    outcome_breakdown_data = []
    for item in outcome_breakdown:
        outcome_code = item['outcome']
        outcome_breakdown_data.append({
            'outcome': outcome_display_map.get(outcome_code, outcome_code),
            'count': item['count']
        })

    # Salesperson leaderboard based on enquiries (Lead data)
    # Owner rule per enquiry:
    #   - if assigned_sales_person is set, the enquiry belongs to that salesperson
    #   - otherwise it belongs to created_by
    # We consider ALL enquiries (lifetime), not limited by date, so that
    # each salesperson card reflects their full portfolio.
    leads_qs = Lead.objects.all()

    # Apply employee filter to leads according to the owner rule
    if selected_emp_id is not None and request.user.is_superuser:
        # For a selected employee, include enquiries where they are either assigned
        # or, when not assigned, they are the creator
        leads_qs = leads_qs.filter(
            Q(assigned_sales_person__id=selected_emp_id)
            | (Q(assigned_sales_person__isnull=True) & Q(created_by__id=selected_emp_id))
        )
    elif not request.user.is_superuser:
        # Regular users see only enquiries they own (assigned or created)
        leads_qs = leads_qs.filter(
            Q(assigned_sales_person=request.user) | Q(created_by=request.user)
        )

    # Aggregate in two steps to respect the owner rule and avoid double counting
    owner_stats = {}

    # 1) Leads with assigned_sales_person -> owner is assigned_sales_person
    assigned_stats = leads_qs.filter(
        assigned_sales_person__isnull=False
    ).values(
        'assigned_sales_person__id',
        'assigned_sales_person__username',
        'assigned_sales_person__first_name',
        'assigned_sales_person__last_name',
    ).annotate(
        total_enquiries=Count('id'),
        total_fulfilled=Count('id', filter=Q(lead_status='fulfilled')),
        # Treat any status that is not 'fulfilled' as not fulfilled
        total_not_fulfilled=Count('id', filter=~Q(lead_status='fulfilled')),
    )

    for item in assigned_stats:
        uid = item['assigned_sales_person__id']
        full_name = f"{item['assigned_sales_person__first_name']} {item['assigned_sales_person__last_name']}".strip()
        if not full_name:
            full_name = item['assigned_sales_person__username']

        owner_stats[uid] = {
            'user_id': uid,
            'full_name': full_name,
            'username': item['assigned_sales_person__username'],
            'total_enquiries': item['total_enquiries'],
            'total_fulfilled': item['total_fulfilled'],
            'total_not_fulfilled': item['total_not_fulfilled'],
        }

    # 2) Leads without assigned_sales_person but with created_by -> owner is creator
    created_stats = leads_qs.filter(
        assigned_sales_person__isnull=True,
        created_by__isnull=False,
    ).values(
        'created_by__id',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name',
    ).annotate(
        total_enquiries=Count('id'),
        total_fulfilled=Count('id', filter=Q(lead_status='fulfilled')),
        # Treat any status that is not 'fulfilled' as not fulfilled
        total_not_fulfilled=Count('id', filter=~Q(lead_status='fulfilled')),
    )

    for item in created_stats:
        uid = item['created_by__id']
        full_name = f"{item['created_by__first_name']} {item['created_by__last_name']}".strip()
        if not full_name:
            full_name = item['created_by__username']

        if uid in owner_stats:
            owner_stats[uid]['total_enquiries'] += item['total_enquiries']
            owner_stats[uid]['total_fulfilled'] += item['total_fulfilled']
            owner_stats[uid]['total_not_fulfilled'] += item['total_not_fulfilled']
        else:
            owner_stats[uid] = {
                'user_id': uid,
                'full_name': full_name,
                'username': item['created_by__username'],
                'total_enquiries': item['total_enquiries'],
                'total_fulfilled': item['total_fulfilled'],
                'total_not_fulfilled': item['total_not_fulfilled'],
            }

    # Convert to sorted list (most enquiries first)
    leaderboard_data = sorted(
        owner_stats.values(),
        key=lambda x: x['total_enquiries'],
        reverse=True,
    )

    print(f"DEBUG analytics_overview: Leaderboard count = {len(leaderboard_data)}")
    print(f"DEBUG analytics_overview: Leaderboard usernames = {[row['username'] for row in leaderboard_data]}")

    # Get enquiries generated from outbound activities
    enquiries_qs = Lead.objects.filter(
        created_date__date__gte=from_date,
        created_date__date__lte=to_date
    )

    # Filter enquiries by employee if specified and user is superuser
    if employee_id and request.user.is_superuser:
        enquiries_qs = enquiries_qs.filter(created_by__id=employee_id)
    elif not request.user.is_superuser:
        enquiries_qs = enquiries_qs.filter(created_by=request.user)

    enquiries_from_outbound = enquiries_qs.count()

    data = {
        'method_breakdown': method_breakdown_data,
        'outcome_breakdown': outcome_breakdown_data,
        'leaderboard': leaderboard_data,
        'total_activities': activities.count(),
        'unique_customers_contacted': activities.values('contact').distinct().count(),
        'enquiries_generated': enquiries_from_outbound,
        'date_range': {
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d')
        }
    }

    return JsonResponse(data)

def settings(request):
    # Show the general settings page
    return render(request, 'crm_app/settings.html')

def user_list(request):
    # This view is deprecated - URLs are now handled by accounts_app
    return redirect('accounts_app:user_management')

def user_add(request):
    # This view is deprecated - URLs are now handled by accounts_app
    return redirect('accounts_app:user_management')

def user_toggle_status(request, pk):
    return JsonResponse({'success': False, 'error': 'Not implemented'})

def user_delete(request, pk):
    # This view is deprecated - URLs are now handled by accounts_app
    return redirect('accounts_app:user_management')

def lead_source_list(request):
    return render(request, 'crm_app/lead_source_list.html', {'lead_sources': []})

def lead_source_add(request):
    return redirect('crm_app:lead_source_list')

def lead_source_edit(request, pk):
    return redirect('crm_app:lead_source_list')

def lead_source_delete(request, pk):
    return redirect('crm_app:lead_source_list')

def reason_list(request):
    return render(request, 'crm_app/reason_list.html', {'reasons': []})

def reason_add(request):
    return redirect('crm_app:reason_list')

def reason_edit(request, pk):
    return redirect('crm_app:reason_list')

def reason_delete(request, pk):
    return redirect('crm_app:reason_list')

def account_list(request):
    return render(request, 'crm_app/account_list.html', {'accounts': []})

def account_add(request):
    return redirect('crm_app:account_list')

def account_detail(request, pk):
    return redirect('crm_app:account_list')

def account_edit(request, pk):
    return redirect('crm_app:account_list')

def deal_list(request):
    return render(request, 'crm_app/deal_list.html', {'deals': []})

def deal_add(request):
    return redirect('crm_app:deal_list')

def deal_detail(request, pk):
    return redirect('crm_app:deal_list')

def deal_edit(request, pk):
    return redirect('crm_app:deal_list')


@login_required
def lead_delete(request, pk):
    """Delete a lead with proper permissions"""
    lead = get_object_or_404(Lead, pk=pk)

    # Check permissions: only superuser, creator, or assigned salesperson can delete
    can_delete = False
    if request.user.is_superuser:
        can_delete = True
    elif lead.created_by == request.user or lead.assigned_sales_person == request.user:
        can_delete = True
    else:
        # Check role-based permissions
        try:
            user_profile = request.user.profile
            user_role = user_profile.role.name if user_profile.role else None
            if user_role in ['ADMIN', 'MANAGER']:
                can_delete = True
        except Exception:
            pass

    if not can_delete:
        messages.error(request, 'You do not have permission to delete this enquiry.')
        return redirect('crm_app:lead_list')

    if request.method == 'POST':
        lead.delete()
        messages.success(request, f'Enquiry "{lead.contact_name}" has been deleted successfully.')
        return redirect('crm_app:lead_list')

    # For GET requests, show confirmation
    return render(request, 'crm_app/lead_confirm_delete.html', {
        'lead': lead,
        'title': 'Delete Enquiry'
    })


@login_required
def lead_products_api(request, lead_id):
    """API endpoint to get products, categories, and images for a specific lead."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        lead = get_object_or_404(Lead, pk=lead_id)

        # Check permissions
        # Allowed when:
        # - superuser
        # - creator or assigned salesperson of this lead
        # - MANAGER/ADMIN roles
        # - user has any lead for the same contact (created_by or assigned)
        allowed = False
        if request.user.is_superuser:
            allowed = True
        elif (lead.created_by == request.user) or (lead.assigned_sales_person == request.user):
            allowed = True
        else:
            # Role-based: MANAGER or ADMIN
            try:
                user_profile = request.user.profile
                user_role = user_profile.role.name if user_profile and user_profile.role else None
                if user_role in ['ADMIN', 'MANAGER']:
                    allowed = True
            except Exception:
                pass

            # Same-contact access: has any lead with same contact
            if not allowed and getattr(lead, 'contact', None):
                same_contact_exists = Lead.objects.filter(
                    contact=lead.contact
                ).filter(
                    Q(created_by=request.user) | Q(assigned_sales_person=request.user)
                ).exists()
                if same_contact_exists:
                    allowed = True

        if not allowed:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        # Backward-compatible response structure
        data = {
            'products': [],            # legacy products list (name/description/category)
            'categories': [],          # legacy categories
            'images': [],              # legacy images
            'lead_products': []        # new, detailed lead product entries
        }

        # Legacy: products_enquired M2M summary (no quantity/price)
        products = lead.products_enquired.all()
        for product in products:
            data['products'].append({
                'id': getattr(product, 'id', None),
                'name': getattr(product, 'name', '') or '',
                'description': getattr(product, 'description', '') or '',
                'category': getattr(product, 'category', '') or '',
                'image': None
            })

        # Legacy: enquiry-level categories
        if getattr(lead, 'category', None):
            try:
                data['categories'].append(lead.category.name)
            except Exception:
                pass
        if getattr(lead, 'subcategory', None):
            try:
                data['categories'].append(lead.subcategory.name)
            except Exception:
                pass

        # Legacy: enquiry-level image
        if getattr(lead, 'images', None):
            try:
                if lead.images:
                    data['images'].append(lead.images.url)
            except Exception:
                pass

        # New: detailed LeadProduct entries
        lead_products = LeadProduct.objects.filter(lead=lead)
        for lp in lead_products:
            lp_entry = {
                'id': lp.id,
                'category': getattr(getattr(lp, 'category', None), 'name', None),
                'subcategory': getattr(getattr(lp, 'subcategory', None), 'name', None),
                'description': getattr(lp, 'description', '') or '',
                'quantity': getattr(lp, 'quantity', None),
                'price': getattr(lp, 'price', None),
                'image': None
            }
            try:
                if getattr(lp, 'image', None):
                    lp_entry['image'] = lp.image.url
                    data['images'].append(lp.image.url)
            except Exception:
                pass
            data['lead_products'].append(lp_entry)

        # Fallback: if no LeadProduct entries, use lead's category/subcategory
        if not lead_products.exists():
            fallback_entry = {
                'id': None,
                'category': getattr(getattr(lead, 'category', None), 'name', None),
                'subcategory': getattr(getattr(lead, 'subcategory', None), 'name', None),
                'description': 'No detailed product information available',
                'quantity': None,
                'price': None,
                'image': None
            }
            data['lead_products'].append(fallback_entry)

        return JsonResponse(data)

    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
