from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from crm.models import ClientProfile
from storefront.models import (
    AuctionBid,
    AuctionLot,
    AuctionStatus,
    BudgetRange,
    Product,
    ProductMedia,
    Waitlist,
)


class StorefrontPublicPageTests(TestCase):
    def setUp(self):
        self.featured_without_media = Product.objects.create(
            name="Apple Bench",
            slug="apple-bench",
            description="A compact accent bench.",
            category="living",
            primary_species="Mango",
            starting_price="80000.00",
            lead_time_days=21,
            is_featured=True,
            is_active=True,
        )
        self.featured_with_media = Product.objects.create(
            name="Walnut Table",
            slug="walnut-table",
            description="A handcrafted walnut dining table.",
            category="dining",
            primary_species="Walnut",
            architectural_drawing_url="https://example.com/walnut-blueprint.jpg",
            starting_price="120000.00",
            lead_time_days=45,
            is_featured=True,
            is_active=True,
        )
        ProductMedia.objects.create(
            product=self.featured_with_media,
            media_type="IMAGE",
            media_url="https://example.com/walnut.jpg",
            thumbnail_url="https://example.com/walnut-thumb.jpg",
            is_primary=True,
            order=0,
        )
        ProductMedia.objects.create(
            product=self.featured_with_media,
            media_type="VIDEO",
            media_url="https://example.com/walnut.mp4",
            thumbnail_url="https://example.com/walnut-thumb.jpg",
            is_primary=False,
            order=1,
        )
        self.inactive_product = Product.objects.create(
            name="Hidden Console",
            slug="hidden-console",
            description="Inactive catalog item.",
            category="office",
            primary_species="Teak",
            starting_price="150000.00",
            lead_time_days=30,
            is_featured=False,
            is_active=False,
        )

        self.active_lot = AuctionLot.objects.create(
            title="Walnut Table Auction",
            description="Live auction lot for the walnut table.",
            product=self.featured_with_media,
            starting_bid="110000.00",
            current_bid="130000.00",
            reserve_price="180000.00",
            status=AuctionStatus.ACTIVE,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
        )
        self.extended_lot = AuctionLot.objects.create(
            title="Apple Bench Auction",
            description="Extended auction lot with override image.",
            product=self.featured_without_media,
            image_url="https://example.com/apple-auction.jpg",
            starting_bid="50000.00",
            current_bid="65000.00",
            reserve_price="90000.00",
            status=AuctionStatus.EXTENDED,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(hours=4),
        )
        self.draft_lot = AuctionLot.objects.create(
            title="Hidden Draft Auction",
            description="Draft lot that should not appear publicly.",
            product=self.inactive_product,
            starting_bid="40000.00",
            current_bid="40000.00",
            reserve_price="50000.00",
            status=AuctionStatus.DRAFT,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
        )

    def test_home_page_uses_featured_product_with_media_for_hero(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/home.html")
        self.assertEqual(response.context["hero_product"], self.featured_with_media)
        self.assertEqual(response.context["hero_media"].media_url, "https://example.com/walnut.jpg")
        self.assertContains(response, 'src="https://example.com/walnut.jpg"')
        self.assertContains(response, self.featured_without_media.name)
        self.assertContains(response, "Request Commission")

    def test_product_list_filters_active_products_by_category(self):
        response = self.client.get(reverse("storefront:product_list"))
        filtered = self.client.get(f"{reverse('storefront:product_list')}?cat=dining")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/product_list.html")
        self.assertEqual(len(response.context["products"]), 2)
        self.assertContains(response, self.featured_with_media.name)
        self.assertContains(response, self.featured_without_media.name)
        self.assertNotContains(response, self.inactive_product.name)

        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.context["products"]), 1)
        self.assertContains(filtered, self.featured_with_media.name)
        self.assertNotContains(filtered, self.featured_without_media.name)

    def test_product_detail_renders_gallery_and_blueprint(self):
        response = self.client.get(reverse("storefront:product_detail", args=[self.featured_with_media.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/product_detail.html")
        self.assertTrue(response.context["has_architectural_specs"])
        self.assertEqual(len(response.context["media_items"]), 2)
        self.assertContains(response, "https://example.com/walnut.jpg")
        self.assertContains(response, "https://example.com/walnut.mp4")
        self.assertContains(response, "https://example.com/walnut-blueprint.jpg")

    def test_auction_list_renders_live_lots_and_skips_drafts(self):
        response = self.client.get(reverse("storefront:auction_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/auction_list.html")
        self.assertEqual(len(response.context["lots"]), 2)
        self.assertContains(response, self.active_lot.title)
        self.assertContains(response, self.extended_lot.title)
        self.assertContains(response, 'src="https://example.com/walnut.jpg"')
        self.assertContains(response, 'src="https://example.com/apple-auction.jpg"')
        self.assertNotContains(response, self.draft_lot.title)

    def test_auction_detail_renders_fallback_media_and_blueprint(self):
        response = self.client.get(reverse("storefront:auction_detail", args=[self.active_lot.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/auction_detail.html")
        self.assertTrue(response.context["has_architectural_specs"])
        self.assertEqual(len(response.context["bids"]), 0)
        self.assertContains(response, self.active_lot.title)
        self.assertContains(response, 'src="https://example.com/walnut.jpg"')
        self.assertContains(response, "https://example.com/walnut-blueprint.jpg")
        self.assertContains(response, "View Full Design Registry")


class StorefrontActionTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Teak Cabinet",
            slug="teak-cabinet",
            description="A solid teak cabinet.",
            category="storage",
            primary_species="Teak",
            starting_price="90000.00",
            lead_time_days=35,
            is_featured=True,
            is_active=True,
        )
        ProductMedia.objects.create(
            product=self.product,
            media_type="IMAGE",
            media_url="https://example.com/teak.jpg",
            thumbnail_url="https://example.com/teak-thumb.jpg",
            is_primary=True,
            order=0,
        )
        self.lot = AuctionLot.objects.create(
            title="Teak Cabinet Auction",
            description="A live auction lot for a teak cabinet.",
            product=self.product,
            starting_bid="85000.00",
            current_bid="95000.00",
            reserve_price="120000.00",
            status=AuctionStatus.ACTIVE,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() + timedelta(hours=2),
        )

    def test_place_bid_updates_client_and_creates_bid(self):
        client = ClientProfile.objects.create(
            name="Old Name",
            email="old@example.com",
            phone="0711000000",
        )

        response = self.client.post(
            reverse("storefront:place_bid", args=[self.lot.pk]),
            {
                "name": "New Name",
                "email": "buyer@example.com",
                "phone": "0711000000",
                "amount": "99000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        client.refresh_from_db()
        self.assertEqual(self.lot.current_bid, Decimal("99000"))
        self.assertEqual(AuctionBid.objects.count(), 1)
        bid = AuctionBid.objects.first()
        self.assertEqual(bid.bidder, client)
        self.assertEqual(client.name, "New Name")
        self.assertEqual(client.email, "buyer@example.com")

    def test_place_bid_rejects_missing_phone(self):
        response = self.client.post(
            reverse("storefront:place_bid", args=[self.lot.pk]),
            {
                "name": "Anonymous Buyer",
                "email": "anon@example.com",
                "amount": "99000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AuctionBid.objects.count(), 0)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.current_bid, Decimal("95000.00"))

    def test_waitlist_get_and_post_creates_entry_once(self):
        get_response = self.client.get(reverse("storefront:waitlist"))

        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, "storefront/waitlist.html")
        self.assertEqual(get_response.context["budget_ranges"], BudgetRange.choices)
        self.assertContains(get_response, "Commission Slot")

        payload = {
            "name": "Prospective Client",
            "email": "client@example.com",
            "phone": "+254700000001",
            "piece_of_interest": "Custom dining table",
            "budget_range": BudgetRange.K50_150,
            "timeline_months": "3",
        }

        post_response = self.client.post(reverse("storefront:waitlist"), payload)
        duplicate_response = self.client.post(reverse("storefront:waitlist"), payload)

        self.assertRedirects(post_response, reverse("storefront:waitlist_success"))
        self.assertRedirects(duplicate_response, reverse("storefront:waitlist_success"))
        self.assertEqual(Waitlist.objects.count(), 1)
        entry = Waitlist.objects.get(email="client@example.com")
        self.assertEqual(entry.name, "Prospective Client")
        self.assertEqual(entry.piece_of_interest, "Custom dining table")
        self.assertEqual(entry.budget_range, BudgetRange.K50_150)
