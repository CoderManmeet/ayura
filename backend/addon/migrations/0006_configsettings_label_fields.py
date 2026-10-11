# Phase B (Ayura): store-wide product information (maker, address, origin, customer care).
#
# Apply:     python manage.py migrate addon 0006
# Roll back: python manage.py migrate addon 0005   (drops the four columns)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("addon", "0005_currency_defaults_inr"),
    ]

    operations = [
        migrations.AddField(
            model_name="configsettings",
            name="consumer_care_contact",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Customer care contact: name or role, phone and email.",
            ),
        ),
        migrations.AddField(
            model_name="configsettings",
            name="country_of_origin",
            field=models.CharField(
                blank=True, default="", help_text="For example: India.", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="configsettings",
            name="maker_address",
            field=models.TextField(
                blank=True, default="", help_text="Maker's full address."
            ),
        ),
        migrations.AddField(
            model_name="configsettings",
            name="maker_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Name of the maker (manufactured and marketed by).",
                max_length=200,
            ),
        ),
    ]
