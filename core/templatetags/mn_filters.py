"""
MN Studio custom template filters.

Usage in templates:
    {% load mn_filters %}
    {{ value|kes }}
    {{ job.actual_margin_pct|margin_class }}
    {{ species_list|join_species }}
"""
from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def kes(value):
    """Format a number as Kenyan Shillings: KES 12,500.00"""
    try:
        return f"KES {Decimal(str(value)):,.2f}"
    except Exception:
        return f"KES {value}"


@register.filter
def kes_short(value):
    """Compact KES display: KES 12.5k  or  KES 1.2M"""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return f"KES {value}"
    if n >= 1_000_000:
        return f"KES {n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"KES {n/1_000:.1f}k"
    return f"KES {n:.0f}"


@register.filter
def margin_class(margin_pct):
    """Return a Tailwind text-color class based on margin percentage."""
    try:
        m = float(margin_pct)
    except (TypeError, ValueError):
        return "text-stone-400"
    if m >= 45:
        return "text-forest-700"
    if m >= 35:
        return "text-amber-600"
    return "text-red-600"


@register.filter
def bom_state_badge(state):
    """Return badge CSS classes for a BOM entry state."""
    if state == "actual":
        return "bg-forest-100 text-forest-800"
    return "bg-stone-100 text-stone-500"


@register.filter
def subtract(value, arg):
    """Subtract arg from value. {{ total|subtract:paid }}"""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except Exception:
        return value


@register.filter
def percent_of(value, total):
    """Return value as % of total. {{ cogs|percent_of:quoted_price }}"""
    try:
        v, t = Decimal(str(value)), Decimal(str(total))
        if t == 0:
            return Decimal("0.00")
        return (v / t * 100).quantize(Decimal("0.1"))
    except Exception:
        return 0


@register.simple_tag
def compliance_row(label, amount, base_label, highlight="normal"):
    """Render a compliance row — used in dashboard widget."""
    color = "text-red-700" if highlight == "danger" else "text-amber-700"
    return (
        f'<div class="flex justify-between items-center py-2 border-b border-stone-50">'
        f'<div><p class="text-sm font-medium text-charcoal-800">{label}</p>'
        f'<p class="text-xs text-stone-400">{base_label}</p></div>'
        f'<p class="text-sm font-semibold {color}">KES {Decimal(str(amount)):,.0f}</p>'
        f'</div>'
    )
