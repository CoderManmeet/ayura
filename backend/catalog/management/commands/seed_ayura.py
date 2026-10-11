"""
Seed a placeholder Ayura catalogue for LOCAL DEVELOPMENT and the Playwright suite.

    python manage.py seed_ayura

Creates categories (Skincare, with Face and Lips inside it; Haircare; Bodycare), eight placeholder
products with their sizes and net quantities, care information, opening stock booked through the
stock ledger, a simple placeholder picture per product, and one demo coupon. Everything here is placeholder data: names, descriptions, sizes and prices
are not the brand's real catalogue.

Wording rules (ROADMAP-AYURA guardrails): cosmetic language only. No disease or treatment
claims, and no "natural", "Ayurvedic", "organic", "chemical-free" or similar claims, because
none of those is a stored fact the owner has entered. `BANNED_CLAIM_WORDS` is checked by the test
suite against everything this command writes.

Idempotent: running it again changes nothing that already exists. Refuses to run unless DEBUG
is True, so it can never touch a production database.
"""

from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from addon.models import ConfigSettings
from catalog.models import ProductVariant
from core.audit import acting_as
from core.money import from_paise
from inventory.models import Batch
from inventory.services import receive_production
from store.models import Category, Coupon, Product
from vendor.models import Vendor

# Words that must never appear in seeded copy. The same list is used by the test suite.
BANNED_CLAIM_WORDS = (
    "cure", "cures", "treat", "treats", "treatment", "heal", "heals", "clinically", "proven",
    "guaranteed", "100%", "chemical-free", "chemical free", "organic", "natural", "ayurvedic",
    "dermatologist", "acne", "hair fall", "hairfall", "dandruff", "anti-ageing", "anti-aging",
    "reverses", "medicine", "medicinal", "candle", "noore",
)

# (slug, title, parent slug). Parents come before their children.
CATEGORIES = (
    ("skincare", "Skincare", None),
    ("face", "Face", "skincare"),
    ("lips", "Lips", "skincare"),
    ("haircare", "Haircare", None),
    ("bodycare", "Bodycare", None),
)

# Placeholder care information, in cosmetic language (product slug -> (benefit line, how to use)).
CARE = {
    "face-serum": ("A light serum for everyday use", "Smooth two or three drops over clean skin, morning or night."),
    "face-scrub": ("A weekly scrub for softer-feeling skin", "Massage gently over damp skin once or twice a week, then rinse."),
    "day-moisturiser": ("A daily moisturiser for normal to dry skin", "Apply to clean skin every morning."),
    "hair-oil": ("A pre-wash oil for the scalp and lengths", "Massage into the scalp and lengths, leave for an hour, then wash."),
    "shampoo": ("Helps cleanse the hair and scalp", "Lather into wet hair, then rinse well."),
    "body-butter": ("A rich butter for dry areas", "Warm a little between your palms and smooth over dry skin."),
    "body-oil": ("A body oil for after the bath", "Smooth over damp skin after a bath."),
    "lip-balm": ("A balm to keep your lips soft", "Apply whenever your lips feel dry."),
}
CAUTIONS = "For external use only. Patch test before first use. Keep away from eyes. Store in a cool, dry place."

