from decimal import Decimal

from django.test import TestCase

from users.models import User

from .models import Branch, Client, ImportProduct, PayDebt, Product, Sale


class ReconciliationTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name='Main')
        self.user = User.objects.create_user(username='cashier', password='pass12345', branch=self.branch)
        self.client.force_login(self.user)

        self.product = Product.objects.create(
            name='Sugar', price=Decimal('10.00'), amount=Decimal('100.000'), unit='kg', branch=self.branch,
        )
        self.customer = Client.objects.create(name='Ali', branch=self.branch)

    def test_sale_create_reduces_stock_and_increases_debt(self):
        resp = self.client.post('/sales/', {
            'product_id': self.product.pk,
            'client_id': self.customer.pk,
            'amount': '10',
            'paid_price': '60',
        })
        self.assertRedirects(resp, '/sales/')

        self.product.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('90.000'))
        self.assertEqual(self.customer.debt, Decimal('40.00'))

        sale = Sale.objects.get()
        self.assertEqual(sale.total_price, Decimal('100.00'))
        self.assertEqual(sale.debt_price, Decimal('40.00'))

    def test_sale_overselling_is_rejected(self):
        resp = self.client.post('/sales/', {
            'product_id': self.product.pk,
            'client_id': self.customer.pk,
            'amount': '1000',
        })
        self.assertEqual(resp.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('100.000'))
        self.assertEqual(Sale.objects.count(), 0)

    def test_sale_delete_restores_stock_and_debt(self):
        sale = Sale.objects.create(
            product=self.product, client=self.customer, amount=Decimal('10'),
            total_price=Decimal('100.00'), paid_price=Decimal('60.00'), debt_price=Decimal('40.00'),
            user=self.user, branch=self.branch,
        )
        self.product.amount -= sale.amount
        self.product.save()
        self.customer.debt += sale.debt_price
        self.customer.save()

        resp = self.client.post(f'/sales/{sale.pk}/delete')
        self.assertRedirects(resp, '/sales/')

        self.product.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('100.000'))
        self.assertEqual(self.customer.debt, Decimal('0.00'))
        self.assertFalse(Sale.objects.exists())

    def test_sale_update_reconciles_amount_and_debt_delta(self):
        sale = Sale.objects.create(
            product=self.product, client=self.customer, amount=Decimal('10'),
            total_price=Decimal('100.00'), paid_price=Decimal('60.00'), debt_price=Decimal('40.00'),
            user=self.user, branch=self.branch,
        )
        self.product.amount -= sale.amount
        self.product.save()
        self.customer.debt += sale.debt_price
        self.customer.save()

        resp = self.client.post(f'/sales/{sale.pk}/update', {
            'amount': '15',
            'total_price': '150.00',
            'paid_price': '60.00',
            'debt_price': '90.00',
        })
        self.assertRedirects(resp, '/sales/')

        self.product.refresh_from_db()
        self.customer.refresh_from_db()
        # started at 100, sold 10 (90), update now sells 15 total -> 85 left
        self.assertEqual(self.product.amount, Decimal('85.000'))
        # debt delta: 90 - 40 = +50 on top of the 40 already applied
        self.assertEqual(self.customer.debt, Decimal('90.00'))

    def test_product_delete_blocked_when_sales_exist(self):
        Sale.objects.create(
            product=self.product, client=self.customer, amount=Decimal('1'),
            total_price=Decimal('10.00'), paid_price=Decimal('10.00'), user=self.user, branch=self.branch,
        )
        resp = self.client.post(f'/products/{self.product.pk}/delete')
        self.assertRedirects(resp, '/products/')
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_import_create_increases_stock_via_signal(self):
        resp = self.client.post('/imports/', {
            'product_id': self.product.pk,
            'amount': '20',
            'buy_price': '5',
        })
        self.assertRedirects(resp, '/imports/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('120.000'))
        self.assertEqual(self.product.price, Decimal('5.00'))

    def test_import_delete_reverses_stock_and_is_blocked_if_oversold(self):
        imp = ImportProduct.objects.create(
            product=self.product, amount=Decimal('20'), buy_price=Decimal('5'), sell_price=Decimal('8'),
            user=self.user, branch=self.branch,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('120.000'))

        # Sell almost everything so reversing the import would go negative.
        self.product.amount = Decimal('5.000')
        self.product.save()

        resp = self.client.post(f'/imports/{imp.pk}/delete')
        self.assertRedirects(resp, '/imports/')
        self.assertTrue(ImportProduct.objects.filter(pk=imp.pk).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('5.000'))

        # Now with enough stock, deletion should succeed and reverse it.
        self.product.amount = Decimal('120.000')
        self.product.save()
        resp = self.client.post(f'/imports/{imp.pk}/delete')
        self.assertRedirects(resp, '/imports/')
        self.assertFalse(ImportProduct.objects.filter(pk=imp.pk).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.amount, Decimal('100.000'))

    def test_debt_payment_flow(self):
        self.customer.debt = Decimal('50.00')
        self.customer.save()

        # Overpaying is rejected.
        resp = self.client.post('/debts/', {'client_id': self.customer.pk, 'amount': '100'})
        self.assertRedirects(resp, '/debts/')
        self.assertEqual(PayDebt.objects.count(), 0)

        resp = self.client.post('/debts/', {'client_id': self.customer.pk, 'amount': '30'})
        self.assertRedirects(resp, '/debts/')
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.debt, Decimal('20.00'))
        payment = PayDebt.objects.get()

        resp = self.client.post(f'/debts/{payment.pk}/delete')
        self.assertRedirects(resp, '/debts/')
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.debt, Decimal('50.00'))
        self.assertFalse(PayDebt.objects.exists())


class LoginBranchGateTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name='Main')

    def test_non_superuser_without_branch_cannot_login(self):
        User.objects.create_user(username='nobranch', password='pass12345')
        resp = self.client.post('/auth/login/', {'username': 'nobranch', 'password': 'pass12345'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_superuser_without_branch_can_login(self):
        User.objects.create_superuser(username='root', password='pass12345', email='root@example.com')
        resp = self.client.post('/auth/login/', {'username': 'root', 'password': 'pass12345'})
        self.assertRedirects(resp, '/')

    def test_user_with_branch_can_login(self):
        User.objects.create_user(username='cashier', password='pass12345', branch=self.branch)
        resp = self.client.post('/auth/login/', {'username': 'cashier', 'password': 'pass12345'})
        self.assertRedirects(resp, '/')
