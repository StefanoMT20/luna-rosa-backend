import uuid

from rest_framework import serializers
from django.utils import timezone
from .models import (
    Product,
    ProductPhoto,
    HomeSection,
    SiteContent,
    Settings,
    Sale,
    PurchaseOrder,
    PurchaseItem,
    SIZES,
    COLORS,
)


class ProductPhotoSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductPhoto
        fields = ["id", "image", "position"]

    def get_image(self, obj):
        request = self.context.get("request")
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductSerializer(serializers.ModelSerializer):
    # El front espera photos: string[] (URLs absolutas), no objetos.
    photos = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "cost",
            "category",
            "sizes",
            "colors",
            "featured",
            "active",
            "position",
            "photos",
            "profit",
        ]

    def get_profit(self, obj):
        return obj.profit

    def get_photos(self, obj):
        request = self.context.get("request")
        urls = []
        for photo in obj.photos.all():
            if not photo.image:
                continue
            url = photo.image.url
            urls.append(request.build_absolute_uri(url) if request else url)
        return urls

    def validate_sizes(self, value):
        if not value:
            raise serializers.ValidationError("At least one size must be selected.")
        if not all(s in SIZES for s in value):
            raise serializers.ValidationError(f"Invalid sizes. Must be from: {SIZES}")
        return value

    def validate_colors(self, value):
        if not value:
            raise serializers.ValidationError("At least one color must be selected.")
        if not all(c in COLORS for c in value):
            raise serializers.ValidationError(f"Invalid colors. Must be from: {COLORS}")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate(self, data):
        if data.get("cost") and data.get("price"):
            if data["cost"] >= data["price"]:
                self.fields["cost"].error_messages["invalid"] = (
                    "Cost must be less than price."
                )
        return data


class ProductPhotoUploadSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()

    class Meta:
        model = ProductPhoto
        fields = ["image", "position"]

    def validate_image(self, value):
        max_size = 8 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image size must not exceed 8MB.")

        if value.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise serializers.ValidationError(
                "Only JPEG, PNG, and WebP images are allowed."
            )

        return value


class HomeSectionSerializer(serializers.ModelSerializer):
    # En el front el campo se llama 'order'; en la base sigue siendo 'position'.
    order = serializers.IntegerField(source="position", required=False)

    class Meta:
        model = HomeSection
        fields = ["key", "title", "mode", "cat", "on", "order"]


class HomeSectionProductSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    products = ProductSerializer(many=True, read_only=True)


class SiteContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteContent
        fields = ["hero_title", "hero_sub", "ship_title", "ship_sub", "closing"]


class SiteContentWithSectionsSerializer(serializers.Serializer):
    hero_title = serializers.CharField()
    hero_sub = serializers.CharField()
    ship_title = serializers.CharField()
    ship_sub = serializers.CharField()
    closing = serializers.CharField()
    sections = HomeSectionProductSerializer(many=True)


class SettingsPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ["whatsapp"]


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ["whatsapp", "margin"]


class SaleSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Sale
        fields = ["id", "product_id", "product_name", "unit_price", "qty", "date", "profit", "created_at"]
        read_only_fields = ["id", "profit", "created_at"]

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Sale date cannot be in the future.")
        return value

    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0.")
        return value

    def validate_qty(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def create(self, validated_data):
        product = validated_data.get("product_id")
        if product:
            validated_data["product"] = product
            validated_data["product_name"] = product.name
            del validated_data["product_id"]
        else:
            validated_data["product_name"] = validated_data.get("product_name", "Unknown")

        sale = Sale(**validated_data)
        sale.profit = sale.calculate_profit()
        sale.save()
        return sale


class SaleListSerializer(serializers.ModelSerializer):
    # El front espera productId; la prenda puede haberse borrado (SET_NULL),
    # en cuyo caso mandamos "" y queda product_name como copia historica.
    product_id = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "product_id",
            "product_name",
            "unit_price",
            "qty",
            "profit",
            "date",
            "created_at",
        ]
        read_only_fields = ["id", "profit", "created_at"]

    def get_product_id(self, obj):
        return str(obj.product_id) if obj.product_id else ""


class PurchaseItemSerializer(serializers.ModelSerializer):
    # El id lo genera el front para poder referenciar el item de inmediato
    # (subir su foto, vincularlo a un producto) sin esperar una respuesta.
    id = serializers.UUIDField(required=False)
    # Todos opcionales a nivel de campo: un PATCH para vincular un producto
    # manda solo {id, productId} sobre un item que ya existe, y con campos
    # 'required' esto fallaria la validacion antes de llegar al update().
    # La obligatoriedad real (name/unit_cost/qty completos) se exige a mano
    # en PurchaseOrderSerializer, y solo para items nuevos.
    name = serializers.CharField(required=False)
    # El modelo guarda "sin foto" como "" (blank=True, sin null=True), pero
    # el front manda null en ese caso: sin este campo explicito, el
    # URLField que genera el ModelSerializer rechaza None.
    photo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    unit_cost = serializers.IntegerField(required=False, min_value=1)
    qty = serializers.IntegerField(required=False, min_value=1)
    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = PurchaseItem
        fields = ["id", "name", "photo", "unit_cost", "qty", "margin", "product_id"]

    def validate_photo(self, value):
        return value or ""


class PurchaseOrderSerializer(serializers.ModelSerializer):
    shipping_cost = serializers.IntegerField(min_value=0, required=False)
    margin = serializers.IntegerField(min_value=10, max_value=90, required=False)
    items = PurchaseItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "date", "supplier", "shipping_cost", "margin", "items"]
        read_only_fields = ["id"]

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("La fecha no puede ser futura.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = PurchaseOrder.objects.create(**validated_data)
        for position, item_data in enumerate(items_data):
            self._require_complete(item_data)
            item_data.setdefault("id", uuid.uuid4())
            PurchaseItem.objects.create(purchase=order, position=position, **item_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Upsert por id: un item existente se actualiza solo en los campos
        # que vinieron (asi {id, productId} no pisa name/photo/unit_cost), y
        # uno sin match se crea. Los que faltan en la lista NO se borran: un
        # PATCH parcial que omite un item no debe hacerlo desaparecer.
        if items_data is not None:
            existentes = {item.id: item for item in instance.items.all()}
            siguiente_posicion = instance.items.count()

            for item_data in items_data:
                item_id = item_data.get("id")
                item = existentes.get(item_id) if item_id else None

                if item is not None:
                    for attr, value in item_data.items():
                        if attr != "id":
                            setattr(item, attr, value)
                    item.save()
                else:
                    self._require_complete(item_data)
                    item_data.setdefault("id", item_id or uuid.uuid4())
                    PurchaseItem.objects.create(
                        purchase=instance, position=siguiente_posicion, **item_data
                    )
                    siguiente_posicion += 1

        return instance

    def _require_complete(self, item_data):
        faltantes = [f for f in ("name", "unit_cost", "qty") if f not in item_data]
        if faltantes:
            raise serializers.ValidationError(
                {"items": f"Un item nuevo necesita: {', '.join(faltantes)}."}
            )


class LoginSerializer(serializers.Serializer):
    pin = serializers.CharField(write_only=True)


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class StatsSerializer(serializers.Serializer):
    revenue = serializers.IntegerField()
    profit = serializers.IntegerField()
    units = serializers.IntegerField()
    months = serializers.ListField(child=serializers.CharField())
    top = serializers.ListField()