# (slug, title, category slug, shape for the placeholder picture, description, featured, sizes)
# sizes: (label, shipping weight in grams incl. packaging, price paise, MRP paise)
PRODUCTS = (
    ("face-serum", "Face Serum", "face", "dropper",
     "A lightweight face serum for everyday use, morning or night.", True,
     (("30 ml", 90, 44900, 49900), ("50 ml", 130, 64900, 69900))),
    ("face-scrub", "Face Scrub", "face", "jar",
     "A gentle-feeling face scrub to use once or twice a week on damp skin.", True,
     (("50 g", 110, 34900, 39900), ("100 g", 180, 54900, 59900))),
    ("day-moisturiser", "Day Moisturiser", "face", "jar",
     "A soft daily moisturiser for the face, for normal to dry skin.", True,
     (("50 g", 110, 39900, 44900), ("100 g", 180, 59900, 64900))),
    ("hair-oil", "Hair Oil", "haircare", "bottle",
     "A hair oil to massage into the scalp and lengths before washing.", True,
     (("100 ml", 160, 29900, 34900), ("200 ml", 280, 49900, 54900))),
    ("shampoo", "Shampoo", "haircare", "bottle",
     "A shampoo that helps cleanse the hair and scalp. For regular use.", True,
     (("200 ml", 260, 34900, 39900), ("400 ml", 470, 59900, 64900))),
    ("body-butter", "Body Butter", "bodycare", "jar",
     "A rich body butter for dry areas such as elbows, knees and heels.", True,
     (("100 g", 180, 44900, 49900), ("200 g", 300, 74900, 79900))),
    ("body-oil", "Body Oil", "bodycare", "bottle",
     "A body oil to smooth over damp skin after a bath.", False,
     (("100 ml", 160, 39900, 44900), ("200 ml", 280, 64900, 69900))),
    ("lip-balm", "Lip Balm", "lips", "tin",
     "A lip balm to keep in your bag.", False,
     (("10 g", 40, 14900, 17900),)),
)

OPENING_UNITS = 20
# Opening batches get a best-before date, so the stock ledger's FEFO order has something to
# work with. Placeholder only: the real shelf life is the owner's to enter.
OPENING_SHELF_LIFE_DAYS = 365
DEMO_COUPON_CODE = "WELCOME10"
PLACEHOLDER_NOTE = " [PLACEHOLDER COPY] Replace this text with the real product description."


