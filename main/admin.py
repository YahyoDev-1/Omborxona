from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Branch)
admin.site.register(Product)
admin.site.register(Client)
admin.site.register(Sale)
admin.site.register(ImportProduct)
admin.site.register(PayDebt)