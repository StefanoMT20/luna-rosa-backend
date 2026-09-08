import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crea o actualiza el usuario dueña a partir de OWNER_EMAIL y "
        "OWNER_PASSWORD. Idempotente: se puede correr en cada deploy."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", default=os.environ.get("OWNER_EMAIL"))
        parser.add_argument("--password", default=os.environ.get("OWNER_PASSWORD"))

    def handle(self, *args, **options):
        email = (options.get("email") or "").strip()
        password = options.get("password") or ""

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "OWNER_EMAIL / OWNER_PASSWORD no definidos: no se crea usuario."
                )
            )
            return

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.filter(username=email).first()

        created = user is None
        if created:
            user = User(username=email, email=email)

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        accion = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Usuario dueña {accion}: {email}"))
