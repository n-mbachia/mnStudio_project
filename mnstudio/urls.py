"""MN Studio root URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.HomeView.as_view(), name="home"),
    path("dashboard/", core_views.DashboardView.as_view(), name="dashboard"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("crm/", include("crm.urls", namespace="crm")),
    path("production/", include("production.urls", namespace="production")),
    path("partners/", include("partners.urls", namespace="partners")),
    path("ledger/", include("ledger.urls", namespace="ledger")),
    path("shop/", include("storefront.urls", namespace="storefront")),
    path("certificates/", include("certificates.urls", namespace="certificates")),
]

# Explicitly tell Django how to serve files locally during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
admin.site.site_header = "MN Studio Administration"
admin.site.site_title = "MN Studio"
admin.site.index_title = "Business Management"
