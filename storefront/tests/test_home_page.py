from django.test import TestCase
from django.urls import reverse

from storefront.models import Product, ProductMedia


class HomePageViewTests(TestCase):
    def test_root_home_page_renders_featured_product_image(self):
        product = Product.objects.create(
            name="Oak Dining Table",
            slug="oak-dining-table",
            description="A handcrafted oak dining table.",
            category="dining",
            primary_species="Oak",
            starting_price="120000.00",
            lead_time_days=45,
            is_featured=True,
            is_active=True,
        )
        ProductMedia.objects.create(
            product=product,
            media_type="IMAGE",
            media_url="https://example.com/oak.jpg",
            thumbnail_url="https://example.com/oak-thumb.jpg",
            is_primary=True,
            order=0,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "storefront/home.html")
        self.assertContains(response, product.name)
        self.assertContains(response, 'src="https://example.com/oak.jpg"')
        self.assertContains(response, "Request Commission")
