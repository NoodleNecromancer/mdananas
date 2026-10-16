from django.urls import include, path


urlpatterns = [path("export/", include("export_service.urls"))]
