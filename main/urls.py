from django.urls import path

from .views import *

urlpatterns = [
    path('sections/', Sections.as_view(), name='sections'),

    path('products/', Products.as_view(), name='products'),

    path('products/<int:pk>/update', ProductUpdateView.as_view(), name='product-update'),

    path('products/<int:pk>/delete', ProductDeleteView.as_view(), name='product-delete'),

    path('clients/', ClientsView.as_view(), name='clients'),
]