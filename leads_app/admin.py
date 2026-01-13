from django.contrib import admin
from .models import Lead, Product

# Note: Lead admin is registered centrally in `crm_app/admin.py` to avoid
# duplicate registrations across apps.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_date']
    list_filter = ['category', 'is_active', 'created_date']
    search_fields = ['name', 'description', 'category']
    ordering = ['name']
    list_editable = ['is_active']
