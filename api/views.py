from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.models import Token
from rest_framework.throttling import ScopedRateThrottle

from .authentication import BearerTokenAuthentication
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.db.models import Sum, F, Q, Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta

from .models import Product, ProductPhoto, HomeSection, SiteContent, Settings, Sale
from .serializers import (
    ProductSerializer,
    ProductPhotoSerializer,
    ProductPhotoUploadSerializer,
    HomeSectionSerializer,
    HomeSectionProductSerializer,
    SiteContentSerializer,
    SiteContentWithSectionsSerializer,
    SettingsPublicSerializer,
    SettingsSerializer,
    SaleSerializer,
    SaleListSerializer,
    LoginSerializer,
    EmailLoginSerializer,
    StatsSerializer,
)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        featured = self.request.query_params.get("featured")

        if category:
            queryset = queryset.filter(category=category)
        if featured and featured.lower() == "true":
            queryset = queryset.filter(featured=True)

        return queryset.order_by("position", "-created_at")


class SettingsPublicView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        settings = Settings.objects.first()
        if not settings:
            return Response({"whatsapp": ""})
        serializer = SettingsPublicSerializer(settings)
        return Response(serializer.data)


class HomeView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        site_content = SiteContent.objects.first()
        sections = HomeSection.objects.filter(on=True).order_by("position")

        if not site_content:
            site_content = SiteContent.objects.create()

        section_data = []
        for section in sections:
            if section.mode == "featured":
                products = Product.objects.filter(active=True, featured=True).order_by(
                    "position", "-created_at"
                )
            else:
                products = Product.objects.filter(active=True, category=section.cat).order_by(
                    "position", "-created_at"
                )

            section_data.append(
                {
                    "key": section.key,
                    "title": section.title,
                    "products": ProductSerializer(products, many=True, context={"request": request}).data,
                }
            )

        data = {
            "hero_title": site_content.hero_title,
            "hero_sub": site_content.hero_sub,
            "ship_title": site_content.ship_title,
            "ship_sub": site_content.ship_sub,
            "closing": site_content.closing,
            "sections": section_data,
        }
        return Response(data)


