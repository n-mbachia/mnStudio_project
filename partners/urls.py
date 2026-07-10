from django.urls import path
from . import views

app_name = "partners"

urlpatterns = [
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/new/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/", views.SupplierDetailView.as_view(), name="supplier_detail"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("pos/", views.PurchaseOrderListView.as_view(), name="po_list"),
    path("pos/new/", views.PurchaseOrderCreateView.as_view(), name="po_create"),
    path("pos/<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="po_detail"),
    path("pos/<int:pk>/confirm/", views.POConfirmView.as_view(), name="po_confirm"),
    path("pos/<int:pk>/receive/", views.POReceiveView.as_view(), name="po_receive"),
    path("artisans/", views.ArtisanListView.as_view(), name="artisan_list"),
    path("artisans/new/", views.ArtisanCreateView.as_view(), name="artisan_create"),
    path("artisans/<int:pk>/", views.ArtisanDetailView.as_view(), name="artisan_detail"),
]
