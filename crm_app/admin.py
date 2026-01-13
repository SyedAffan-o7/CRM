from django.contrib import admin
from leads_app.models import Lead, Reason
from customers_app.models import Contact
from accounts_app.models import Account
from deals_app.models import Deal
from activities_app.models import ActivityLog


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'primary_contact', 'phone_number', 'account_status', 'created_date']
    list_filter = ['account_status', 'industry_type', 'created_date']
    search_fields = ['company_name', 'primary_contact', 'phone_number']
    ordering = ['company_name']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'company', 'role_position', 'created_date']
    list_filter = ['company', 'created_date']
    search_fields = ['full_name', 'phone_number', 'company__company_name']
    ordering = ['full_name']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'phone_number', 'company_name', 'lead_status', 'priority', 'assigned_sales_person', 'created_date']
    list_filter = ['lead_status', 'priority', 'lead_source', 'assigned_sales_person', 'created_date', 'products_enquired']
    search_fields = ['contact_name', 'phone_number', 'company_name']
    ordering = ['-created_date']
    filter_horizontal = ['products_enquired']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['deal_name', 'contact', 'account', 'deal_value', 'deal_stage', 'probability_percent', 'sales_person_assigned', 'expected_close_date']
    list_filter = ['deal_stage', 'sales_person_assigned', 'expected_close_date', 'created_date']
    search_fields = ['deal_name', 'contact__full_name', 'account__company_name']
    ordering = ['-created_date']


@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_date']
    list_filter = ['is_active', 'created_date']
    search_fields = ['name', 'description']
    ordering = ['name']
    list_editable = ['is_active']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'subject', 'contact', 'lead', 'deal', 'user', 'activity_date']
    list_filter = ['activity_type', 'user', 'activity_date', 'created_date']
    search_fields = ['subject', 'description', 'contact__full_name', 'lead__contact_name']
    ordering = ['-activity_date']
