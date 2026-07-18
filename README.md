# MN Studio — Business Management Platform

> Bespoke Hardwood Furniture · Nairobi, Kenya  
> Django 5.1 · PostgreSQL · Tailwind CSS · Celery · M-Pesa Daraja

---

## Architecture Overview

```
mnstudio_project/
├── core/           # Job (central entity), AuditLog
├── crm/            # ClientProfile, Lead, DesignBrief, Interaction
├── production/     # JobCard, TimberEntry, HardwareEntry, LaborEntry + signals
├── partners/       # SupplierProfile, PurchaseOrder, ArtisanProfile
├── ledger/         # Quote, Invoice, Payment, COGSRecord, CompliancePeriod
│   ├── compliance.py   # Stateless compliance service (TOT, AHL, Retirement, SACCO)
│   ├── mpesa.py        # Daraja STK Push service
│   └── tasks.py        # Celery async tasks
├── storefront/     # Product, AuctionLot, AuctionBid, Waitlist
├── certificates/   # Certificate of Authenticity, CareSchedule
├── templates/      # All HTML templates (Tailwind + Alpine.js)
└── static/         # mnstudio.css, mnstudio.js
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/n-mbachia/mnStudio_project.git
cd mnstudio
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Spin up all services (Web, DB, Redis, Celery)
docker compose up --build

### 3. Initialize database & seed demo data (Run in a separate terminal)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demoConfigure Environment
```

### 4. Run

```bash
# Terminal 1 — Django
python manage.py runserver

# Terminal 2 — Celery worker (for STK push + care reminders)
celery -A mnstudio worker --loglevel=info

# Access the platform
# Public storefront:  http://127.0.0.1:8000/
# Business dashboard: http://127.0.0.1:8000/dashboard/  (login: admin / mn2025admin)
# Django admin:       http://127.0.0.1:8000/admin/
```

---

## Statutory Compliance Engine

The compliance service (`ledger/compliance.py`) is **stateless and context-free**.

| Obligation | Base | Rate | Frequency |
|---|---|---|---|
| Turnover Tax (TOT) | Gross Sales | 1.5% | Monthly |
| Affordable Housing Levy (AHL) | Gross Sales | 1.5% | Monthly |
| Retirement Savings | Gross Profit | 10% | Monthly |
| Business SACCO | Gross Profit | 10% | Monthly |

**Critical:** AHL and TOT use **gross sales** as base. Retirement and SACCO use **gross profit**. The system enforces cash-basis accounting — `Payment.paid_at` (not `Invoice.issued_at`) drives period assignment.

```bash
# Recompute current month
python manage.py refresh_compliance

# Recompute a specific month
python manage.py refresh_compliance --year 2025 --month 4
```

---

## Material-to-Margin Intelligence (MMI)

Every commission flows through:

```
Client Brief → Quote (Estimated BOM) → Job Card (Actual BOM) → COGS Signal → Ledger
```

- `TimberEntry`, `HardwareEntry`, `LaborEntry` have two states: `ESTIMATED` and `ACTUAL`
- Django signals auto-sync `Job.actual_cogs` and `Job.gross_profit` on every save/delete
- `PurchaseOrder` price is locked at receipt (`unit_cost_at_receipt`) and propagated to linked BOM entries
- Variance = `estimated_cogs − actual_cogs` (negative = cost overrun)

---

## Production Gate

Job Cards are locked (`is_locked=True`) by default. Unlock requires **both**:

1. A `DesignBrief` in `APPROVED` state for the job
2. A confirmed `Payment` ≥ `Quote.deposit_amount` on the linked invoice

```python
success, reason = card.unlock(request.user)
```

---

## Tests

```bash
python manage.py test ledger.tests core.tests

# Key test: compliance base correctness
# - TOT and AHL on gross SALES
# - Retirement and SACCO on gross PROFIT
# - Cash basis (Payment.paid_at, not Invoice.issued_at)
```

---

## Deployment (Railway / Render)

1. Set `DEBUG=False`, `ALLOWED_HOSTS=yourdomain.com` in `.env`
2. `DATABASE_URL` → Railway/Render PostgreSQL add-on
3. `REDIS_URL` → Railway/Render Redis add-on
4. Run `python manage.py collectstatic` before deploy
5. Procfile runs `web:` (gunicorn) + `worker:` (celery) processes

---

## Key URLs

| URL | Description |
|---|---|
| `/` | Public storefront — home |
| `/shop/` | Product catalogue |
| `/shop/auctions/` | Live auctions |
| `/shop/waitlist/` | Demand waitlist |
| `/certificates/<uuid>/` | Public CoA verification |
| `/dashboard/` | Business dashboard (auth required) |
| `/crm/` | Client management |
| `/crm/pipeline/` | Sales pipeline |
| `/production/` | Job cards + BOM entries |
| `/ledger/quotes/` | Quote builder |
| `/ledger/invoices/` | Invoice + payments |
| `/ledger/compliance/` | Compliance dashboard |
| `/partners/suppliers/` | Supplier registry |
| `/partners/pos/` | Purchase orders |
| `/partners/artisans/` | Artisan registry |
| `/admin/` | Django admin |

---

*MN Studio Business OS — Built on the Zero to One principle:  
own your Material-to-Margin Intelligence loop.*
# mnStudio_project
