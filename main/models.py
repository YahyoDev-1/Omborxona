from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings

# Create your models here.

User = settings.AUTH_USER_MODEL


class Branch(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    price = models.FloatField(validators=[MinValueValidator(0.0)])
    amount = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
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
    debt = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    amount = models.FloatField(validators=[MinValueValidator(0.0)], default=1)
    description = models.TextField(blank=True, null=True)
    total_price = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    paid_price = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    debt_price = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} -- {self.client.name} -- {self.amount} -- {self.product.unit}"


class ImportProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField(validators=[MinValueValidator(0.0)])
    buy_price = models.FloatField(validators=[MinValueValidator(0.0)])
    sell_price = models.FloatField(validators=[MinValueValidator(0.0)], blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.product.name} -- {self.amount} -- {self.product.unit}"


class PayDebt(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    amount = models.FloatField(validators=[MinValueValidator(0.0)])
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.client.name} -- {self.amount} -- {self.description}"