class HealthView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class AuthLoginView(views.APIView):
    """POST /api/auth/login/  {email, password} -> {token}

    El token se devuelve para usarse como 'Authorization: Bearer <token>'.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Email o contraseña inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            # Hasheamos igual para no filtrar por tiempo de respuesta si el
            # email existe o no.
            User().set_password(password)
            return Response(
                {"detail": "Email o contraseña inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password) or not user.is_active:
            return Response(
                {"detail": "Email o contraseña inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class AuthLogoutView(views.APIView):
    """POST /api/auth/logout/ — invalida el token actual."""

    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Sesión cerrada."})


class AdminLoginView(views.APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            pin = serializer.validated_data.get("pin")
            settings = Settings.objects.first()

            if not settings or not settings.pin_hash:
                return Response(
                    {"error": "PIN not configured"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if check_password(pin, settings.pin_hash):
                user, _ = User.objects.get_or_create(username="admin")
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"token": token.key})
            else:
                return Response(
                    {"error": "Invalid PIN"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminLogoutView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except AttributeError:
            pass
        return Response({"status": "logged out"})


class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.all().order_by("position", "-created_at")

    @action(detail=True, methods=["post"], parser_classes=(MultiPartParser, FormParser))
    def photos(self, request, pk=None):
        product = self.get_object()
        photo_count = product.photos.count()

        if photo_count >= 4 and not request.FILES:
            return Response(
                {"error": "Maximum 4 photos per product"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_photos = []
        files = request.FILES.getlist("image")

        for idx, file in enumerate(files):
            if photo_count + idx >= 4:
                break

            serializer = ProductPhotoUploadSerializer(
                data={"image": file, "position": photo_count + idx}
            )
            if serializer.is_valid():
                photo = serializer.save(product=product)
                uploaded_photos.append(
                    {
                        "id": str(photo.id),
                        "image": request.build_absolute_uri(photo.image.url),
                        "position": photo.position,
                    }
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"photos": uploaded_photos}, status=status.HTTP_201_CREATED)


class AdminPhotoDeleteView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            photo = ProductPhoto.objects.get(id=pk)
            product = photo.product
            photo.delete()

            reorder_photos = ProductPhoto.objects.filter(product=product).order_by(
                "position"
            )
            for idx, p in enumerate(reorder_photos):
                p.position = idx
                p.save()

            return Response({"status": "photo deleted"})
        except ProductPhoto.DoesNotExist:
            return Response(
                {"error": "Photo not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class AdminSiteContentView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        site_content = SiteContent.objects.first()
        if not site_content:
            site_content = SiteContent.objects.create()

        serializer = SiteContentSerializer(site_content, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminHomeSectionUpdateView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, key):
        try:
            section = HomeSection.objects.get(key=key)
        except HomeSection.DoesNotExist:
            return Response(
                {"error": "Section not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = HomeSectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminHomeSectionReorderView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        keys = request.data.get("keys", [])
        if not keys:
            return Response(
                {"error": "keys list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for idx, key in enumerate(keys):
            try:
                section = HomeSection.objects.get(key=key)
                section.position = idx
                section.save()
            except HomeSection.DoesNotExist:
                return Response(
                    {"error": f"Section {key} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response({"status": "sections reordered"})


class AdminSalesViewSet(viewsets.ViewSet):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        month = request.query_params.get("month")
        sales = Sale.objects.all()

        if month:
            try:
                month_date = datetime.strptime(month, "%Y-%m").date()
                sales = sales.filter(
                    date__year=month_date.year,
                    date__month=month_date.month,
                )
            except ValueError:
                return Response(
                    {"error": "Invalid month format. Use YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = SaleListSerializer(sales.order_by("-date", "-created_at"), many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = SaleSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            sale = serializer.save()
            return Response(SaleListSerializer(sale).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            sale = Sale.objects.get(id=pk)
            sale.delete()
            return Response({"status": "sale deleted"})
        except Sale.DoesNotExist:
            return Response(
                {"error": "Sale not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class AdminStatsView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get("month")
        sales = Sale.objects.all()

        if month:
            try:
                month_date = datetime.strptime(month, "%Y-%m").date()
                sales = sales.filter(
                    date__year=month_date.year,
                    date__month=month_date.month,
                )
            except ValueError:
                return Response(
                    {"error": "Invalid month format. Use YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        revenue = sales.aggregate(total=Sum(F("unit_price") * F("qty")))["total"] or 0
        profit = sales.aggregate(total=Sum("profit"))["total"] or 0
        units = sales.aggregate(total=Sum("qty"))["total"] or 0

        months = list(
            sales.values_list("date", flat=True)
            .annotate(month=TruncMonth("date"))
            .values_list("month", flat=True)
            .distinct()
            .order_by("-month")
        )
        months = [m.strftime("%Y-%m") for m in months if m]

        top_products = (
            sales.values("product_name")
            .annotate(
                total=Sum(F("unit_price") * F("qty")),
                qty=Sum("qty"),
            )
            .order_by("-total")[:5]
        )

        top = [
            {
                "name": p["product_name"],
                "total": p["total"],
                "qty": p["qty"],
            }
            for p in top_products
        ]

        return Response(
            {
                "revenue": revenue,
                "profit": profit,
                "units": units,
                "months": months,
                "top": top,
            }
        )


class AdminSettingsView(views.APIView):
    authentication_classes = [BearerTokenAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings = Settings.objects.first()
        if not settings:
            settings = Settings.objects.create()
        serializer = SettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings = Settings.objects.first()
        if not settings:
            settings = Settings.objects.create()

        data = request.data.copy()
        if "pin" in data:
            data["pin_hash"] = make_password(data.pop("pin"))

        serializer = SettingsSerializer(settings, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if "pin_hash" in data:
                settings.pin_hash = data["pin_hash"]
                settings.save()
            return Response(SettingsSerializer(settings).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
