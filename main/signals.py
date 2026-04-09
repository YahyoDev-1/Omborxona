from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ImportProduct


@receiver(post_save, sender=ImportProduct)
def update_stock_after_import(sender, instance, created, **kwargs):
    """
    Kirim (ImportProduct) saqlanganda avtomatik Product miqdorini oshiradi.
    """
    if created:  # Faqat yangi kirim yaratilganda ishlaydi (tahrirlashda emas)
        product = instance.product
        # 1. Ombor qoldig'ini oshiramiz
        product.amount += instance.amount
        # 2. Sotish narxini yangilaymiz
        if instance.sell_price:
            product.price = instance.sell_price

        product.save()