# --- ./storefront/urls.py

from django.urls import path
from . import views

app_name = "storefront"

urlpatterns = [
	path("", views.HomeView.as_view(), name="home"),
    path("shop/", views.ProductListView.as_view(), name="product_list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("auctions/", views.AuctionListView.as_view(), name="auction_list"),
    path("auctions/<int:pk>/", views.AuctionDetailView.as_view(), name="auction_detail"),
    path("auctions/<int:pk>/bid/", views.PlaceBidView.as_view(), name="place_bid"),
    path("waitlist/", views.WaitlistJoinView.as_view(), name="waitlist"),
    path("waitlist/success/", views.WaitlistSuccessView.as_view(), name="waitlist_success"),
]
