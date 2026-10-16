from django.urls import path
from .views import by_views, kg_views, uz_views

urlpatterns = [
    path('', kg_views.main_page, name='main_page'),
    path('kg/', kg_views.kg_page, name='kg_page'),
    path('kg/sales-file-processing-progress/', kg_views.get_upload_progress, name='get-upload-progress'),
    path('kg/save-stores/', kg_views.kg_page_save_stores, name='kg_page_save_stores'),
    path('kg/save-competitors-sku/', kg_views.kg_page_save_competitors_sku, name='kg_page_save_competitors_sku'),
    path('uz/', uz_views.uz_page, name='uz_page'),
    path('uz/get-progress/', uz_views.get_progress, name='get_progress'),
    path('by/', by_views.by_page, name='by_page'),
]
