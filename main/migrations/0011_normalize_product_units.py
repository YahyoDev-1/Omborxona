from django.db import migrations

# Maps whatever free text was typed before to the new fixed choice. Keys are
# lowercased for matching; anything not listed here is left untouched rather
# than guessed at.
UNIT_ALIASES = {
    'dona': 'dona', 'piece': 'dona', 'pieces': 'dona', 'pcs': 'dona', 'pc': 'dona', 'ta': 'dona',

    'kg': 'kg', 'kilogram': 'kg', 'kilogramm': 'kg', 'kilo': 'kg',

    'gramm': 'gramm', 'gram': 'gramm', 'gr': 'gramm', 'g': 'gramm',

    'litr': 'litr', 'litre': 'litr', 'liter': 'litr', 'l': 'litr',

    'quti': 'quti', 'qadoq': 'quti', 'box': 'quti', 'karobka': 'quti',

    'paket': 'paket', 'pack': 'paket', 'pack.': 'paket',
}


def normalize_units(apps, schema_editor):
    Product = apps.get_model('main', 'Product')
    for product in Product.objects.exclude(unit__isnull=True).exclude(unit=''):
        canonical = UNIT_ALIASES.get(product.unit.strip().lower())
        if canonical and canonical != product.unit:
            product.unit = canonical
            product.save(update_fields=['unit'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_alter_product_unit'),
    ]

    operations = [
        migrations.RunPython(normalize_units, noop_reverse),
    ]
