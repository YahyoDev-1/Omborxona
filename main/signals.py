from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ImportProduct, Product


@receiver(post_save, sender=ImportProduct)
def update_stock_after_import(sender, instance, created, **kwargs):
    """Increase Product stock when a new ImportProduct is created."""
    if not created or instance.product_id is None:
        return

    # select_for_update requires an open transaction; ImportsView.post()
    # wraps the ImportProduct.objects.create() call (which triggers this
    # signal synchronously) in transaction.atomic() for exactly this reason.
    # It locks the row against concurrent imports of the same product - a
    # no-op on SQLite (no row locking support), but effective once the
    # project moves to Postgres/MySQL.
    product = Product.objects.select_for_update().get(pk=instance.product_id)
    product.amount += instance.amount
    if instance.sell_price:
        product.price = instance.sell_price
    product.save()
