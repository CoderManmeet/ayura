from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import AppendOnlyModel
from store.models import Product


NET_QUANTITY_UNITS = (
    ("g", "g"),
    ("ml", "ml"),
)


class ProductVariant(models.Model):
    """
    A sellable unit: the thing that carries a SKU, a price and stock.

    `Product` remains the marketing/catalogue entry. Every product has exactly one
    default variant (created by the F-B backfill); products with real options get more.
    Money is stored as integer paise (rule 6). Legacy Decimal columns on Product are
    left untouched and remain the source of truth until the money migration.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120, default="Default")

    # Optional option values. Kept as plain text to mirror how the cart already stores them.
    size = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)

    # What makes this variant different from its siblings, as {option name: value}, e.g.
    # {"Size": "200 g"}. The storefront builds one selector per key, so a second axis
    # (for example {"Size": "200 g", "Colour": "Ivory"}) needs data only, no code.
    options = models.JSONField(default=dict, blank=True)

    price_paise = models.BigIntegerField(validators=[MinValueValidator(0)])
    mrp_paise = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    # Packed weight in grams, for shipping. NOT the declared net quantity (see below).
    weight_grams = models.PositiveIntegerField(null=True, blank=True)

    # The declared net quantity of the product in this pack, e.g. 30 ml or 50 g (Phase B, Ayura).
    # Shown on the product page as "Net quantity". Empty until the owner enters it.
    net_quantity = models.PositiveIntegerField(null=True, blank=True)
    net_quantity_unit = models.CharField(max_length=2, choices=NET_QUANTITY_UNITS, blank=True, default="")

    # Perishable variants require a best_before on every batch and show it on the product page.
    perishable = models.BooleanField(default=False)

    # A sample size given away with orders (Phase D, Ayura). It has its own SKU and its own stock
    # in the ledger, is never shown in the shop or the size picker, and is never charged for.
    is_sample = models.BooleanField(default=False)

    # A kit sold as one item but made up of other variants (Phase E, Ayura). A kit has no stock
    # of its own: what it can sell is decided by its components, and buying one holds theirs.
    # A kit is never a component of another kit, and never a sample (ROADMAP Z7).
    is_kit = models.BooleanField(default=False)

    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id", "-is_default", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"], condition=models.Q(is_default=True), name="catalog_one_default_variant_per_product"
            ),
        ]

    def __str__(self):
        return f"{self.sku} ({self.product.title} / {self.name})"

    @property
    def net_quantity_label(self):
        """'30 ml', or '' when the owner has not entered a net quantity."""
        if self.net_quantity and self.net_quantity_unit:
            return f"{self.net_quantity} {self.net_quantity_unit}"
        return ""

    @property
    def sellable(self):
        """True when a shopper may see and buy this variant."""
        return self.active and not self.is_sample

    def kit_parts(self):
        """What is inside this kit, in a stable order. Empty for anything that is not a kit."""
        if not self.is_kit:
            return []
        return list(
            KitComponent.objects.filter(kit_variant=self)
            .select_related("component_variant", "component_variant__product")
            .order_by("id")
        )

    @property
    def available_qty(self):
        from inventory.services import available_qty

        return available_qty(self)


class KitComponent(models.Model):
    """
    One part of a kit: `qty` units of `component_variant` go into every `kit_variant` sold
    (Phase E, Ayura).

    A kit holds no stock itself. Its availability is the scarcest of its components
    (`inventory.services.kit_available_qty`), and selling one holds every component's stock
    through the ledger, all or nothing.

    The kit's price is whatever the owner set on the kit variant: it is never added up from
    the components (ROADMAP Z7), so a kit can be cheaper than its parts.
    """

    kit_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="kit_components")
    component_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="part_of_kits")
    qty = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["kit_variant_id", "id"]
        constraints = [
            models.UniqueConstraint(fields=["kit_variant", "component_variant"],
                                    name="catalog_kitcomponent_kit_component_uniq"),
            models.CheckConstraint(check=~models.Q(kit_variant=models.F("component_variant")),
                                   name="catalog_kitcomponent_not_itself"),
        ]

    def __str__(self):
        return f"{self.qty} x {self.component_variant.sku} in {self.kit_variant.sku}"


class PriceHistory(AppendOnlyModel):
    """
    Append-only record of every selling price and MRP a variant has had (ROADMAP P9).

    One row is written by a signal each time `ProductVariant.price_paise` or `mrp_paise`
    changes through save(), whatever the entry point (owner dashboard, Django admin, shell,
    management command). `effective_from` is when that price started applying; a row stays
    in force until the next row for the same variant.
    """

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="price_history")
    price_paise = models.BigIntegerField(validators=[MinValueValidator(0)])
    mrp_paise = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    effective_from = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        "userauths.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    actor_label = models.CharField(max_length=100, default="system")

    class Meta:
        ordering = ["-effective_from", "-id"]
        verbose_name_plural = "Price history"
        indexes = [models.Index(fields=["variant", "effective_from"])]

    def __str__(self):
        return f"{self.variant.sku} @ {self.price_paise} paise from {self.effective_from:%Y-%m-%d %H:%M}"
