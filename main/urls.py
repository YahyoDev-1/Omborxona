from django.urls import path

from .views import *

urlpatterns = [
    path('', Sections.as_view(), name='sections'),

    path('products/', Products.as_view(), name='products'),

    path('products/<int:pk>/update', ProductUpdateView.as_view(), name='product-update'),

    path('products/<int:pk>/delete', ProductDeleteView.as_view(), name='product-delete'),

    path('clients/', ClientsView.as_view(), name='clients'),

    path('clients/<int:pk>/update', ClientUpdateView.as_view(), name='client-update'),

    path('clients/<int:pk>/delete', ClientDeleteView.as_view(), name='client-delete'),

    path('sales/', SalesView.as_view(), name='sales'),

    path('sales/<int:pk>/update', SaleUpdateView.as_view(), name='sale-update'),

    path('sales/<int:pk>/delete', SaleDeleteView.as_view(), name='sale-delete'),

    path('imports/', ImportsView.as_view(), name='imports'),

    path('imports/<int:pk>/update', ImportUpdateView.as_view(), name='import-update'),

    path('imports/<int:pk>/delete', ImportDeleteView.as_view(), name='import-delete'),

    path('debts/', DebtsView.as_view(), name='debts'),

    path('debts/<int:pk>/update', DebtUpdateView.as_view(), name='debt-update'),

    path('debts/<int:pk>/delete', DebtDeleteView.as_view(), name='debt-delete'),
]
