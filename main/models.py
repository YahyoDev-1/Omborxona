from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings

# Create your models here.

User = settings.AUTH_USER_MODEL

# Money: 2 decimal places is enough for currency and avoids binary
# floating-point rounding drift (0.1 + 0.2 != 0.3) that FloatField had.
def money_field(**kwargs):
    kwargs.setdefault('max_digits', 14)
    kwargs.setdefault('decimal_places', 2)
    kwargs.setdefault('validators', [MinValueValidator(0)])
    return models.DecimalField(**kwargs)


# Quantities (kg, litre, dona, ...) can be fractional, so keep 3 decimals.
def quantity_field(**kwargs):
    kwargs.setdefault('max_digits', 12)
    kwargs.setdefault('decimal_places', 3)
    kwargs.setdefault('validators', [MinValueValidator(0)])
    return models.DecimalField(**kwargs)


class Branch(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    price = money_field()
    amount = quantity_field(default=0)
    unit = models.CharField(max_length=20, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Client(models.Model):
    name = models.CharField(max_length=100)
    shop_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    debt = money_field(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Sale(models.Model):
    # PROTECT, not CASCADE: a Product/Client can't be deleted out from under
    # its sales history - that would silently erase financial records that
    # must never be deleted (see SaleAdmin.has_delete_permission).
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    amount = quantity_field(default=1)
    description = models.TextField(blank=True, null=True)
    total_price = money_field(default=0)
    paid_price = money_field(default=0)
    debt_price = money_field(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} -- {self.client.name} -- {self.amount} -- {self.product.unit}"


class ImportProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    amount = quantity_field()
    buy_price = money_field()
    sell_price = money_field(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.product.name} -- {self.amount} -- {self.product.unit}"


class PayDebt(models.Model):
    # Same reasoning as Sale.client: payment history must survive the
    # client record it was made against.
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    amount = money_field()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.client.name} -- {self.amount} -- {self.description}"
