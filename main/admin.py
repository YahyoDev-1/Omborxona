from django.contrib import admin
from django.contrib.admin.sites import AdminSite

from .models import Branch, Client, ImportProduct, PayDebt, Product, Sale


def _branch_id(request):
    return request.user.branch_id


class BranchScopedAdmin(admin.ModelAdmin):
    """
    Base admin for every branch-owned model.

    SuperAdmins see and manage every branch. Everyone else only ever sees
    their own branch's rows, can never re-point a record at another branch
    (the `branch` field is forced server-side on save, not just hidden in
    the UI, so tampering with the submitted form can't move data across
    branches), and gets a permission error if they try to view/edit/delete
    another branch's object directly by URL.
    """

    branch_scoped_fk_fields: tuple[str, ...] = ()
    staff_locked_fields: tuple[str, ...] = ('branch',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(branch_id=_branch_id(request))

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            for field in self.staff_locked_fields:
                if field not in readonly:
                    readonly.append(field)
        return readonly

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # `branch` itself is handled by staff_locked_fields (readonly, then
        # forced in save_model) - this only needs to scope the *other*
        # relations (e.g. Sale.product/client) to the employee's branch,
        # so they can't attach a sale to another branch's stock/customer.
        if not request.user.is_superuser and db_field.name in self.branch_scoped_fk_fields:
            kwargs['queryset'] = db_field.related_model.objects.filter(branch_id=_branch_id(request))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.branch_id = _branch_id(request)
        super().save_model(request, obj, form, change)

    def _owns(self, request, obj):
        return obj is None or request.user.is_superuser or obj.branch_id == _branch_id(request)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._owns(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._owns(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._owns(request, obj)


class OwnerAssignedAdmin(BranchScopedAdmin):
    """For models that also carry a `user` (the employee who made the entry)."""

    staff_locked_fields = ('branch', 'user')

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


class ReconciledElsewhereAdmin(BranchScopedAdmin):
    """
    For models whose stock/debt side effects on create/update/delete are
    implemented in the web views (main/views.py), not in a model signal.
    Editing or deleting one of these directly through admin would silently
    desync Product.amount/Client.debt with no way to reconstruct the
    correct value - so all writes are blocked here unconditionally, even
    for SuperAdmins. The data stays visible/searchable (read-only audit
    trail); every change must go through the reconciling view instead.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Branches are the tenant boundary itself, so only a SuperAdmin may manage them."""

    list_display = ('id', 'name')
    search_fields = ('name',)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Product)
class ProductAdmin(BranchScopedAdmin):
    list_display = ('name', 'brand', 'price', 'amount', 'unit', 'branch', 'updated_at')
    list_filter = ('branch', 'unit')
    search_fields = ('name', 'brand')
    readonly_fields = ('updated_at',)


@admin.register(Client)
class ClientAdmin(BranchScopedAdmin):
    list_display = ('name', 'shop_name', 'phone_number', 'debt', 'branch', 'created_at')
    list_filter = ('branch',)
    search_fields = ('name', 'shop_name', 'phone_number')
    readonly_fields = ('created_at',)


@admin.register(Sale)
class SaleAdmin(ReconciledElsewhereAdmin):
    branch_scoped_fk_fields = ('product', 'client')

    list_display = ('product', 'client', 'amount', 'total_price', 'paid_price', 'debt_price', 'branch', 'created_at')
    list_filter = ('branch', 'created_at')
    search_fields = ('product__name', 'client__name')
    readonly_fields = ('created_at',)


@admin.register(ImportProduct)
class ImportProductAdmin(OwnerAssignedAdmin):
    branch_scoped_fk_fields = ('product',)

    list_display = ('product', 'amount', 'buy_price', 'sell_price', 'branch', 'created_at')
    list_filter = ('branch',)
    search_fields = ('product__name',)
    readonly_fields = ('created_at',)

    # Creation stays open: the post_save signal reconciles stock correctly
    # no matter how the row is created. Editing/deleting bypass that
    # signal's delta/guard logic entirely (see ImportUpdateView/
    # ImportDeleteView in main/views.py), so those two stay blocked.
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PayDebt)
class PayDebtAdmin(ReconciledElsewhereAdmin):
    branch_scoped_fk_fields = ('client',)

    list_display = ('client', 'amount', 'branch', 'created_at')
    list_filter = ('branch',)
    search_fields = ('client__name',)
    readonly_fields = ('created_at',)


# Mirrors the same rule enforced on the main app's login view: a non-super
# account with no branch assigned is mis-provisioned and must not be able
# to authenticate anywhere, including the Django admin.
_default_has_permission = AdminSite.has_permission


def _has_permission(self, request):
    if not _default_has_permission(self, request):
        return False
    return request.user.is_superuser or request.user.branch_id is not None


AdminSite.has_permission = _has_permission
