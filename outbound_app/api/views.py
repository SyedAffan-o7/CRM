from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg, F, Case, When, IntegerField
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from urllib.parse import quote
from customers_app.models import Contact
from outbound_app.models import OutboundActivity, MessageTemplate, Campaign
from leads_app.models import Lead, FollowUp

from .serializers import (
    ContactSerializer,
    OutboundActivitySerializer,
    QuickActivitySerializer,
    EnquiryCreateSerializer,
    MessageTemplateSerializer,
    CampaignSerializer,
    UserSerializer,
    ContactStatsSerializer,
    SalespersonStatsSerializer,
)


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user and request.user.is_authenticated


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ContactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Contact.objects.all().select_related('company').prefetch_related('outbound_activities', 'leads').order_by('full_name')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['outbound_status', 'company']
    search_fields = ['full_name', 'phone_number', 'whatsapp_number', 'company__company_name']
    ordering_fields = ['full_name', 'last_contacted', 'outbound_status']

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by days since last contact
        days_since = self.request.query_params.get('days_since_last_contact')
        if days_since:
            try:
                days = int(days_since)
                cutoff_date = timezone.now() - timedelta(days=days)
                qs = qs.filter(Q(last_contacted__lte=cutoff_date) | Q(last_contacted__isnull=True))
            except ValueError:
                pass
        
        # Filter by follow-up due
        follow_up_due = self.request.query_params.get('follow_up_due')
        if follow_up_due == 'true':
            qs = qs.filter(
                outbound_activities__follow_up_reminder__lte=timezone.now(),
                outbound_activities__follow_up_reminder__isnull=False
            ).distinct()
        
        return qs

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None, format=None):
        """Get all outbound activities for a specific contact"""
        contact = self.get_object()
        activities = OutboundActivity.objects.select_related(
            'contact', 'lead', 'created_by', 'campaign', 'template_used'
        ).filter(contact=contact).order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(activities, request)
        if page is not None:
            serializer = OutboundActivitySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = OutboundActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def quick_activity(self, request, pk=None, format=None):
        """Quickly log an activity for a contact"""
        contact = self.get_object()
        data = request.data.copy()
        data['contact_id'] = contact.id
        
        serializer = QuickActivitySerializer(data=data)
        if serializer.is_valid():
            # Create full activity
            activity_data = {
                'contact': contact,
                'method': serializer.validated_data['method'],
                'outcome': serializer.validated_data.get('outcome', ''),
                'summary': serializer.validated_data.get('summary', ''),
                'next_step': serializer.validated_data.get('next_step', 'NONE'),
                'duration_minutes': serializer.validated_data.get('duration_minutes'),
                'created_by': request.user if request.user.is_authenticated else None
            }
            
            # Add template if provided
            template_id = serializer.validated_data.get('template_id')
            if template_id:
                try:
                    template = MessageTemplate.objects.get(id=template_id)
                    activity_data['template_used'] = template
                except MessageTemplate.DoesNotExist:
                    pass
            
            activity = OutboundActivity.objects.create(**activity_data)
            return Response(OutboundActivitySerializer(activity).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def create_enquiry(self, request, pk=None, format=None):
        """Create an enquiry from this contact"""
        contact = self.get_object()
        data = request.data.copy()
        data['contact'] = contact.id
        
        serializer = EnquiryCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            lead = serializer.save()
            return Response({'id': lead.id, 'contact_name': lead.contact_name}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OutboundActivityViewSet(viewsets.ModelViewSet):
    queryset = OutboundActivity.objects.select_related(
        'contact', 'lead', 'created_by', 'campaign', 'template_used'
    ).all().order_by('-created_at')
    serializer_class = OutboundActivitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['method', 'outcome', 'next_step', 'contact__outbound_status']
    search_fields = ['summary', 'detailed_notes', 'contact__full_name']
    ordering_fields = ['created_at', 'next_step_date', 'follow_up_reminder']

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Contact filter
        contact_id = self.request.query_params.get('contact_id')
        if contact_id:
            qs = qs.filter(contact_id=contact_id)

        # Salesperson filter
        salesperson = self.request.query_params.get('salesperson')
        if salesperson:
            qs = qs.filter(created_by__username__icontains=salesperson)

        # Date range filters
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            try:
                dtf = datetime.fromisoformat(date_from)
                qs = qs.filter(created_at__gte=dtf)
            except Exception:
                pass
        if date_to:
            try:
                dtt = datetime.fromisoformat(date_to)
                qs = qs.filter(created_at__lte=dtt)
            except Exception:
                pass
        
        # Follow-up due filter
        follow_up_due = self.request.query_params.get('follow_up_due')
        if follow_up_due == 'true':
            qs = qs.filter(
                follow_up_reminder__lte=timezone.now(),
                follow_up_reminder__isnull=False
            )
        
        # Campaign filter
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        return qs

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['post'], url_path='create-enquiry')
    def create_enquiry(self, request, format=None):
        """Create an enquiry from activity data"""
        serializer = EnquiryCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            lead = serializer.save()
            return Response({'id': lead.id, 'contact_name': lead.contact_name}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def follow_ups_due(self, request, format=None):
        """Get activities with follow-ups due"""
        now = timezone.now()
        activities = self.get_queryset().filter(
            follow_up_reminder__lte=now,
            follow_up_reminder__isnull=False
        )
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(activities, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=['post'], url_path='create-enquiry')
    def create_enquiry_linked(self, request, pk=None, format=None):
        """Create an enquiry from this specific activity and link it back"""
        activity = self.get_object()
        data = request.data.copy()
        data['contact'] = activity.contact_id

        serializer = EnquiryCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            lead = serializer.save()
            # Link the lead back to the activity
            activity.lead = lead
            try:
                activity.save(update_fields=['lead'])
            except Exception:
                activity.save()
            return Response({'id': lead.id, 'contact_name': lead.contact_name, 'linked_activity': activity.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='communication-links')
    def communication_links(self, request, pk=None, format=None):
        """Return tel/whatsapp/mailto links for this activity's contact.
        Optionally personalize message via ?template_id=<id>."""
        activity = self.get_object()
        contact = activity.contact
        template_id = request.query_params.get('template_id')

        personalized_message = None
        subject = None
        if template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
                temp_activity = OutboundActivity(contact=contact, template_used=template)
                personalized_message = temp_activity.get_personalized_message(template)
                subject = template.subject
            except MessageTemplate.DoesNotExist:
                pass

        if not personalized_message:
            name = getattr(contact, 'full_name', '') or ''
            personalized_message = f"Hi {name}, this is a follow-up.".strip()
        if not subject:
            subject = f"Follow up - {getattr(contact, 'full_name', '')}".strip() or "Follow up"

        links = {}
        if getattr(contact, 'phone_number', None):
            links['phone'] = f"tel:{contact.phone_number}"
        if getattr(contact, 'whatsapp_number', None):
            wa_number = contact.whatsapp_number.replace('+', '').replace(' ', '')
            links['whatsapp'] = f"https://wa.me/{wa_number}?text={quote(personalized_message)}"
        email = getattr(contact, 'email', None)
        if email:
            links['email'] = f"mailto:{email}?subject={quote(subject)}&body={quote(personalized_message)}"

        return Response({
            'contact': {
                'id': contact.id,
                'name': getattr(contact, 'full_name', None),
                'phone': getattr(contact, 'phone_number', None),
                'whatsapp': getattr(contact, 'whatsapp_number', None),
                'email': email
            },
            'links': links,
            'template_used': int(template_id) if (template_id and template_id.isdigit()) else None
        })


class MessageTemplateViewSet(viewsets.ModelViewSet):
    queryset = MessageTemplate.objects.all().order_by('template_type', 'name')
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'message', 'subject']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def personalize(self, request, pk=None):
        """Get personalized message for a specific contact"""
        template = self.get_object()
        contact_id = request.data.get('contact_id')
        
        if not contact_id:
            return Response({'error': 'contact_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            contact = Contact.objects.get(id=contact_id)
            
            # Create a temporary activity to use the personalization method
            temp_activity = OutboundActivity(contact=contact, template_used=template)
            personalized_message = temp_activity.get_personalized_message(template)
            
            return Response({
                'personalized_message': personalized_message,
                'subject': template.subject,
                'template_type': template.template_type
            })
        except Contact.DoesNotExist:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None, format=None):
        """Get all activities for this campaign"""
        campaign = self.get_object()
        activities = OutboundActivity.objects.select_related(
            'contact', 'created_by'
        ).filter(campaign=campaign).order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(activities, request)
        if page is not None:
            serializer = OutboundActivitySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = OutboundActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None, format=None):
        """Get campaign statistics"""
        campaign = self.get_object()
        activities = campaign.outbound_activities.all()
        
        stats = {
            'total_activities': activities.count(),
            'unique_contacts': activities.values('contact').distinct().count(),
            'methods_breakdown': activities.values('method').annotate(count=Count('id')),
            'outcomes_breakdown': activities.exclude(outcome='').values('outcome').annotate(count=Count('id')),
            'avg_duration': activities.exclude(duration_minutes__isnull=True).aggregate(
                avg=Avg('duration_minutes')
            )['avg'] or 0,
            'conversion_rate': 0  # Can be calculated based on leads created
        }
        
        return Response(stats)


class OutboundAnalyticsOverview(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, format=None):
        now = timezone.now()
        
        # Use passed date parameters or default to last 30 days for consistency with dashboard
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')
        
        if from_date_str and to_date_str:
            try:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            except ValueError:
                # Fallback to last 30 days if date parsing fails
                to_date = now.date()
                from_date = to_date - timedelta(days=30)
        else:
            # Default to last 30 days to match dashboard behavior
            to_date = now.date()
            from_date = to_date - timedelta(days=30)

        # Calculate periods based on the date range (not hardcoded)
        start_of_week = to_date - timedelta(days=7)  # Last 7 days from end date
        start_of_month = from_date  # Use the from_date as start of month period

        # Get employee filter
        employee_id = request.GET.get('employee')

        # Base queryset
        base_activities = OutboundActivity.objects.all()

        # Normalize employee_id to int if provided
        selected_emp_id = None
        if employee_id:
            try:
                selected_emp_id = int(employee_id)
            except (TypeError, ValueError):
                selected_emp_id = None

        # Apply filtering logic
        if selected_emp_id is not None:
            # When an employee is selected, always filter to that employee
            base_activities = base_activities.filter(created_by__id=selected_emp_id)
        elif not request.user.is_superuser:
            # Non-superusers only see their own data
            base_activities = base_activities.filter(created_by=request.user)

        # Basic stats
        total_contacts = Contact.objects.count()
        contacted_today = (
            base_activities
            .filter(created_at__date__gte=to_date, created_at__date__lte=to_date)  # Today only
            .values('contact_id')
            .distinct()
            .count()
        )
        
        not_contacted = Contact.objects.filter(
            Q(last_contacted__isnull=True) | Q(outbound_status='NOT_CONTACTED')
        ).count()
        
        # Follow-ups due
        follow_ups_due = base_activities.filter(
            follow_up_reminder__lte=now,
            follow_up_reminder__isnull=False
        ).count()
        
        activities_today = base_activities.filter(created_at__date__gte=to_date, created_at__date__lte=to_date).count()

        # Activity breakdown by method for the selected date range
        method_stats = (
            base_activities
            .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
            .values('method')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Outcome breakdown (for the selected period)
        outcome_stats = (
            base_activities
            .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
            .exclude(outcome='')
            .values('outcome')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Conversion rate: contacts with leads vs contacts with activities
        contacts_with_activity = (
            base_activities.values('contact_id').distinct().count()
        )
        
        try:
            contacts_with_leads = (
                Lead.objects.filter(contact__isnull=False)
                .values('contact_id')
                .distinct()
                .count()
            )
            conversion_rate = round((contacts_with_leads / contacts_with_activity) * 100, 1) if contacts_with_activity else 0.0
        except:
            conversion_rate = 0.0

        # Salesperson leaderboard (for the selected period)
        leaderboard = (
            base_activities
            .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
            .values('created_by__username', 'created_by__first_name', 'created_by__last_name')
            .annotate(
                total_activities=Count('id'),
                unique_contacts=Count('contact_id', distinct=True),
                calls=Count(Case(When(method='PHONE', then=1), output_field=IntegerField())),
                whatsapp=Count(Case(When(method='WHATSAPP', then=1), output_field=IntegerField())),
                emails=Count(Case(When(method='EMAIL', then=1), output_field=IntegerField()))
            )
            .order_by('-total_activities')[:10]
        )
        
        leaderboard_data = []
        for row in leaderboard:
            full_name = f"{row['created_by__first_name'] or ''} {row['created_by__last_name'] or ''}".strip()
            leaderboard_data.append({
                'username': row['created_by__username'] or 'Unknown',
                'full_name': full_name or row['created_by__username'] or 'Unknown',
                'total_activities': row['total_activities'],
                'unique_contacts': row['unique_contacts'],
                'calls': row['calls'],
                'whatsapp': row['whatsapp'],
                'emails': row['emails']
            })

        data = {
            'contact_stats': ContactStatsSerializer({
                'total_contacts': total_contacts,
                'contacted_today': contacted_today,
                'not_contacted': not_contacted,
                'follow_ups_due': follow_ups_due,
                'activities_today': activities_today
            }).data,
            'method_breakdown': list(method_stats),
            'outcome_breakdown': list(outcome_stats),
            'leaderboard': leaderboard_data,
            'conversion_rate': conversion_rate
        }

        return Response(data)


# Additional API endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_contact_communication_links(request, contact_id, format=None):
    """Get communication links (tel, WhatsApp, email) for a contact"""
    try:
        contact = Contact.objects.get(id=contact_id)
        
        links = {}
        
        # Phone link
        if contact.phone_number:
            links['phone'] = f"tel:{contact.phone_number}"
        
        # WhatsApp link
        if contact.whatsapp_number:
            # Default message can be customized
            default_message = f"Hi {contact.full_name}, this is regarding your inquiry with us."
            links['whatsapp'] = f"https://wa.me/{contact.whatsapp_number.replace('+', '').replace(' ', '')}?text={default_message}"
        
        # Email link using contact's email if available
        contact_email = getattr(contact, 'email', None)
        if contact_email:
            subject = f"Follow up - {contact.full_name}"
            links['email'] = f"mailto:{contact_email}?subject={subject}"
        
        return Response({
            'contact': {
                'id': contact.id,
                'name': contact.full_name,
                'phone': contact.phone_number,
                'whatsapp': contact.whatsapp_number,
                'email': contact_email
            },
            'links': links
        })
    
    except Contact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
