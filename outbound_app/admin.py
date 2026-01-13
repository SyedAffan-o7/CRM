from django.contrib import admin
from .models import Campaign, OutboundActivity


class OutboundActivityInline(admin.TabularInline):
    model = OutboundActivity
    extra = 1  # how many empty rows to show for quick add
    fields = ("contact", "lead", "method", "summary", "next_step", "next_step_date", "created_by", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("contact", "lead", "created_by")
    show_change_link = True


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("name", "description")
    actions = ["make_active", "make_inactive"]
    inlines = [OutboundActivityInline]

    @admin.action(description="Mark selected campaigns as active")
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Mark selected campaigns as inactive")
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(OutboundActivity)
class OutboundActivityAdmin(admin.ModelAdmin):
    list_display = ("contact", "lead", "campaign", "method", "created_by", "created_at", "next_step", "next_step_date")
    list_filter = ("method", "next_step", "created_at", "campaign")
    search_fields = ("summary", "contact__full_name", "campaign__name")
    autocomplete_fields = ("campaign", "contact", "lead", "created_by")
    date_hierarchy = "created_at"
