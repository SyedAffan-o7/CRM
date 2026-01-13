from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.products_home, name='products-home'),
    path('categories/', views.category_list, name='category-list'),
    path('subcategories/', views.subcategory_list, name='subcategory-list'),
    path('import-csv/', views.import_categories_csv, name='products-import-csv'),
    path('download-example-csv/', views.download_example_csv, name='download-example-csv'),
    path('all/', views.product_list, name='product-list'),
]