def placeholder_picture(shape):
    """
    A plain 4:5 picture with one simple container shape, so local listings are not empty boxes.

    Drawn with Pillow (already a dependency for image fields). Neutral colours, no text, no
    product claims: it only shows that a photo belongs here.
    """
    from PIL import Image, ImageDraw

    width, height = 800, 1000
    image = Image.new("RGB", (width, height), (226, 224, 216))
    draw = ImageDraw.Draw(image)
    body, cap = (120, 116, 104), (74, 72, 64)
    cx = width // 2
    if shape == "dropper":
        draw.rounded_rectangle((cx - 110, 470, cx + 110, 820), radius=40, fill=body)
        draw.rectangle((cx - 50, 400, cx + 50, 470), fill=cap)
        draw.ellipse((cx - 55, 300, cx + 55, 410), fill=cap)
    elif shape == "bottle":
        draw.rounded_rectangle((cx - 130, 380, cx + 130, 840), radius=50, fill=body)
        draw.rectangle((cx - 45, 290, cx + 45, 380), fill=cap)
    elif shape == "tin":
        draw.ellipse((cx - 160, 560, cx + 160, 700), fill=body)
        draw.rectangle((cx - 160, 520, cx + 160, 630), fill=body)
        draw.ellipse((cx - 160, 460, cx + 160, 600), fill=cap)
    else:  # jar
        draw.rounded_rectangle((cx - 170, 520, cx + 170, 820), radius=36, fill=body)
        draw.rounded_rectangle((cx - 180, 450, cx + 180, 530), radius=14, fill=cap)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Create the placeholder Ayura catalogue for local development (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--no-pictures", action="store_true",
                            help="Do not draw placeholder pictures (products keep no photo).")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_ayura only runs when DEBUG is True. It is for local development data.")

        with transaction.atomic(), acting_as(None, label="system:seed_ayura"):
            if ConfigSettings.objects.first() is None:
                ConfigSettings.objects.create()
                self.stdout.write("created ConfigSettings (default shipping settings, tax 0)")

            # Products are attached to the owner's shop when one exists, so they show up in
            # the owner dashboard. No shop is created here.
            shop = Vendor.objects.order_by("id").first()
            categories = {}
            for slug, title, parent_slug in CATEGORIES:
                categories[slug] = self._category(slug, title, categories.get(parent_slug))

            created_products = created_variants = stocked = 0
            for slug, title, category_slug, shape, description, featured, sizes in PRODUCTS:
                product, was_created = self._product(
                    slug, title, categories[category_slug], description, featured, shape, shop,
                    pictures=not options["no_pictures"],
                )
                created_products += int(was_created)
                for label, grams, price_paise, mrp_paise in sizes:
                    variant, variant_created = self._variant(product, slug, label, grams, price_paise, mrp_paise)
                    created_variants += int(variant_created)
                    stocked += int(self._opening_stock(variant))

            coupon_created = self._coupon(shop)

        self.stdout.write(self.style.SUCCESS(
            f"seed_ayura: {created_products} product(s), {created_variants} variant(s) and "
            f"{stocked} opening batch(es) created; demo coupon {DEMO_COUPON_CODE} "
            f"{'created' if coupon_created else 'already present'}."
        ))

    def _category(self, slug, title, parent=None):
        category = Category.objects.filter(slug=slug).first()
        if category is None:
            category = Category.objects.create(title=title, slug=slug, active=True, parent=parent)
        return category

    def _product(self, slug, title, category, description, featured, shape, shop, pictures):
        product = Product.objects.filter(slug=slug).first()
        if product is not None:
            return product, False
        _label, _grams, price_paise, mrp_paise = next(
            sizes for s, _t, _c, _sh, _d, _f, sizes in PRODUCTS if s == slug)[0]
        benefit_line, how_to_use = CARE[slug]
        product = Product.objects.create(
            title=title,
            slug=slug,
            category=category,
            description=description + PLACEHOLDER_NOTE,
            benefit_line=benefit_line,
            how_to_use=how_to_use,
            cautions=CAUTIONS,
            ingredients="[PLACEHOLDER] The full ingredient list goes here, exactly as on the label.",
            price=from_paise(price_paise),
            old_price=from_paise(mrp_paise),
            stock_qty=0,
            status="published",
            featured=featured,
            vendor=shop,
        )
        if pictures:
            product.image.save(f"{slug}.jpg", placeholder_picture(shape), save=True)
        return product, True

    def _variant(self, product, slug, label, grams, price_paise, mrp_paise):
        sku = f"SEED-{slug.upper()}-{label.replace(' ', '').upper()}"
        variant = ProductVariant.objects.filter(sku=sku).first()
        if variant is not None:
            return variant, False

        amount, unit = label.split(" ")
        fields = dict(
            sku=sku, name=label, options={"Size": label}, weight_grams=grams,
            net_quantity=int(amount), net_quantity_unit=unit,
            price_paise=price_paise, mrp_paise=mrp_paise, perishable=False, active=True,
        )
        # Creating the product created its default variant; the first size takes that slot.
        default = ProductVariant.objects.filter(product=product, is_default=True).first()
        if default is not None and default.name == "Default" and not default.options:
            for name, value in fields.items():
                setattr(default, name, value)
            default.save()
            return default, True
        return ProductVariant.objects.create(product=product, is_default=False, **fields), True

    def _opening_stock(self, variant):
        batch_code = f"SEED-{variant.sku}"[:64]
        if Batch.objects.filter(batch_code=batch_code).exists():
            return False
        today = timezone.localdate()
        batch = Batch.objects.create(
            batch_code=batch_code, variant=variant, manufactured_on=today,
            best_before=today + timedelta(days=OPENING_SHELF_LIFE_DAYS),
            quantity_produced=OPENING_UNITS, cost_per_unit_paise=0,
            production_notes="Placeholder opening stock from seed_ayura (local development)",
        )
        receive_production(variant, batch, OPENING_UNITS, reason="seed_ayura opening stock")
        return True

    def _coupon(self, shop):
        if Coupon.objects.filter(code__iexact=DEMO_COUPON_CODE).exists():
            return False
        Coupon.objects.create(
            vendor=shop, code=DEMO_COUPON_CODE, kind="PERCENT", discount=10, active=True,
            max_uses_per_customer=1, max_total_uses=None,
        )
        return True
