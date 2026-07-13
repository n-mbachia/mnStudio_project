# ./storefront/views.py

from django.views.generic import ListView, DetailView, CreateView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django import forms as django_forms
from django.db.models import Q
from .models import Product, AuctionLot, ProductCategory, AuctionStatus, Waitlist, AuctionBid, BudgetRange
from crm.models import ClientProfile


class HomeView(TemplateView):
    template_name = "storefront/home.html"

    def get_context_data(self, **kwargs):
        cxt = super().get_context_data(**kwargs)

        # 1. Featured products for The Registry (3 items to fill the 3-col grid)
        featured_products = (
            Product.objects
            .filter(is_active=True, is_featured=True)
            .prefetch_related("media")[:3]
        )

        # 2. Derive hero from featured set — prefer one with media
        hero_product = None
        for product in featured_products:
            if product.media.exists():
                hero_product = product
                break

        # Fallback: first featured product even if it has no media
        if hero_product is None:
            hero_product = featured_products.first()

        cxt["featured"] = featured_products
        cxt["hero_product"] = hero_product
        cxt["hero_media"] = hero_product.media.first() if hero_product else None

        # 3. Active auctions (3 items to fill the 3-col grid)
        cxt["active_auctions"] = (
            AuctionLot.objects
            .filter(status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED])
            .select_related("product")
            .prefetch_related("product__media")[:3]
        )

        return cxt


class ProductListView(ListView):
    model = Product
    template_name = "storefront/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).prefetch_related("media")
        cat = self.request.GET.get("cat", "")
        if cat:
            qs = qs.filter(category=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        ctx["categories"] = ProductCategory.choices
        ctx["featured"] = (
            Product.objects
            .filter(is_featured=True, is_active=True)
            .prefetch_related("media")[:3]
        )
        ctx["active_auctions"] = (
            AuctionLot.objects
            .filter(status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED])
            .select_related("product")
            .prefetch_related("product__media")[:6]
        )
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "storefront/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["media_items"] = self.object.media.all()
        
        ctx["has_architectural_specs"] = bool(
            self.object.architectural_drawing_url or 
            (self.object.width_cm and self.object.height_cm and self.object.depth_cm)
        )
        return ctx


class AuctionListView(ListView):
    model = AuctionLot
    template_name = "storefront/auction_list.html"
    context_object_name = "lots"

    def get_queryset(self):
        return AuctionLot.objects.filter(
            status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
        ).select_related("product").order_by("end_time")


class AuctionDetailView(DetailView):
    model = AuctionLot
    template_name = "storefront/auction_detail.html"
    context_object_name = "lot"

    def get_queryset(self):
        return AuctionLot.objects.select_related("product")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bids"] = self.object.bids.select_related("bidder").order_by("-amount")[:10]
        
        ctx["has_architectural_specs"] = bool(
            self.object.display_blueprint_url or 
            (self.object.product and self.object.product.width_cm)
        )
        return ctx


class PlaceBidView(View):
    def post(self, request, pk):
        lot = get_object_or_404(AuctionLot, pk=pk)
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        name  = request.POST.get("name", "Anonymous")
        
        if not phone:
            messages.error(request, "A valid phone contact number is required to place a bid.")
            return redirect("storefront:auction_detail", pk=pk)

        try:
            amount = __import__("decimal").Decimal(request.POST.get("amount", "0"))
        except Exception:
            messages.error(request, "Invalid bid amount.")
            return redirect("storefront:auction_detail", pk=pk)

        # Unified lookup: search for matching phone OR matching email
        client = ClientProfile.objects.filter(Q(phone=phone) | Q(email=email)).first()

        if client:
            updated = False
            if name and client.name != name:
                client.name = name
                updated = True
            if phone and client.phone != phone:
                client.phone = phone
                updated = True
            if email and client.email != email:
                client.email = email
                updated = True
            if updated:
                client.save()
        else:
            client = ClientProfile.objects.create(
                name=name,
                email=email,
                phone=phone
            )

        success, msg = lot.place_bid(bidder=client, amount=amount, phone=phone)
        
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
            
        return redirect("storefront:auction_detail", pk=pk)


class WaitlistJoinView(View):
    template_name = "storefront/waitlist.html"

    def get(self, request):
        return render(request, self.template_name, {"budget_ranges": BudgetRange.choices})

    def post(self, request):
        data = request.POST
        files = request.FILES
        
        email = data.get("email", "").strip()
        
        exists = Waitlist.objects.filter(email=email).exists()
        
        if exists:
            messages.info(request, "You're already on our waitlist. We'll reach out soon.")
            return redirect("storefront:waitlist_success")
            
        try:
            waitlist_entry = Waitlist(
                email=email,
                name=data.get("name", ""),
                phone=data.get("phone", ""),
                piece_of_interest=data.get("piece_of_interest", ""),
                budget_range=data.get("budget_range", ""),
                timeline_months=int(data.get("timeline_months", 3)),
                reference_image=files.get("reference_image")
            )
            waitlist_entry.save()
            
            messages.success(request, "You've been added to our waiting list. We'll be in touch!")
        except Exception as e:
            messages.error(request, f"Could not save your details. Error: {e}")
            
        return redirect("storefront:waitlist_success")


class WaitlistSuccessView(TemplateView):
    template_name = "storefront/waitlist_success.html"
