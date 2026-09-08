"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from api.views import (
    ProductViewSet,
    AdminProductViewSet,
    AdminSalesViewSet,
    SettingsPublicView,
    HomeView,
    HealthView,
    AuthLoginView,
    AuthLogoutView,
    AdminLoginView,
    AdminLogoutView,
    AdminPhotoDeleteView,
    AdminSiteContentView,
    AdminHomeSectionUpdateView,
    AdminHomeSectionReorderView,
    AdminStatsView,
    AdminSettingsView,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"admin/products", AdminProductViewSet, basename="admin-product")
router.register(r"admin/sales", AdminSalesViewSet, basename="admin-sale")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/settings/", SettingsPublicView.as_view(), name="settings"),
    path("api/home/", HomeView.as_view(), name="home"),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("api/auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("api/admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("api/admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("api/admin/photos/<uuid:pk>/", AdminPhotoDeleteView.as_view(), name="admin-photo-delete"),
    path("api/admin/home/", AdminSiteContentView.as_view(), name="admin-home"),
    # 'reorder' va ANTES: es un slug valido y <slug:key> lo capturaria primero.
    path("api/admin/sections/reorder/", AdminHomeSectionReorderView.as_view(), name="admin-section-reorder"),
    path("api/admin/sections/<slug:key>/", AdminHomeSectionUpdateView.as_view(), name="admin-section-update"),
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/settings/", AdminSettingsView.as_view(), name="admin-settings"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
