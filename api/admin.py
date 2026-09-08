from django.contrib import admin
from .models import (
    Product,
    ProductPhoto,
    HomeSection,
    SiteContent,
    Settings,
    Sale,
    PurchaseOrder,
    PurchaseItem,
)


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "cost", "profit", "category", "featured", "active", "position"]
    list_filter = ["category", "featured", "active"]
    list_editable = ["price", "featured"]
    search_fields = ["name"]
    inlines = [ProductPhotoInline]
    ordering = ["position", "-created_at"]


@admin.register(ProductPhoto)
class ProductPhotoAdmin(admin.ModelAdmin):
    list_display = ["product", "position", "created_at"]
    list_filter = ["product"]


@admin.register(HomeSection)
class HomeSectionAdmin(admin.ModelAdmin):
    list_display = ["key", "title", "mode", "cat", "on", "position"]
    list_editable = ["title", "on", "position"]


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ["id"]

    def has_add_permission(self, request):
        return not SiteContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "whatsapp", "margin"]

    def has_add_permission(self, request):
        return not Settings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ["product_name", "unit_price", "qty", "profit", "date"]
    list_filter = ["date", "product"]
    search_fields = ["product_name"]
    readonly_fields = ["profit", "created_at"]
    ordering = ["-date", "-created_at"]


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["supplier", "date", "shipping_cost", "margin", "created_at"]
    list_filter = ["date"]
    search_fields = ["supplier"]
    inlines = [PurchaseItemInline]
    ordering = ["-date", "-created_at"]
