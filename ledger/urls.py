from django.urls import path
from . import views

app_name = "ledger"

urlpatterns = [
    path("quotes/", views.QuoteListView.as_view(), name="quote_list"),
    path("quotes/new/", views.QuoteCreateView.as_view(), name="quote_create"),
    path("quotes/<int:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
    path("quotes/<int:pk>/send/", views.QuoteSendView.as_view(), name="quote_send"),
    path("quotes/<int:pk>/approve/", views.QuoteApproveView.as_view(), name="quote_approve"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/print/", views.InvoicePrintView.as_view(), name="invoice_print"),
    path("jobs/<int:job_pk>/invoice/create/", views.InvoiceCreateView.as_view(), name="invoice_create"),
    path("invoices/<int:pk>/payment/add/", views.PaymentCreateView.as_view(), name="payment_add"),
    path("compliance/", views.ComplianceDashboardView.as_view(), name="compliance_dashboard"),
    path("compliance/<int:year>/<int:month>/", views.ComplianceMonthView.as_view(), name="compliance_month"),
    path("compliance/<int:year>/<int:month>/save/", views.ComplianceSaveView.as_view(), name="compliance_save"),
    path("mpesa/callback/", views.MpesaCallbackView.as_view(), name="mpesa_callback"),
]
