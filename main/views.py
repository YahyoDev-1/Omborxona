from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ExpressionWrapper, F, FloatField
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import *


# Create your views here.

class Sections(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        context = {
            'user': request.user,
        }
        return render(request, 'sections.html', context)


class Products(LoginRequiredMixin, View):
    login_url = 'login'
    def get(self, request):
        products = Product.objects.filter(branch=request.user.branch).annotate(
            total_price=ExpressionWrapper(
                F('price') + F('amount'),
                output_field=FloatField()
            )
        ).order_by('-total_price')
        context = {
            'products': products
        }
        return render(request, 'products.html', context)

    def post(self, request):
        Product.objects.create(
            name=request.POST.get('name'),
            brand=request.POST.get('brand'),
            price=request.POST.get('price'),
            amount=request.POST.get('amount'),
            unit=request.POST.get('unit'),
            updated_at=request.POST.get('updated_at'),
            branch=request.user.branch,
        )
        return redirect('products')


class ProductUpdateView(LoginRequiredMixin, View):
    login_url = 'login'
    def get_object(self, pk):
        return get_object_or_404(Product, pk=pk)

    def get(self, request, pk):
        product = self.get_object(pk)
        context = {
            'product': product,
        }
        return render(request, 'product-update.html', context)

    def post(self, request, pk):
        product = self.get_object(pk)

        product.name = request.POST.get('name')
        product.brand = request.POST.get('brand')
        product.price = request.POST.get('price')
        product.amount = request.POST.get('amount')
        product.unit = request.POST.get('unit')
        product.save()
        return redirect('products')


class ProductDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Product, pk=pk, user=self.request.user)

    def get(self, request, pk):
        product = self.get_object(pk)
        context = {
            'product': product,
        }
        return render(request, 'product-delete.html', context)

    def post(self, request, pk):
        product = self.get_object(pk)
        product.delete()
        return redirect('products')


class ClientsView(LoginRequiredMixin, View):
    def get(self, request):
        clients = Client.objects.filter(branch=request.user.branch)
        context = {
            'clients': clients
        }
        return render(request, 'clients.html', context)

    def post(self, request):
        Client.objects.create(
            name=request.POST.get('name'),
            shop_name=request.POST.get('shop_name'),
            phone_number=request.POST.get('phone_number'),
            address=request.POST.get('address'),
            debt=request.POST.get('debt'),
            branch=request.user.branch,
        )
        return redirect('clients')

    class ClientUpdateView(LoginRequiredMixin, View):
        login_url = 'login'

        def get_object(self, pk):
            return get_object_or_404(Client, pk=pk)

        def get(self, request, pk):
            client = self.get_object(pk)
            context = {
                'client': client,
            }
            return render(request, 'client-update.html', context)

        def post(self, request, pk):
            client = self.get_object(pk)

            client.name = request.POST.get('name')
            client.brand = request.POST.get('brand')
            client.price = request.POST.get('price')
            client.amount = request.POST.get('amount')
            client.unit = request.POST.get('unit')
            client.save()
            return redirect('clients')

    class ClientDeleteView(LoginRequiredMixin, View):
        login_url = 'login'

        def get_object(self, pk):
            return get_object_or_404(Client, pk=pk, user=self.request.user)

        def get(self, request, pk):
            client = self.get_object(pk)
            context = {
                'client': client,
            }
            return render(request, 'client-delete.html', context)

        def post(self, request, pk):
            client = self.get_object(pk)
            client.delete()
            return redirect('clients')
