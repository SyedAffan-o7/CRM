from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from customers_app.models import Contact
from outbound_app.models import OutboundActivity, MessageTemplate, Campaign


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class MessageTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'message', 
            'is_active', 'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']


class CampaignSerializer(serializers.ModelSerializer):
    activity_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date', 
            'is_active', 'created_at', 'activity_count'
        ]
    
    def get_activity_count(self, obj):
        return obj.outbound_activities.count()


class ContactSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    total_activities = serializers.SerializerMethodField()
    days_since_last_contact = serializers.SerializerMethodField()
    enquiries_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'full_name', 'phone_number', 'whatsapp_number',
            'company_name', 'outbound_status', 'last_contacted',
            'role_position', 'address', 'notes',
            'last_activity', 'total_activities', 'days_since_last_contact',
            'enquiries_count'
        ]

    def get_company_name(self, obj):
        try:
            return getattr(obj.company, 'company_name', None)
        except Exception:
            return None
    
    def get_last_activity(self, obj):
        try:
            last = obj.outbound_activities.first()
            if last:
                return {
                    'id': last.id,
                    'method': last.method,
                    'outcome': last.outcome,
                    'summary': last.summary[:100] + '...' if len(last.summary) > 100 else last.summary,
                    'created_at': last.created_at,
                    'created_by': last.created_by.username if last.created_by else None
                }
        except Exception:
            pass
        return None
    
    def get_total_activities(self, obj):
        return obj.outbound_activities.count()
    
    def get_days_since_last_contact(self, obj):
        if obj.last_contacted:
            return (timezone.now().date() - obj.last_contacted.date()).days
        return None
    
    def get_enquiries_count(self, obj):
        try:
            return obj.leads.count()
        except Exception:
            return 0


class OutboundActivitySerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    customer_whatsapp = serializers.SerializerMethodField()
    salesperson = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)
    next_step_display = serializers.CharField(source='get_next_step_display', read_only=True)
    is_follow_up_due = serializers.BooleanField(read_only=True)
    days_since_contact = serializers.IntegerField(read_only=True)
    personalized_message = serializers.SerializerMethodField()

    class Meta:
        model = OutboundActivity
        fields = [
            'id', 'contact', 'lead', 'campaign', 'method', 'outcome',
            'summary', 'detailed_notes', 'next_step', 'next_step_date',
            'follow_up_reminder', 'duration_minutes', 'template_used',
            'created_by', 'created_at', 'updated_at', 'metadata',
            # Computed fields
            'customer', 'customer_phone', 'customer_whatsapp', 'salesperson',
            'campaign_name', 'template_name', 'method_display', 'outcome_display',
            'next_step_display', 'is_follow_up_due', 'days_since_contact',
            'personalized_message'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_customer(self, obj):
        return getattr(obj.contact, 'full_name', None)
    
    def get_customer_phone(self, obj):
        return getattr(obj.contact, 'phone_number', None)
    
    def get_customer_whatsapp(self, obj):
        return getattr(obj.contact, 'whatsapp_number', None)

    def get_salesperson(self, obj):
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'username': obj.created_by.username,
                'full_name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
            }
        return None
    
    def get_campaign_name(self, obj):
        return getattr(obj.campaign, 'name', None)
    
    def get_template_name(self, obj):
        return getattr(obj.template_used, 'name', None)
    
    def get_personalized_message(self, obj):
        if obj.template_used:
            return obj.get_personalized_message(obj.template_used)
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)
    
    def validate(self, data):
        # Validate follow-up reminder is in the future
        if data.get('follow_up_reminder') and data['follow_up_reminder'] <= timezone.now():
            raise serializers.ValidationError({
                'follow_up_reminder': 'Follow-up reminder must be in the future.'
            })
        
        # Validate next step date is in the future if provided
        if data.get('next_step_date') and data['next_step_date'] <= timezone.now():
            raise serializers.ValidationError({
                'next_step_date': 'Next step date should be in the future.'
            })
        
        return data


class QuickActivitySerializer(serializers.Serializer):
    """Simplified serializer for quick activity logging"""
    contact_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=OutboundActivity.METHOD_CHOICES)
    outcome = serializers.ChoiceField(choices=OutboundActivity.OUTCOME_CHOICES, required=False)
    summary = serializers.CharField(max_length=500, required=False)
    next_step = serializers.ChoiceField(choices=OutboundActivity.NEXT_STEP_CHOICES, required=False)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=480, required=False)
    template_id = serializers.IntegerField(required=False)
    
    def validate_contact_id(self, value):
        try:
            Contact.objects.get(id=value)
        except Contact.DoesNotExist:
            raise serializers.ValidationError("Contact not found.")
        return value
    
    def validate_template_id(self, value):
        if value:
            try:
                MessageTemplate.objects.get(id=value, is_active=True)
            except MessageTemplate.DoesNotExist:
                raise serializers.ValidationError("Template not found or inactive.")
        return value


class EnquiryCreateSerializer(serializers.Serializer):
    contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), required=True)
    contact_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        default='medium'
    )
    
    def create(self, validated_data):
        """
        Create a minimal Lead (enquiry) from a Contact.
        """
        from leads_app.models import Lead
        
        contact = validated_data['contact']
        request = self.context.get('request')
        
        # Build lead data
        lead_data = {
            'contact': contact,
            'contact_name': validated_data.get('contact_name') or contact.full_name,
            'phone_number': validated_data.get('phone_number') or contact.phone_number,
            'company_name': validated_data.get('company_name') or getattr(getattr(contact, 'company', None), 'company_name', ''),
            'notes': validated_data.get('notes', ''),
            'priority': validated_data.get('priority', 'medium'),
            'enquiry_stage': 'enquiry_received',
            'lead_status': 'not_fulfilled'
        }
        
        # Set created_by if available
        if request and request.user.is_authenticated:
            lead_data['created_by'] = request.user
            lead_data['assigned_sales_person'] = request.user
        
        lead = Lead(**lead_data)
        try:
            lead.save()
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create enquiry: {str(e)}")
        
        return lead


class ContactStatsSerializer(serializers.Serializer):
    """Serializer for contact statistics"""
    total_contacts = serializers.IntegerField()
    contacted_today = serializers.IntegerField()
    not_contacted = serializers.IntegerField()
    follow_ups_due = serializers.IntegerField()
    activities_today = serializers.IntegerField()


class SalespersonStatsSerializer(serializers.Serializer):
    """Serializer for salesperson performance stats"""
    salesperson_id = serializers.IntegerField()
    salesperson_name = serializers.CharField()
    total_activities = serializers.IntegerField()
    calls_made = serializers.IntegerField()
    whatsapp_sent = serializers.IntegerField()
    emails_sent = serializers.IntegerField()
    meetings_held = serializers.IntegerField()
    enquiries_created = serializers.IntegerField()
    avg_response_rate = serializers.FloatField()
