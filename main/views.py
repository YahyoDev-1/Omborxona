from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import Client, ImportProduct, PayDebt, Product, Sale

ZERO = Decimal('0')
# Mirrors the DecimalField(max_digits=..., decimal_places=...) capacity
# defined in models.py, so we reject an out-of-range value with a clear
# message instead of letting decimal.InvalidOperation crash the request
# when Django tries to quantize it for storage.
MAX_MONEY = Decimal('999999999999.99')
MAX_QUANTITY = Decimal('999999999.999')


def parse_decimal(raw, *, minimum=None, maximum=None):
    """
    Parse a form value into a Decimal, or None if it's blank/missing,
    not a valid number, infinite/NaN, or outside [minimum, maximum].
    Callers treat None uniformly as "invalid input".
    """
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def parse_money(raw, *, minimum=ZERO):
    return parse_decimal(raw, minimum=minimum, maximum=MAX_MONEY)


def parse_quantity(raw, *, minimum=ZERO):
    return parse_decimal(raw, minimum=minimum, maximum=MAX_QUANTITY)


class Sections(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        return render(request, 'sections.html', {'branch': request.user.branch})


class Products(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'products.html'

    def get_products(self, request):
        return Product.objects.filter(branch=request.user.branch).annotate(
            total_price=ExpressionWrapper(
                F('price') * F('amount'),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        ).order_by('-total_price')

    def get(self, request):
        return render(request, self.template_name, {'products': self.get_products(request)})

    def _invalid(self, request, message):
        messages.error(request, message)
        return render(request, self.template_name, {'products': self.get_products(request)})

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        brand = (request.POST.get('brand') or '').strip()
        unit = (request.POST.get('unit') or '').strip()

        if not name:
            return self._invalid(request, "❌ Mahsulot nomi bo'sh bo'la olmaydi!")
        if len(name) < 3:
            return self._invalid(request, "❌ Mahsulot nomi kamida 3 ta belgi bo'lishi kerak!")

        price = parse_money(request.POST.get('price'))
        if price is None or price <= 0:
            return self._invalid(request, "❌ Mahsulot narxi noto'g'ri! Musbat raqam kiriting.")

        amount = parse_quantity(request.POST.get('amount'))
        if amount is None or amount <= 0:
            return self._invalid(request, "❌ Mahsulot miqdori noto'g'ri! Musbat raqam kiriting.")

        if not unit:
            return self._invalid(request, "❌ O'lchov birligi tanlanmagan!")

        existing_product = Product.objects.filter(name__iexact=name, branch=request.user.branch).first()
        if existing_product:
            return self._invalid(
                request,
                f"⚠️ '{name}' nomli mahsulot allaqachon mavjud! "
                f"Miqdor: {existing_product.amount}, Narx: {existing_product.price}"
            )

        product = Product.objects.create(
            name=name,
            brand=brand or None,
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


class ProductUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Product, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'product-update.html', {'product': self.get_object(pk)})

    def post(self, request, pk):
        product = self.get_object(pk)

        name = (request.POST.get('name') or '').strip()
        brand = (request.POST.get('brand') or '').strip()
        unit = (request.POST.get('unit') or '').strip()
        price = parse_money(request.POST.get('price'))
        amount = parse_quantity(request.POST.get('amount'))

        if not name or len(name) < 3:
            messages.error(request, "❌ Mahsulot nomi kamida 3 ta belgi bo'lishi kerak!")
            return render(request, 'product-update.html', {'product': product})
        if price is None or price <= 0:
            messages.error(request, "❌ Mahsulot narxi noto'g'ri! Musbat raqam kiriting.")
            return render(request, 'product-update.html', {'product': product})
        if amount is None:
            messages.error(request, "❌ Mahsulot miqdori noto'g'ri! Manfiy bo'lmagan raqam kiriting.")
            return render(request, 'product-update.html', {'product': product})
        if not unit:
            messages.error(request, "❌ O'lchov birligi tanlanmagan!")
            return render(request, 'product-update.html', {'product': product})

        product.name = name
        product.brand = brand or None
        product.price = price
        product.amount = amount
        product.unit = unit
        product.save()
        messages.success(request, "✅ Mahsulot yangilandi!")
        return redirect('products')


class ProductDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Product, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'product-delete.html', {'product': self.get_object(pk)})

    def post(self, request, pk):
        product = self.get_object(pk)
        try:
            product.delete()
        except ProtectedError:
            messages.error(request, "❌ Bu mahsulotni o'chirib bo'lmaydi: unda sotuvlar tarixi mavjud.")
            return redirect('products')
        return redirect('products')


class ClientsView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'clients.html'

    def get(self, request):
        clients = Client.objects.filter(branch=request.user.branch)
        return render(request, self.template_name, {'clients': clients})

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, "❌ Mijoz ismi bo'sh bo'la olmaydi!")
            return redirect('clients')

        debt_raw = (request.POST.get('debt') or '').strip()
        if debt_raw:
            debt = parse_money(debt_raw)
            if debt is None:
                messages.error(request, "❌ Boshlang'ich qarz noto'g'ri! Manfiy bo'lmagan raqam kiriting.")
                return redirect('clients')
        else:
            debt = ZERO

        Client.objects.create(
            name=name,
            shop_name=(request.POST.get('shop_name') or '').strip() or None,
            phone_number=(request.POST.get('phone_number') or '').strip() or None,
            address=(request.POST.get('address') or '').strip() or None,
            debt=debt,
            branch=request.user.branch,
        )
        messages.success(request, "✅ Mijoz muvaffaqiyatli qo'shildi!")
        return redirect('clients')


class ClientUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Client, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'client-update.html', {'client': self.get_object(pk)})

    def post(self, request, pk):
        client = self.get_object(pk)

        name = (request.POST.get('name') or '').strip()
        debt = parse_money(request.POST.get('debt'))

        if not name:
            messages.error(request, "❌ Mijoz ismi bo'sh bo'la olmaydi!")
            return render(request, 'client-update.html', {'client': client})
        if debt is None:
            messages.error(request, "❌ Qarz miqdori noto'g'ri! Manfiy bo'lmagan raqam kiriting.")
            return render(request, 'client-update.html', {'client': client})

        client.name = name
        client.shop_name = (request.POST.get('shop_name') or '').strip() or None
        client.phone_number = (request.POST.get('phone_number') or '').strip() or None
        client.address = (request.POST.get('address') or '').strip() or None
        client.debt = debt
        client.save()
        messages.success(request, "✅ Mijoz ma'lumotlari yangilandi!")
        return redirect('clients')


class ClientDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Client, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'client-delete.html', {'client': self.get_object(pk)})

    def post(self, request, pk):
        client = self.get_object(pk)
        try:
            client.delete()
        except ProtectedError:
            messages.error(request, "❌ Bu mijozni o'chirib bo'lmaydi: unda sotuvlar yoki to'lovlar tarixi mavjud.")
            return redirect('clients')
        return redirect('clients')


class SalesView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'sales.html'

    def get_context_data(self, request):
        return {
            'sales': Sale.objects.filter(branch=request.user.branch).order_by('-created_at'),
            'products': Product.objects.filter(branch=request.user.branch).order_by('-id'),
            'clients': Client.objects.filter(branch=request.user.branch),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context_data(request))

    def _invalid(self, request, message):
        messages.error(request, message)
        return render(request, self.template_name, self.get_context_data(request))

    def post(self, request):
        user_branch = request.user.branch
        if user_branch is None:
            messages.error(request, "Sizga filial biriktirilmagan. Administratorga murojaat qiling.")
            return redirect('sections')

        amount = parse_quantity(request.POST.get('amount'))
        if amount is None or amount <= 0:
            return self._invalid(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")

        total_price_raw = (request.POST.get('total_price') or '').strip()
        paid_price_raw = (request.POST.get('paid_price') or '').strip()
        debt_price_raw = (request.POST.get('debt_price') or '').strip()

        total_price = None
        if total_price_raw:
            total_price = parse_money(total_price_raw)
            if total_price is None:
                return self._invalid(request, "❌ Umumiy narx noto'g'ri! Manfiy bo'lmagan raqam kiriting.")

        paid_price = ZERO
        if paid_price_raw:
            paid_price = parse_money(paid_price_raw)
            if paid_price is None:
                return self._invalid(request, "❌ To'langan narx noto'g'ri! Manfiy bo'lmagan raqam kiriting.")

        debt_price = ZERO
        if debt_price_raw:
            debt_price = parse_money(debt_price_raw)
            if debt_price is None:
                return self._invalid(request, "❌ Qarz narxi noto'g'ri! Manfiy bo'lmagan raqam kiriting.")

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), pk=request.POST.get('product_id'), branch=user_branch
            )
            client = get_object_or_404(
                Client.objects.select_for_update(), pk=request.POST.get('client_id'), branch=user_branch
            )

            if product.amount < amount:
                return self._invalid(
                    request,
                    f"❌ Omborda yetarli mahsulot yo'q! Qoldiq: {product.amount}, So'ralgan: {amount}"
                )

            if total_price is None:
                total_price = product.price * amount

            if not paid_price_raw and not debt_price_raw:
                paid_price = total_price
                debt_price = ZERO
            elif paid_price_raw and not debt_price_raw:
                debt_price = total_price - paid_price
            elif not paid_price_raw and debt_price_raw:
                paid_price = total_price - debt_price

            if paid_price < 0 or debt_price < 0:
                return self._invalid(
                    request,
                    "❌ To'langan yoki qarz summasi umumiy narxdan oshib ketmasligi kerak!"
                )

            if paid_price + debt_price != total_price:
                return self._invalid(
                    request,
                    f"❌ XATOLIK: To'langan summa ({paid_price}) + Qarz ({debt_price}) = "
                    f"{paid_price + debt_price}, lekin Umumiy narx {total_price}. Ularni tekshiring!"
                )

            Sale.objects.create(
                product=product,
                client=client,
                amount=amount,
                description=request.POST.get('description', ''),
                total_price=total_price,
                paid_price=paid_price,
                debt_price=debt_price,
                user=request.user,
                branch=user_branch,
            )

            product.amount -= amount
            product.save()

            client.debt += debt_price
            client.save()

        messages.success(
            request,
            f"✅ Sotish muvaffaqiyatli! "
            f"Umumiy narx: {total_price}, To'langan: {paid_price}, Qarz: {debt_price}"
        )
        return redirect('sales')


class SaleUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Sale, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'sale-update.html', {'sale': self.get_object(pk)})

    def post(self, request, pk):
        amount = parse_quantity(request.POST.get('amount'))
        total_price = parse_money(request.POST.get('total_price'))
        paid_price = parse_money(request.POST.get('paid_price'))
        debt_price = parse_money(request.POST.get('debt_price'))

        if amount is None or amount <= 0:
            messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
            return render(request, 'sale-update.html', {'sale': self.get_object(pk)})
        if None in (total_price, paid_price, debt_price):
            messages.error(request, "❌ Narxlar noto'g'ri! Manfiy bo'lmagan raqamlar kiriting.")
            return render(request, 'sale-update.html', {'sale': self.get_object(pk)})
        if paid_price + debt_price != total_price:
            messages.error(
                request,
                f"❌ To'langan ({paid_price}) + Qarz ({debt_price}) yig'indisi "
                f"Umumiy narxga ({total_price}) teng emas!"
            )
            return render(request, 'sale-update.html', {'sale': self.get_object(pk)})

        with transaction.atomic():
            sale = get_object_or_404(
                Sale.objects.select_for_update(), pk=pk, branch=request.user.branch
            )
            product = Product.objects.select_for_update().get(pk=sale.product_id)
            client = Client.objects.select_for_update().get(pk=sale.client_id)

            # Reconcile the stock this sale ties up: a bigger amount consumes
            # more stock, a smaller amount gives some back.
            amount_delta = amount - sale.amount
            if product.amount < amount_delta:
                messages.error(
                    request,
                    f"❌ Omborda yetarli mahsulot yo'q! Qoldiq: {product.amount}, "
                    f"qo'shimcha kerak: {amount_delta}"
                )
                return render(request, 'sale-update.html', {'sale': sale})

            # Reconcile the client's debt the same way.
            debt_delta = debt_price - sale.debt_price
            new_client_debt = client.debt + debt_delta
            if new_client_debt < 0:
                messages.error(
                    request,
                    "❌ Bu o'zgarish mijozning qarzini manfiy qiladi - to'lovlarni tekshiring!"
                )
                return render(request, 'sale-update.html', {'sale': sale})

            product.amount -= amount_delta
            product.save()

            client.debt = new_client_debt
            client.save()

            sale.amount = amount
            sale.description = request.POST.get('description', sale.description)
            sale.total_price = total_price
            sale.paid_price = paid_price
            sale.debt_price = debt_price
            sale.save()

        messages.success(request, "✅ Sotuv muvaffaqiyatli yangilandi!")
        return redirect('sales')


class SaleDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(Sale, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'sale-delete.html', {'sale': self.get_object(pk)})

    def post(self, request, pk):
        with transaction.atomic():
            sale = get_object_or_404(
                Sale.objects.select_for_update(), pk=pk, branch=request.user.branch
            )
            product = Product.objects.select_for_update().get(pk=sale.product_id)
            client = Client.objects.select_for_update().get(pk=sale.client_id)

            # Reverse the stock/debt effects this sale had - otherwise
            # deleting it leaves both permanently desynced from reality.
            product.amount += sale.amount
            product.save()

            client.debt = max(ZERO, client.debt - sale.debt_price)
            client.save()

            sale.delete()

        messages.success(request, "✅ Sotuv o'chirildi, ombor va qarz qoldiqlari tiklandi.")
        return redirect('sales')


class ImportsView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'imports.html'

    def get_context_data(self, request):
        return {'products': Product.objects.filter(branch=request.user.branch).order_by('-id')}

    def get(self, request):
        return render(request, self.template_name, self.get_context_data(request))

    def post(self, request):
        user_branch = request.user.branch
        if user_branch is None:
            messages.error(request, "Sizga filial biriktirilmagan!")
            return redirect('imports')

        amount = parse_quantity(request.POST.get('amount'))
        if amount is None or amount <= 0:
            messages.error(request, "Miqdor 0 dan katta bo'lishi kerak!")
            return redirect('imports')

        buy_price = parse_money(request.POST.get('buy_price'))
        if buy_price is None:
            messages.error(request, "Olish narxi noto'g'ri! Manfiy bo'lmagan raqam kiriting.")
            return redirect('imports')

        sell_price_raw = (request.POST.get('sell_price') or '').strip()
        if sell_price_raw:
            sell_price = parse_money(sell_price_raw)
            if sell_price is None:
                messages.error(request, "Sotish narxi noto'g'ri! Manfiy bo'lmagan raqam kiriting.")
                return redirect('imports')
        else:
            sell_price = buy_price

        # Validate the product belongs to this branch before attaching stock
        # to it - an unscoped lookup would let stock be imported into
        # another branch's product by guessing its id.
        product = get_object_or_404(Product, pk=request.POST.get('product_id'), branch=user_branch)

        with transaction.atomic():
            ImportProduct.objects.create(
                product=product,
                amount=amount,
                buy_price=buy_price,
                sell_price=sell_price,
                description=request.POST.get('description', ''),
                user=request.user,
                branch=user_branch,
            )

        messages.success(request, "Kirim muvaffaqiyatli amalga oshirildi!")
        return redirect('imports')


class ImportUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(ImportProduct, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'import-update.html', {'import_product': self.get_object(pk)})

    def post(self, request, pk):
        amount = parse_quantity(request.POST.get('amount'))
        buy_price = parse_money(request.POST.get('buy_price'))
        sell_price = parse_money(request.POST.get('sell_price'))

        if amount is None or amount <= 0:
            messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
            return render(request, 'import-update.html', {'import_product': self.get_object(pk)})
        if buy_price is None or sell_price is None:
            messages.error(request, "❌ Narxlar noto'g'ri! Manfiy bo'lmagan raqamlar kiriting.")
            return render(request, 'import-update.html', {'import_product': self.get_object(pk)})

        with transaction.atomic():
            import_product = get_object_or_404(
                ImportProduct.objects.select_for_update(), pk=pk, branch=request.user.branch
            )

            if import_product.product_id is None:
                messages.error(request, "❌ Bu kirim endi hech qanday mahsulotga bog'lanmagan.")
                return redirect('imports')

            product = Product.objects.select_for_update().get(pk=import_product.product_id)

            # This import originally added `import_product.amount` to stock;
            # reconcile only the difference against the new amount.
            amount_delta = amount - import_product.amount
            if product.amount + amount_delta < 0:
                messages.error(
                    request,
                    "❌ Ombordagi qoldiq bu o'zgarishni qo'llab-quvvatlay olmaydi "
                    "(mahsulotning bir qismi allaqachon sotilgan bo'lishi mumkin)."
                )
                return render(request, 'import-update.html', {'import_product': import_product})

            product.amount += amount_delta
            product.price = sell_price
            product.save()

            import_product.amount = amount
            import_product.buy_price = buy_price
            import_product.sell_price = sell_price
            import_product.description = request.POST.get('description', import_product.description)
            import_product.save()

        messages.success(request, "✅ Kirim muvaffaqiyatli yangilandi!")
        return redirect('imports')


class ImportDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(ImportProduct, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'import-delete.html', {'import_product': self.get_object(pk)})

    def post(self, request, pk):
        with transaction.atomic():
            import_product = get_object_or_404(
                ImportProduct.objects.select_for_update(), pk=pk, branch=request.user.branch
            )

            if import_product.product_id is not None:
                product = Product.objects.select_for_update().get(pk=import_product.product_id)
                if product.amount < import_product.amount:
                    messages.error(
                        request,
                        "❌ Bu kirimni o'chirib bo'lmaydi: mahsulotning bir qismi allaqachon "
                        "sotilgan, ombor qoldig'i manfiy bo'lib qoladi."
                    )
                    return redirect('imports')
                product.amount -= import_product.amount
                product.save()

            import_product.delete()

        messages.success(request, "✅ Kirim o'chirildi, ombor qoldig'i tiklandi.")
        return redirect('imports')


class DebtsView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'debts.html'

    def get_context_data(self, request):
        return {
            'debts': PayDebt.objects.filter(branch=request.user.branch).order_by('-id'),
            'clients': Client.objects.filter(branch=request.user.branch).order_by('-id'),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context_data(request))

    def post(self, request):
        user_branch = request.user.branch
        if user_branch is None:
            messages.error(request, "Sizga filial biriktirilmagan!")
            return redirect('debts')

        amount = parse_money(request.POST.get('amount'))
        if amount is None or amount <= 0:
            messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
            return redirect('debts')

        with transaction.atomic():
            client = get_object_or_404(
                Client.objects.select_for_update(), pk=request.POST.get('client_id'), branch=user_branch
            )

            if amount > client.debt:
                messages.error(
                    request,
                    f"❌ To'lov miqdori mijoz qarzidan katta bo'lishi mumkin emas! "
                    f"Qarz: {client.debt}, kiritilgan: {amount}"
                )
                return redirect('debts')

            PayDebt.objects.create(
                client=client,
                amount=amount,
                description=request.POST.get('description', ''),
                user=request.user,
                branch=user_branch,
            )

            client.debt -= amount
            client.save()

        messages.success(request, "✅ To'lov muvaffaqiyatli qabul qilindi!")
        return redirect('debts')


class DebtUpdateView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(PayDebt, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'debt-update.html', {'debt': self.get_object(pk)})

    def post(self, request, pk):
        amount = parse_money(request.POST.get('amount'))
        if amount is None or amount <= 0:
            messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
            return render(request, 'debt-update.html', {'debt': self.get_object(pk)})

        with transaction.atomic():
            debt = get_object_or_404(
                PayDebt.objects.select_for_update(), pk=pk, branch=request.user.branch
            )
            client = Client.objects.select_for_update().get(pk=debt.client_id)

            # Undo the old payment amount, then apply the new one.
            new_client_debt = client.debt + debt.amount - amount
            if new_client_debt < 0:
                messages.error(
                    request,
                    f"❌ Bu o'zgarish mijoz qarzini manfiy qiladi! Joriy qarz: {client.debt}"
                )
                return render(request, 'debt-update.html', {'debt': debt})

            client.debt = new_client_debt
            client.save()

            debt.amount = amount
            debt.description = request.POST.get('description', debt.description)
            debt.save()

        messages.success(request, "✅ To'lov muvaffaqiyatli yangilandi!")
        return redirect('debts')


class DebtDeleteView(LoginRequiredMixin, View):
    login_url = 'login'

    def get_object(self, pk):
        return get_object_or_404(PayDebt, pk=pk, branch=self.request.user.branch)

    def get(self, request, pk):
        return render(request, 'debt-delete.html', {'debt': self.get_object(pk)})

    def post(self, request, pk):
        with transaction.atomic():
            debt = get_object_or_404(
                PayDebt.objects.select_for_update(), pk=pk, branch=request.user.branch
            )
            client = Client.objects.select_for_update().get(pk=debt.client_id)

            # Deleting a payment means it never happened - restore the debt it paid off.
            client.debt += debt.amount
            client.save()

            debt.delete()

        messages.success(request, "✅ To'lov o'chirildi, mijoz qarzi tiklandi.")
        return redirect('debts')
