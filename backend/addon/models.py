
from django.db import models
from django.utils.html import mark_safe
from django.utils.text import slugify

from shortuuid.django_fields import ShortUUIDField

import shortuuid
import datetime




SERVICE_FEE_CHARGE_TYPE = (
    ("percentage", "Percentage"),
    ("flat_rate", "Flat Rate"),
)

AFFILIATE_COMMISSION_TYPE = (
    ("percentage", "Percentage"),
    ("flat_rate", "Flat Rate"),
)





class ConfigSettings(models.Model):
    view_more = models.CharField(default="View All", max_length=10)
    currency_sign = models.CharField(default="\u20b9", max_length=10)
    currency_abbreviation = models.CharField(default="INR", max_length=10)
    service_fee_percentage = models.IntegerField(default=5, help_text="NOTE: Numbers added here are in percentage (%)ve.g 4%")
    service_fee_flat_rate = models.DecimalField(default=0.7, max_digits=12, decimal_places=2 ,help_text="NOTE: Add the amount you want to charge as service fee e.g $2.30")
    service_fee_charge_type = models.CharField(default="percentage", max_length=30, choices=SERVICE_FEE_CHARGE_TYPE)
    enforce_2fa = models.BooleanField(default=True)
    activate_affiliate_system = models.BooleanField(default=True)
    send_email_notifications = models.BooleanField(default=False)

    # --- pricing (Phase G1). All amounts are integer paise. --------------------------------------
    shipping_flat_paise = models.BigIntegerField(default=7900, help_text="Flat shipping charged once per order, in paise (Rs 79 = 7900).")
    free_shipping_threshold_paise = models.BigIntegerField(default=99900, help_text="Shipping is free when the subtotal after discount is at least this many paise (Rs 999 = 99900).")
    tax_rate_bps = models.PositiveIntegerField(default=0, help_text="Tax rate in basis points (18% = 1800). Prices are tax-inclusive: tax is carved out of the price, never added on top. 0 while the business is not GST-registered.")

    # --- shipping and Cash on Delivery switches (Phase C, Ayura). Set by the owner in the admin
    # area ("Store settings"); read only by store.pricing.quote() and the payment-method check.
    shipping_enabled = models.BooleanField(default=True, help_text="Off: no order is charged shipping.")
    free_shipping_enabled = models.BooleanField(default=True, help_text="Off: shipping is charged on every order, whatever its size.")
    cod_enabled = models.BooleanField(default=True, help_text="Off: Cash on Delivery is not offered at checkout.")
    cod_fee_enabled = models.BooleanField(default=False, help_text="On: Cash on Delivery orders pay the fee below, shown before the order is placed.")
    cod_fee_paise = models.BigIntegerField(default=0, help_text="Cash on Delivery fee in paise (Rs 49 = 4900). Charged only while the fee is switched on.")

    # --- product information shown on every product page (Phase B, Ayura). Store-wide, because
    # every product is made by the same maker. Blank = not shown. Which of these the law requires,
    # and in what wording, is a question for the owner's professional (ROADMAP L3).
    maker_name = models.CharField(max_length=200, blank=True, default="", help_text="Name of the maker (manufactured and marketed by).")
    maker_address = models.TextField(blank=True, default="", help_text="Maker's full address.")
    country_of_origin = models.CharField(max_length=100, blank=True, default="", help_text="For example: India.")
    consumer_care_contact = models.TextField(blank=True, default="", help_text="Customer care contact: name or role, phone and email.")

    # --- grievance officer (Phase F, Ayura). The Consumer Protection (E-Commerce) Rules require
    # an e-commerce store to publish these. EVERY FIELD IS THE OWNER'S OWN TEXT and every one is
    # blank by default: the storefront shows this block only once a name has been filled in, so
    # nothing is ever published on the store's behalf. Whether these details are required of this
    # business, and in what wording, is a question for the owner's professional (ROADMAP L4);
    # nothing in this codebase decides it.
    grievance_officer_name = models.CharField(max_length=200, blank=True, default="", help_text="Name of the grievance officer. Blank = the whole block is hidden.")
    grievance_officer_designation = models.CharField(max_length=200, blank=True, default="", help_text="For example: Grievance Officer, or Proprietor.")
    grievance_officer_email = models.CharField(max_length=254, blank=True, default="", help_text="Email address for grievances.")
    grievance_officer_phone = models.CharField(max_length=40, blank=True, default="", help_text="Phone number for grievances, as it should be printed.")
    grievance_officer_address = models.TextField(blank=True, default="", help_text="Postal address for grievances, if you want to publish one.")
    grievance_response_days = models.PositiveIntegerField(default=0, help_text="Days within which a grievance is acknowledged. 0 = do not state a time.")


    class Meta:
        verbose_name = ("Settings")
        verbose_name_plural = ("Settings")


    
    
class Tax(models.Model):
    country = models.CharField(max_length=500)
    rate = models.IntegerField(default=5, help_text="Numbers added here are in percentage (5 = 5%)")
    active = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Tax"

    def __str__(self):
        return f"{self.country}"
    

        
