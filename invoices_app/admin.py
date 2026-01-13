from django.contrib import admin

from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'contact', 'issue_date', 'total_amount', 'status']
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'contact__full_name']
    inlines = [InvoiceItemInline]
