#	./storefront/views.py

from django.views.generic import ListView, DetailView, CreateView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django import forms as django_forms
from .models import Product, AuctionLot, AuctionStatus, Waitlist, AuctionBid, BudgetRange
from crm.models import ClientProfile


class ProductListView(ListView):
    model = Product
    template_name = "storefront/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        cat = self.request.GET.get("cat", "")
        if cat:
            qs = qs.filter(category=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .models import ProductCategory, AuctionLot, AuctionStatus
        
        ctx["categories"] = ProductCategory.choices
        
        # 1. Pull the 3 active featured items for the media-flashing registry rows (Optimized prefetch)
        featured_products = Product.objects.filter(is_featured=True, is_active=True).prefetch_related('media')
        ctx["featured"] = featured_products[:3]
        
        # 2. Isolate the very first item to serve your hero banner layout accurately
        hero_showcase = featured_products.first()
        ctx["hero_product"] = hero_showcase
        if hero_showcase:
            # Grabs the fallback property or the first item in the media pool safely
            ctx["hero_media"] = hero_showcase.media.first()

        # 3. Correctly fetch live auction logs matching your model properties
        # Optimized with select_related('product') to fetch spatial data and blueprint fields efficiently
        ctx["active_auctions"] = AuctionLot.objects.filter(
            status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
        ).select_related('product')[:3]
        
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "storefront/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Context is updated to handle robust media items instead of just raw static images
        ctx["media_items"] = self.object.media.all()
        
        # Robustness check: flag whether frontend layout switcher should present the blueprint tab
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
        # Prefetch parent product to natively grab dynamic structural specs down the wire
        return AuctionLot.objects.filter(
            status__in=[AuctionStatus.ACTIVE, AuctionStatus.EXTENDED]
        ).select_related("product").order_by("end_time")


class AuctionDetailView(DetailView):
    model = AuctionLot
    template_name = "storefront/auction_detail.html"
    context_object_name = "lot"

    def get_queryset(self):
        # Ensure fallback product data is always loaded instantly
        return AuctionLot.objects.select_related("product")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bids"] = self.object.bids.select_related("bidder").order_by("-amount")[:10]
        
        # Robustness check for auction pages: determine structural sizing availability
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

        # Unified lookup query: search for matching phone OR matching email
        from django.db.models import Q
        client = ClientProfile.objects.filter(Q(phone=phone) | Q(email=email)).first()

        if client:
            # Safely patch missing or updated details onto the found profile identity
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
            # Instantiate a clean record if no parts match existing accounts
            client = ClientProfile.objects.create(
                name=name,
                email=email,
                phone=phone
            )

        # Process ledger mechanics — passing the 'phone' variable here
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
        
        # Check if the email is already registered on the waitlist
        exists = Waitlist.objects.filter(email=email).exists()
        
        if exists:
            messages.info(request, "You're already on our waitlist. We'll reach out soon.")
            return redirect("storefront:waitlist_success")
            
        try:
            # Instantiate the object directly to trigger Cloudinary's file upload handler
            waitlist_entry = Waitlist(
                email=email,
                name=data.get("name", ""),
                phone=data.get("phone", ""),
                piece_of_interest=data.get("piece_of_interest", ""),
                budget_range=data.get("budget_range", ""),
                timeline_months=int(data.get("timeline_months", 3)),
                reference_image=files.get("reference_image") # Cloudinary safely streams this now
            )
            waitlist_entry.save() # Triggers storage pipeline
            
            messages.success(request, "You've been added to our waiting list. We'll be in touch!")
        except Exception as e:
            messages.error(request, f"Could not save your details. Error: {e}")
            
        return redirect("storefront:waitlist_success")


class WaitlistSuccessView(TemplateView):
    template_name = "storefront/waitlist_success.html"
