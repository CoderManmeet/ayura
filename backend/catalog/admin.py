from django.contrib import admin

from catalog.models import KitComponent, PriceHistory, ProductVariant
from inventory.services import available_qty, on_hand_qty


class KitComponentInline(admin.TabularInline):
    """What goes inside a kit (Phase E). Shown on the kit's own variant page.

    The owner's normal screen for this is Admin area -> Kits; this inline is the fallback.
    A kit never contains another kit or a sample (ROADMAP Z7); the model's constraints and
    `store/owner_kits.py` enforce that, so pick components with care from here.
    """

    model = KitComponent
    fk_name = "kit_variant"
    extra = 1
    autocomplete_fields = ["component_variant"]
    fields = ["component_variant", "qty"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "product", "name", "options", "net_quantity", "net_quantity_unit", "price_rupees",
                    "mrp_rupees", "perishable", "is_kit", "is_sample", "is_default", "active", "on_hand",
                    "available"]
    list_filter = ["active", "is_default", "perishable", "is_kit", "is_sample"]
    search_fields = ["sku", "name", "product__title"]
    autocomplete_fields = ["product"]
    inlines = [KitComponentInline]

    @admin.display(description="Price")
    def price_rupees(self, obj):
        from core.money import format_inr

        return format_inr(obj.price_paise)

    @admin.display(description="MRP")
    def mrp_rupees(self, obj):
        from core.money import format_inr

        return format_inr(obj.mrp_paise) if obj.mrp_paise else "-"

    @admin.display(description="On hand")
    def on_hand(self, obj):
        return on_hand_qty(obj)

    @admin.display(description="Available")
    def available(self, obj):
        return available_qty(obj)


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Read-only: rows are written by a signal on every price change and are append-only."""

    list_display = ["effective_from", "variant", "price_rupees", "mrp_rupees", "actor_label"]
    list_filter = ["effective_from"]
    search_fields = ["variant__sku", "variant__product__title"]
    date_hierarchy = "effective_from"
    readonly_fields = [f.name for f in PriceHistory._meta.fields]

    @admin.display(description="Price")
    def price_rupees(self, obj):
        from core.money import format_inr

        return format_inr(obj.price_paise)

    @admin.display(description="MRP")
    def mrp_rupees(self, obj):
        from core.money import format_inr

        return format_inr(obj.mrp_paise) if obj.mrp_paise else "-"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
