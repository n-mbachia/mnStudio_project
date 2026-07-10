from django.urls import path
from . import views

app_name = "certificates"

urlpatterns = [
    path("<uuid:uuid>/", views.CertificatePublicView.as_view(), name="detail"),
    path("admin/create/<int:job_pk>/", views.CertificateCreateView.as_view(), name="create"),
    path("admin/<int:pk>/print/", views.CertificatePrintView.as_view(), name="print"),
]
