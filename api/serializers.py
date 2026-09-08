from rest_framework import serializers
from django.utils import timezone
from .models import Product, ProductPhoto, HomeSection, SiteContent, Settings, Sale, SIZES, COLORS


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
