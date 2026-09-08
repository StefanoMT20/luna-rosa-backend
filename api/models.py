import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


SIZES = ["XS", "S", "M", "L", "XL", "Único"]
COLORS = ["Negro", "Blanco", "Rosa", "Fucsia", "Rojo", "Beige", "Celeste", "Dorado"]
CATEGORIES = [
    ("casual", "Casual"),
    ("fiesta", "Fiesta"),
    ("accesorios", "Accesorios"),
]


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cost = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    sizes = ArrayField(models.CharField(max_length=10, choices=[(s, s) for s in SIZES]))
    colors = ArrayField(models.CharField(max_length=20, choices=[(c, c) for c in COLORS]))
    featured = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self):
        return self.name

    @property
    def profit(self):
        if self.cost > 0:
            return self.price - self.cost
        settings = Settings.objects.first()
        margin = settings.margin if settings else 60
        return round(self.price * margin / 100)


class ProductPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to="products/")
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.product.name} - Photo {self.position}"

    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)

            max_size = 1200
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=82, optimize=True)
            buffer.seek(0)

            filename = f"{self.product.id}_{self.position}.jpg"
            self.image.save(filename, ContentFile(buffer.read()), save=False)

        super().save(*args, **kwargs)


class HomeSection(models.Model):
    MODE_CHOICES = [
        ("featured", "Featured"),
        ("cat", "Category"),
    ]

    key = models.SlugField(unique=True, primary_key=True)
    title = models.CharField(max_length=80)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    cat = models.CharField(max_length=20, blank=True, default="")
    on = models.BooleanField(default=True)
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return self.title


class SiteContent(models.Model):
    id = models.AutoField(primary_key=True)
    hero_title = models.CharField(max_length=255, default="Ropa que te hace sentir linda")
    hero_sub = models.TextField(
        default="Elegís, nos escribís por WhatsApp y te lo llevamos. Así de simple, bonita."
    )
    ship_title = models.CharField(max_length=255, default="Envíos y pagos")
    ship_sub = models.CharField(
        max_length=255, default="Entrega en Apóstoles y alrededores"
    )
    closing = models.CharField(max_length=255, default="gracias por estar acá")

    class Meta:
        verbose_name_plural = "Site Content"

    def __str__(self):
        return "Site Content"


class Settings(models.Model):
    id = models.AutoField(primary_key=True)
    whatsapp = models.CharField(max_length=20, default="")
    margin = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(90)],
    )
    pin_hash = models.CharField(max_length=255, default="")

    class Meta:
        verbose_name_plural = "Settings"

    def __str__(self):
        return "Settings"


class Sale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name="sales"
    )
    product_name = models.CharField(max_length=120)
    unit_price = models.PositiveIntegerField()
    qty = models.PositiveSmallIntegerField(default=1)
    date = models.DateField()
    profit = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.product_name} x{self.qty} on {self.date}"

    def calculate_profit(self):
        if self.product and self.product.cost > 0:
            return (self.unit_price - self.product.cost) * self.qty
        settings = Settings.objects.first()
        margin = settings.margin if settings else 60
        return round(self.unit_price * margin / 100) * self.qty
