# Phase B (Ayura): the declared net quantity of each size (e.g. 30 ml, 50 g). Deliberately NOT
# copied from weight_grams, which is the packed shipping weight in Ayura (BUILD_LOG K5, B3).
#
# Apply:     python manage.py migrate catalog 0007
# Roll back: python manage.py migrate catalog 0006   (drops the two columns)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_opening_price_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="net_quantity",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="net_quantity_unit",
            field=models.CharField(
                blank=True, choices=[("g", "g"), ("ml", "ml")], default="", max_length=2
            ),
        ),
    ]
