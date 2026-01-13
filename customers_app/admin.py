from django.contrib import admin
from django.apps import apps
import importlib
from outbound_app.models import OutboundActivity

# Ensure central admin registrations are loaded first (crm_app.admin registers Contact)
try:
    importlib.import_module('crm_app.admin')
except Exception:
    # If import fails, continue; we'll still try to augment if possible
    pass

Contact = apps.get_model('customers_app', 'Contact')


class OutboundActivityInline(admin.TabularInline):
    model = OutboundActivity
    extra = 1
    fields = ("campaign", "method", "summary", "next_step", "next_step_date", "created_by", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("campaign", "created_by")
    show_change_link = True


# Append inline to existing Contact admin if it exists
existing_admin = admin.site._registry.get(Contact)
if existing_admin:
    inlines = list(getattr(existing_admin, 'inlines', []))
    if OutboundActivityInline not in inlines:
        inlines.append(OutboundActivityInline)
        existing_admin.inlines = inlines
# Do NOT register Contact here to avoid AlreadyRegistered errors
