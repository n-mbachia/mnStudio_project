"""
Management command: seed_demo
Creates a minimal demo dataset so you can explore the platform immediately.

Usage:
    python manage.py seed_demo
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = "Seed the database with demo data for development."

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding MN Studio demo data…\n")

        # Superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@mnstudio.co.ke", "mn2025admin")
            self.stdout.write("  ✓ Admin user created (admin / mn2025admin)")

        # Supplier profiles
        from partners.models import SupplierProfile, MaterialType, SupplierLocation
        mahogany_sup, _ = SupplierProfile.objects.get_or_create(
            name="Kariuki Timber — Gikomba",
            defaults={
                "phone": "+254712000001", "material_type": MaterialType.TIMBER,
                "location": SupplierLocation.GIKOMBA, "current_rate": Decimal("400.00"),
            }
        )
        mvule_sup, _ = SupplierProfile.objects.get_or_create(
            name="Mwangi Hardwoods — Ngara",
            defaults={
                "phone": "+254712000002", "material_type": MaterialType.TIMBER,
                "location": SupplierLocation.NGARA, "current_rate": Decimal("450.00"),
            }
        )
        hw_sup, _ = SupplierProfile.objects.get_or_create(
            name="BuildRight Hardware — Ngong Rd",
            defaults={
                "phone": "+254712000003", "material_type": MaterialType.HARDWARE,
                "location": SupplierLocation.NGONG, "current_rate": Decimal("250.00"),
            }
        )
        self.stdout.write("  ✓ Suppliers created")

        # Artisans
        from partners.models import ArtisanProfile, ArtisanSpecialty
        artisan1, _ = ArtisanProfile.objects.get_or_create(
            name="Joseph Otieno",
            defaults={"phone": "+254712001001", "specialty": ArtisanSpecialty.CARPENTRY,
                      "base_piece_rate": Decimal("3500.00"), "is_active": True,
                      "joined_at": datetime.date(2022, 3, 15)}
        )
        artisan2, _ = ArtisanProfile.objects.get_or_create(
            name="Mary Wanjiku",
            defaults={"phone": "+254712001002", "specialty": ArtisanSpecialty.FINISHING,
                      "base_piece_rate": Decimal("2000.00"), "is_active": True,
                      "joined_at": datetime.date(2023, 6, 1)}
        )
        self.stdout.write("  ✓ Artisans created")

        # Clients
        from crm.models import ClientProfile, AcquisitionSource
        client1, _ = ClientProfile.objects.get_or_create(
            email="amara.ndungu@example.co.ke",
            defaults={
                "name": "Amara Ndungu", "phone": "+254722100001",
                "county": "Nairobi", "acquisition_source": AcquisitionSource.REFERRAL,
                "is_vip": True, "preference_notes": "Prefers mvule. Minimalist aesthetic. No stain.",
            }
        )
        client2, _ = ClientProfile.objects.get_or_create(
            email="kariuki.mutua@example.co.ke",
            defaults={
                "name": "Kariuki Mutua", "phone": "+254733200002",
                "county": "Kiambu", "acquisition_source": AcquisitionSource.INSTAGRAM,
            }
        )
        self.stdout.write("  ✓ Clients created")

        # Products
        from storefront.models import Product, ProductCategory
        Product.objects.get_or_create(
            slug="heritage-dining-set-mvule",
            defaults={
                "name": "Heritage Dining Set — Mvule",
                "description": "A six-seater dining table and chairs milled from solid African Teak. "
                               "Jointed with traditional mortise-and-tenon. Finished in pure teak oil.",
                "category": ProductCategory.DINING, "primary_species": "Mvule",
                "starting_price": Decimal("185000.00"), "lead_time_days": 45, "is_featured": True,
            }
        )
        Product.objects.get_or_create(
            slug="study-desk-mahogany",
            defaults={
                "name": "Executive Study Desk — Mahogany",
                "description": "A single-pedestal writing desk with cable management and solid brass handles.",
                "category": ProductCategory.OFFICE, "primary_species": "Mahogany",
                "starting_price": Decimal("78000.00"), "lead_time_days": 30, "is_featured": True,
            }
        )
        Product.objects.get_or_create(
            slug="floating-tv-unit-pine",
            defaults={
                "name": "Floating TV Unit — Pine",
                "description": "Wall-mounted media console with hidden cable tray. "
                               "Available in raw pine or painted finishes.",
                "category": ProductCategory.LIVING, "primary_species": "Pine",
                "starting_price": Decimal("45000.00"), "lead_time_days": 21, "is_featured": False,
            }
        )
        self.stdout.write("  ✓ Products created")

        # Full Job lifecycle demo
        from ledger.models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment, PaymentMethod, PaymentStatus
        from core.models import Job, JobStatus
        from production.models import JobCard, TimberEntry, HardwareEntry, LaborEntry, TimberSpecies, BOMState
        from crm.models import DesignBrief, DesignBriefStatus

        # Quote
        admin_user = User.objects.get(username="admin")
        quote, created = Quote.objects.get_or_create(
            quote_id="QT-06-2025-0001",
            defaults={"client": client1, "discount": Decimal("0"), "deposit_amount": Decimal("92500"),
                      "notes": "50% deposit required. Lead time 45 days from deposit.",
                      "valid_until": datetime.date(2025, 7, 30)}
        )
        if created:
            QuoteLineItem.objects.create(
                quote=quote, description="6-Seater Dining Table — Solid Mvule, teak oil finish",
                quantity=Decimal("1"), unit_price=Decimal("145000")
            )
            QuoteLineItem.objects.create(
                quote=quote, description="Matching Dining Chairs × 6 — Mvule frame, linen upholstery",
                quantity=Decimal("6"), unit_price=Decimal("8500")
            )
            quote.recalculate()
            self.stdout.write("  ✓ Quote QT-06-2025-0001 created")

        # Job
        job, created = Job.objects.get_or_create(
            job_id="JC-06-01-2025-0001",
            defaults={"client": client1, "status": JobStatus.IN_PRODUCTION,
                      "quoted_price": Decimal("196000"), "description": "Heritage Dining Set commission"}
        )
        if created:
            quote.job = job; quote.save()

        # Design brief
        brief, _ = DesignBrief.objects.get_or_create(
            job=job, version=1,
            defaults={
                "title": "Heritage Dining Set v1", "status": DesignBriefStatus.APPROVED,
                "description": "6-seater dining table 2400×900×760mm + 6 chairs. Mvule solid wood. "
                               "Mortise-and-tenon joints. Teak oil finish. No stain.",
                "dimensions": "Table: 2400×900×760mm | Chairs: 450×450×900mm",
                "primary_species": "Mvule", "finish": "Teak oil, 2 coats",
                "approved_at": timezone.now(),
            }
        )

        # Invoice
        inv, created = Invoice.objects.get_or_create(
            invoice_id="INV-06-2025-0001",
            defaults={"job": job, "client": client1, "due_at": datetime.date(2025, 9, 1),
                      "notes": "50% deposit paid. Balance on delivery."}
        )
        if created:
            InvoiceLineItem.objects.create(
                invoice=inv, description="Heritage Dining Table — Solid Mvule",
                quantity=Decimal("1"), unit_price=Decimal("145000")
            )
            InvoiceLineItem.objects.create(
                invoice=inv, description="Matching Dining Chairs × 6",
                quantity=Decimal("6"), unit_price=Decimal("8500")
            )
            inv.recalculate()

        # Deposit payment
        Payment.objects.get_or_create(
            invoice=inv, mpesa_ref="QJK1234ABCD",
            defaults={"amount": Decimal("98000"), "method": PaymentMethod.MPESA,
                      "status": PaymentStatus.CONFIRMED, "paid_at": timezone.now(),
                      "recorded_by": admin_user}
        )

        # Job card
        card, _ = JobCard.objects.get_or_create(
            job=job,
            defaults={"is_locked": False, "unlocked_by": admin_user, "unlocked_at": timezone.now(),
                      "start_date": datetime.date(2025, 6, 10),
                      "target_completion": datetime.date(2025, 7, 25)}
        )

        # BOM entries
        if not card.timber_entries.exists():
            TimberEntry.objects.create(
                job_card=card, species=TimberSpecies.MVULE, board_feet=Decimal("18.5"),
                unit_cost_per_bf=Decimal("450"), supplier=mvule_sup, state=BOMState.ACTUAL,
                date_purchased=datetime.date(2025, 6, 12)
            )
            TimberEntry.objects.create(
                job_card=card, species=TimberSpecies.MVULE, board_feet=Decimal("6.0"),
                unit_cost_per_bf=Decimal("450"), supplier=mvule_sup, state=BOMState.ACTUAL,
                date_purchased=datetime.date(2025, 6, 12), notes="Chair frames"
            )
            HardwareEntry.objects.create(
                job_card=card, item_name="M8 Bolts + Barrel Nuts (table frame)",
                quantity=Decimal("24"), unit_cost=Decimal("45"), supplier=hw_sup, state=BOMState.ACTUAL
            )
            HardwareEntry.objects.create(
                job_card=card, item_name="Teak Oil 1L × 2", quantity=Decimal("2"),
                unit_cost=Decimal("850"), supplier=hw_sup, state=BOMState.ACTUAL
            )
            HardwareEntry.objects.create(
                job_card=card, item_name="Linen upholstery fabric (chair seats)",
                quantity=Decimal("3.5"), unit_cost=Decimal("1200"), supplier=hw_sup, state=BOMState.ACTUAL
            )
            LaborEntry.objects.create(
                job_card=card, artisan=artisan1, task_description="Table frame construction + joinery",
                piece_rate=Decimal("8000"), state=BOMState.ACTUAL, work_date=datetime.date(2025, 6, 20)
            )
            LaborEntry.objects.create(
                job_card=card, artisan=artisan1, task_description="6 × Chair frames",
                piece_rate=Decimal("6000"), state=BOMState.ACTUAL, work_date=datetime.date(2025, 6, 22)
            )
            LaborEntry.objects.create(
                job_card=card, artisan=artisan2, task_description="Sanding + 2 coats teak oil (table + chairs)",
                piece_rate=Decimal("3500"), state=BOMState.ACTUAL, work_date=datetime.date(2025, 6, 25)
            )

        # Waitlist entries
        from storefront.models import Waitlist, BudgetRange, WaitlistStatus
        Waitlist.objects.get_or_create(
            email="nj.kamau@example.co.ke",
            defaults={"name": "NJ Kamau", "phone": "+254700333001",
                      "piece_of_interest": "Master bedroom wardrobe — mahogany",
                      "budget_range": BudgetRange.K150_300, "timeline_months": 4}
        )
        Waitlist.objects.get_or_create(
            email="dibora.hailu@example.co.ke",
            defaults={"name": "Dibora Hailu", "phone": "+254700333002",
                      "piece_of_interest": "Home office fit-out — desk + shelving",
                      "budget_range": BudgetRange.K300_500, "timeline_months": 3}
        )
        self.stdout.write("  ✓ Waitlist entries created")

        self.stdout.write("\n✅ Demo seed complete!")
        self.stdout.write("   Login: http://127.0.0.1:8000/accounts/login/")
        self.stdout.write("   Username: admin | Password: mn2025admin")
        self.stdout.write("   Admin panel: http://127.0.0.1:8000/admin/")
        self.stdout.write("   Dashboard: http://127.0.0.1:8000/dashboard/")
        self.stdout.write("   Public store: http://127.0.0.1:8000/\n")
