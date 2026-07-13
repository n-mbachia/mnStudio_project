from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from storefront.models import AuctionLot, AuctionStatus, Product, ProductMedia


class AuctionMediaRenderingTests(TestCase):
    def test_auction_templates_render_product_media_fallback(self):
        product = Product.objects.create(
            name="Walnut Sideboard",
            slug="walnut-sideboard",
            description="A handcrafted walnut sideboard.",
            category="living",
            primary_species="Walnut",
            starting_price="180000.00",
            lead_time_days=60,
            is_featured=False,
            is_active=True,
        )
        ProductMedia.objects.create(
            product=product,
            media_type="IMAGE",
            media_url="https://example.com/walnut.jpg",
            thumbnail_url="https://example.com/walnut-thumb.jpg",
            is_primary=True,
            order=0,
        )
        lot = AuctionLot.objects.create(
            title="Walnut Sideboard Auction",
            description="Live auction lot for a walnut sideboard.",
            product=product,
            starting_bid="150000.00",
            current_bid="160000.00",
            reserve_price="200000.00",
            status=AuctionStatus.ACTIVE,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
        )

        list_response = self.client.get(reverse("storefront:auction_list"))
        detail_response = self.client.get(reverse("storefront:auction_detail", args=[lot.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'src="https://example.com/walnut.jpg"')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'src="https://example.com/walnut.jpg"')
