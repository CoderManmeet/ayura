# Phase B (Ayura): a category may sit inside another category.
#
# Apply:     python manage.py migrate store 0040
# Roll back: python manage.py migrate store 0039   (drops the column; no category is lost)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0039_review_one_per_user_per_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="store.category",
            ),
        ),
    ]
