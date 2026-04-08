from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ExpressionWrapper, F, FloatField
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import *
from django.contrib import messages


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
    template_name = 'products.html'

    def get(self, request):
        products = Product.objects.filter(branch=request.user.branch).annotate(
            total_price=ExpressionWrapper(
                F('price') * F('amount'),  # ✅ XATO TUZATILDI: + o'rniga * (ko'paytirish)
                output_field=FloatField()
            )
        ).order_by('-total_price')

        context = {
            'products': products
        }
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            # ✅ STEP 1: Ma'lumotlarni oling
            name = request.POST.get('name', '').strip()
            brand = request.POST.get('brand', '').strip()
            price_input = request.POST.get('price', '').strip()
            amount_input = request.POST.get('amount', '').strip()
            unit = request.POST.get('unit', '').strip()

            # ✅ STEP 2: Mahsulot nomini tekshiring
            if not name:
                messages.error(request, "❌ Mahsulot nomi bo'sh bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            if len(name) < 3:
                messages.error(request, "❌ Mahsulot nomi kamida 3 ta belgi bo'lishi kerak!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            # ✅ STEP 3: Mahsulot narxini tekshiring
            if not price_input:
                messages.error(request, "❌ Mahsulot narxi bo'sh bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            try:
                price = float(price_input)
            except ValueError:
                messages.error(request, "❌ Mahsulot narxi noto'g'ri! Raqam kiriting.")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            if price < 0:
                messages.error(request, "❌ Mahsulot narxi manfiy bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            if price == 0:
                messages.error(request, "❌ Mahsulot narxi 0 bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            # ✅ STEP 4: Mahsulot miqdorini tekshiring
            if not amount_input:
                messages.error(request, "❌ Mahsulot miqdori bo'sh bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            try:
                amount = float(amount_input)
            except ValueError:
                messages.error(request, "❌ Mahsulot miqdori noto'g'ri! Raqam kiriting.")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            if amount < 0:
                messages.error(request, "❌ Mahsulot miqdori manfiy bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            if amount == 0:
                messages.error(request, "❌ Mahsulot miqdori 0 bo'la olmaydi!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            # ✅ STEP 5: Bir xil mahsulot tekshirish (Ixtiyoriy)
            existing_product = Product.objects.filter(
                name__iexact=name,  # Case-insensitive qidirish
                branch=request.user.branch
            ).first()

            if existing_product:
                messages.warning(
                    request,
                    f"⚠️ '{name}' nomli mahsulot allaqachon mavjud! "
                    f"Miqdor: {existing_product.amount}, Narx: {existing_product.price}"
                )
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            # ✅ STEP 6: Unit tekshiring
            if not unit:
                messages.error(request, "❌ O'lchov birligi tanlanmagan!")
                products = self.get_products(request)
                context = {'products': products}
                return render(request, self.template_name, context)

            # ✅ STEP 7: MAHSULOT QOSHISH
            product = Product.objects.create(
                name=name,
                brand=brand if brand else None,  # Bo'sh bo'lsa None
                price=price,
                amount=amount,
                unit=unit,
                branch=request.user.branch,
            )

            messages.success(
                request,
                f"✅ Mahsulot muvaffaqiyatli qo'shildi! "
                f"Nomi: {product.name}, Narx: {product.price}, Miqdor: {product.amount}"
            )
            return redirect('products')

        except Exception as e:
            messages.error(request, f"❌ Xatolik yuz berdi: {str(e)}")
            print(f"❌ Exception: {e}")
            products = self.get_products(request)
            context = {'products': products}
            return render(request, self.template_name, context)

    def get_products(self, request):
        """Mahsulotlarni qaytaradi"""
        return Product.objects.filter(branch=request.user.branch).annotate(
            total_price=ExpressionWrapper(
                F('price') * F('amount'),
                output_field=FloatField()
            )
        ).order_by('-total_price')


class ProductUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Product, pk=pk, branch=self.request.user.branch)

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
        return get_object_or_404(Product, pk=pk, branch=self.request.user.branch)

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
        return get_object_or_404(Client, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        client = self.get_object(pk)
        context = {
            'client': client,
        }
        return render(request, 'client-update.html', context)

    def post(self, request, pk):
        client = self.get_object(pk)

        client.name = request.POST.get('name')
        client.shop_name = request.POST.get('shop_name')
        client.phone_number = request.POST.get('phone_number')
        client.address = request.POST.get('address')
        client.debt = request.POST.get('debt')
        client.save()
        return redirect('clients')


class ClientDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Client, pk=pk, branch=self.request.user.branch)

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


class SalesView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'sales.html'

    def get_context_data(self, request):
        """Context data'sini qaytaradi"""
        return {
            'sales': Sale.objects.filter(branch=request.user.branch).order_by('-created_at'),
            'products': Product.objects.filter(branch=request.user.branch).order_by('-id'),
            'clients': Client.objects.filter(branch=request.user.branch),
        }

    def get(self, request):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            # ✅ Mahsulot va Mijozni oling
            product = get_object_or_404(
                Product,
                pk=request.POST.get('product_id'),
                branch=request.user.branch
            )
            client = get_object_or_404(
                Client,
                pk=request.POST.get('client_id'),
                branch=request.user.branch
            )

            # ✅ STEP 1: Miqdorni oling va tekshiring
            try:
                amount = float(request.POST.get('amount', 0))
                if amount <= 0:
                    messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
                    context = self.get_context_data(request)
                    return render(request, self.template_name, context)
            except (ValueError, TypeError):
                messages.error(request, "❌ Miqdor noto'g'ri! Raqam kiriting.")
                context = self.get_context_data(request)
                return render(request, self.template_name, context)

            # ✅ STEP 2: Ombordagi mahsulot soni tekshiring
            if product.amount < amount:
                messages.error(
                    request,
                    f"❌ Omborda yetarli mahsulot yo'q! Qoldiq: {product.amount}, So'ralgan: {amount}"
                )
                context = self.get_context_data(request)
                return render(request, self.template_name, context)

            # ✅ STEP 3: total_price ni hisoblang (agar bo'sh bo'lsa)
            total_price_input = request.POST.get('total_price', '').strip()

            if total_price_input:  # Agar kiritilgan bo'lsa
                try:
                    total_price = float(total_price_input)
                    if total_price < 0:
                        messages.error(request, "❌ Umumiy narx manfiy bo'la olmaydi!")
                        context = self.get_context_data(request)
                        return render(request, self.template_name, context)
                except (ValueError, TypeError):
                    messages.error(request, "❌ Umumiy narx noto'g'ri! Raqam kiriting.")
                    context = self.get_context_data(request)
                    return render(request, self.template_name, context)
            else:  # ✅ Bo'sh bo'lsa - avtomatik hisobla
                total_price = product.price * amount
                print(f"✅ total_price avtomatik hisoblandi: {total_price}")

            # ✅ STEP 4: paid_price va debt_price ni oling
            paid_price_input = request.POST.get('paid_price', '').strip()
            debt_price_input = request.POST.get('debt_price', '').strip()

            # paid_price'ni o'zgartirishga o'rnatilgan
            if paid_price_input:
                try:
                    paid_price = float(paid_price_input)
                    if paid_price < 0:
                        messages.error(request, "❌ To'langan narx manfiy bo'la olmaydi!")
                        context = self.get_context_data(request)
                        return render(request, self.template_name, context)
                except (ValueError, TypeError):
                    messages.error(request, "❌ To'langan narx noto'g'ri! Raqam kiriting.")
                    context = self.get_context_data(request)
                    return render(request, self.template_name, context)
            else:
                paid_price = 0

            # debt_price'ni o'zgartirishga o'rnatilgan
            if debt_price_input:
                try:
                    debt_price = float(debt_price_input)
                    if debt_price < 0:
                        messages.error(request, "❌ Qarz narxi manfiy bo'la olmaydi!")
                        context = self.get_context_data(request)
                        return render(request, self.template_name, context)
                except (ValueError, TypeError):
                    messages.error(request, "❌ Qarz narxi noto'g'ri! Raqam kiriting.")
                    context = self.get_context_data(request)
                    return render(request, self.template_name, context)
            else:
                debt_price = 0

            # ✅ STEP 5: Avtomatik hisoblash logikasi
            # Hech qaysi maydon kiritilmagan bo'lsa
            if not paid_price_input and not debt_price_input:
                paid_price = total_price  # Barchasi to'landi
                debt_price = 0
                print(f"✅ Hech qaysi maydon bo'sh -> paid_price={paid_price}, debt_price={debt_price}")

            # Faqat paid_price kiritilgan bo'lsa
            elif paid_price_input and not debt_price_input:
                debt_price = total_price - paid_price
                print(f"✅ Faqat paid_price -> debt_price avtomatik={debt_price}")

            # Faqat debt_price kiritilgan bo'lsa
            elif not paid_price_input and debt_price_input:
                paid_price = total_price - debt_price
                print(f"✅ Faqat debt_price -> paid_price avtomatik={paid_price}")

            # Ikkalasi kiritilgan bo'lsa - tekshirish kerak
            else:
                print(f"✅ Ikkalasi kiritilgan: paid_price={paid_price}, debt_price={debt_price}")

            # ✅ STEP 6: Yig'indini tekshiring
            yigindi = round(paid_price + debt_price, 2)
            total = round(total_price, 2)

            if yigindi != total:
                messages.error(
                    request,
                    f"❌ XATOLIK: To'langan summa ({paid_price}) + Qarz ({debt_price}) = {yigindi}, "
                    f"lekin Umumiy narx {total}. Ularni tekshiring!"
                )
                context = self.get_context_data(request)
                return render(request, self.template_name, context)

            # ✅ STEP 7: SOTISH QO'SHISH
            Sale.objects.create(
                product=product,
                client=client,
                amount=amount,
                description=request.POST.get('description', ''),
                total_price=total_price,
                paid_price=paid_price,
                debt_price=debt_price,
                user=request.user,
                branch=request.user.branch,
            )

            # ✅ STEP 8: Mahsulot miqdorini kamayting
            product.amount -= amount
            product.save()
            print(f"✅ Mahsulot miqdori kamaytirildi: {product.amount}")

            # ✅ STEP 9: Mijozning qarzini oshiring
            client.debt += debt_price
            client.save()
            print(f"✅ Mijozning qarzi oshirildi: {client.debt}")

            messages.success(
                request,
                f"✅ Sotish muvaffaqiyatli! "
                f"Umumiy narx: {total_price}, To'langan: {paid_price}, Qarz: {debt_price}"
            )
            return redirect('sales')

        except Exception as e:
            messages.error(request, f"❌ Kutilmagan xatolik: {str(e)}")
            print(f"❌ Exception: {e}")
            context = self.get_context_data(request)
            return render(request, self.template_name, context)


class SaleUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Sale, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        sale = self.get_object(pk)
        context = {
            'sale': sale,
        }
        return render(request, 'sale-update.html', context)

    def post(self, request, pk):
        sale = self.get_object(pk)
        sale.product.name = request.POST.get('name')
        sale.client.name = request.POST.get('client')
        sale.description = request.POST.get('description')
        sale.total_price = request.POST.get('total_price')
        sale.paid_price = request.POST.get('paid_price')
        sale.debt_price = request.POST.get('debt_price')
        sale.save()
        return redirect('sales')


class ImportsView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        imports_list = ImportProduct.objects.all().order_by('-created_at')
        products = Product.objects.all().order_by('-updated_at')
        context = {
            'imports_list': imports_list,
        }

        return render(request, 'imports.html', context)


class DebtsView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        return render(request, 'debts.html')
