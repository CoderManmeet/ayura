# Phase B (Ayura): personal-care information on a product, all typed by the owner.
#
# Apply:     python manage.py migrate store 0041
# Roll back: python manage.py migrate store 0040   (drops the four columns and what was typed in them)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0040_category_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="benefit_line",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="product",
            name="ingredients",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="how_to_use",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="cautions",
            field=models.TextField(blank=True, default=""),
        ),
    ]
