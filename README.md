# Luna Rosa — Handoff de BACKEND (Django + PostgreSQL)

## Contexto

Luna Rosa es una tienda de ropa de **Apóstoles, Misiones (Argentina)**, con una web app móvil hecha aparte (React, la ve Lovable). Este backend le da los datos por **REST**.

Volumen real esperado: **una sola dueña**, decenas de prendas, unas pocas ventas por día. No hace falta escala; sí simpleza y que se pueda operar desde el celular.

**No hay checkout ni pagos.** La clienta arma el carrito en el front y termina en WhatsApp. El backend **no** conoce carritos ni pedidos: solo catálogo, contenido de la portada, ventas anotadas a mano por la dueña, y ajustes.

## Stack
- Python 3.12 · Django 5 · Django REST Framework
- PostgreSQL 16
- Pillow (miniaturas) · django-cors-headers · python-decouple (o django-environ)
- Storage de imágenes: disco con `MEDIA_ROOT` detrás de Nginx, o S3/Cloudflare R2 vía `django-storages`
- Auth: **un solo usuario dueña**, token simple (DRF `TokenAuthentication` o JWT corto)

## Modelo de datos

### Product
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID pk | |
| name | CharField(120) | |
| price | PositiveIntegerField | **pesos enteros**, sin centavos |
| cost | PositiveIntegerField, default 0 | 0 = "sin costo cargado" |
| category | CharField choices | `casual` · `fiesta` · `accesorios` |
| sizes | ArrayField(CharField) | de `XS S M L XL Único` |
| colors | ArrayField(CharField) | nombres de la paleta (abajo) |
| featured | BooleanField, default True | aparece en "Recién llegado" |
| active | BooleanField, default True | borrado lógico |
| position | IntegerField, default 0 | orden dentro de su categoría |
| created_at / updated_at | auto | |

Propiedad `profit`: `price - cost` si `cost > 0`, si no `round(price * Settings.margin / 100)`.

### ProductPhoto
`id` · `product` FK(related_name='photos', on_delete=CASCADE) · `image` ImageField · `position` Integer (0 = principal) · `created_at`.
Máximo **4 por prenda** (validar en el serializer). Al guardar, generar una versión de lado máximo 1200px (el front ya manda ~900px, pero no confiar).

### HomeSection
`key` slug único · `title` CharField(80) · `mode` (`featured` | `cat`) · `cat` CharField (vacío si `featured`) · `on` Boolean · `position` Integer.
Semilla (migración de datos):
```
nov · "Recién llegado"        · featured ·            · on · 0
cas · "Para todos los días"   · cat      · casual     · on · 1
fie · "Noches de fiesta"      · cat      · fiesta     · on · 2
acc · "Detalles que suman"    · cat      · accesorios · on · 3
```

### SiteContent (singleton, pk=1)
`hero_title` · `hero_sub` · `ship_title` · `ship_sub` · `closing` (todos Text/Char).
Valores iniciales:
- hero_title: "Ropa que te hace sentir linda"
- hero_sub: "Elegís, nos escribís por WhatsApp y te lo llevamos. Así de simple, bonita."
- ship_title: "Envíos y pagos"
- ship_sub: "Entrega en Apóstoles y alrededores"
- closing: "gracias por estar acá"

### Settings (singleton, pk=1)
`whatsapp` CharField(20) — solo dígitos con código de país (ej. `5493755000000`) · `margin` PositiveSmallIntegerField default **60** (validado 10–90).

### Sale
`id` UUID · `product` FK(SET_NULL, null=True) · `product_name` CharField (copia histórica, sobrevive al borrado) · `unit_price` PositiveInteger · `qty` PositiveSmallInteger default 1 · `date` DateField · `profit` PositiveInteger · `created_at`.

**`profit` se calcula en el servidor al crear** y queda congelado: `(unit_price - cost) * qty` si la prenda tiene costo, si no `round(unit_price * margin/100) * qty`. Cambiar el margen después **no** debe alterar ventas ya anotadas.

Paleta válida de colores: Negro #2A2022 · Blanco #F7F2F0 · Rosa #F79BC0 · Fucsia #E8407F · Rojo #A83A46 · Beige #D9C4AE · Celeste #AFC5D8 · Dorado #C9A961.

## Endpoints

Base: `/api/`. Respuestas en JSON, camelCase (usar `djangorestframework-camel-case`) para que el front no traduzca.

### Público (sin auth, solo GET)
| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/products/` | prendas `active=True`, con `photos[]` (URLs absolutas), ordenadas por `position, -created_at`. Filtros opcionales `?category=`, `?featured=true` |
| GET | `/products/<id>/` | una prenda |
| GET | `/home/` | `{ heroTitle, heroSub, shipTitle, shipSub, closing, sections: [...] }` — solo secciones `on=True`, ordenadas por `position` |
| GET | `/settings/` | **solo** `{ whatsapp }` — el margen nunca es público |

### Dueña (token requerido)
| Método | Ruta | Acción |
|---|---|---|
| POST | `/admin/login/` | `{ pin }` → `{ token }` |
| POST | `/admin/logout/` | invalida el token |
| GET | `/admin/products/` | incluye inactivas y `cost`/`profit` |
| POST | `/admin/products/` | crear |
| PATCH | `/admin/products/<id>/` | editar (nombre y precio se editan sueltos desde la lista) |
| DELETE | `/admin/products/<id>/` | `active=False` (borrado lógico) |
| POST | `/admin/products/<id>/photos/` | multipart, hasta 4 archivos; devuelve las URLs |
| DELETE | `/admin/photos/<id>/` | borrar una foto |
| PATCH | `/admin/home/` | textos de la portada |
| PATCH | `/admin/sections/<key>/` | `title`, `on` |
| POST | `/admin/sections/reorder/` | `{ keys: ["fie","nov",...] }` → reescribe `position` |
| GET | `/admin/sales/?month=YYYY-MM` | ventas (sin `month`: todas), orden `-date, -created_at` |
| POST | `/admin/sales/` | `{ productId, unitPrice, qty, date }` → calcula `profit` |
| DELETE | `/admin/sales/<id>/` | borrar |
| GET | `/admin/stats/?month=YYYY-MM` | `{ revenue, profit, units, months: ["2026-09",...], top: [{ name, total }] }` |
| GET/PATCH | `/admin/settings/` | `{ whatsapp, margin }` |

`/admin/stats/` reemplaza los cálculos que hoy hace el front: `revenue = Σ unit_price*qty`, `profit = Σ profit`, `units = Σ qty`, `months` = meses distintos con ventas (desc), `top` = las 5 prendas con más facturado en el período.

## Autenticación

La dueña entra con **un PIN** (hoy `lunarosa` en el prototipo).
- Guardar el PIN **hasheado** (`make_password`) en el único `User`, o en `Settings.pin_hash`. Nunca en texto plano ni en el repo.
- `POST /admin/login/` compara y devuelve token. Token sin expiración corta (la dueña usa el celular a diario) pero revocable con logout.
- Rate limit en login: DRF throttling, ~5 intentos por minuto por IP.
- Permitir cambiar el PIN por `PATCH /admin/settings/`.

## Reglas y validaciones
1. `price > 0`; `cost >= 0` y `cost < price` (advertencia si no, no error duro).
2. Precios **enteros** en pesos: sin decimales en ningún lado.
3. `sizes` y `colors` validados contra las listas permitidas.
4. Fotos: máx. 4 por prenda, máx. 8 MB, solo jpeg/png/webp; recomprimir a JPEG calidad 82.
5. Prenda borrada: `active=False` y desaparece de `/products/`, pero sus ventas quedan (por eso `product_name`).
6. `Sale.date` no puede ser futura.
7. Zona horaria: `TIME_ZONE = 'America/Argentina/Buenos_Aires'`, `USE_TZ = True`. Los meses de `stats` se agrupan en hora local.
8. Los meses se identifican como `"YYYY-MM"` en toda la API.

## CORS y despliegue
- `CORS_ALLOWED_ORIGINS`: dominio del front (y `localhost:5173` en desarrollo). No usar `CORS_ALLOW_ALL_ORIGINS`.
- `ALLOWED_HOSTS`, `SECRET_KEY`, `DATABASE_URL`, `DEBUG=False` por variables de entorno.
- Servir `/media/` por Nginx (o CDN) con caché larga; nombres de archivo con hash.
- HTTPS obligatorio (el front abre WhatsApp y sube fotos desde el celular).
- Backups: `pg_dump` diario + copia de `MEDIA_ROOT`. Es el inventario entero de la tienda.
- `/api/health/` para monitoreo.

## Admin de Django
Registrar `Product` (con inline de fotos, filtro por categoría, edición en lista de `price` y `featured`), `Sale` (solo lectura de `profit`), `HomeSection`, `SiteContent`, `Settings`. Es la red de seguridad si algo falla en la app.

## Orden sugerido
1. Proyecto, settings por entorno, Postgres, health check.
2. `Product` + `ProductPhoto` + endpoints públicos + fixtures de muestra (las 6 prendas del prototipo).
3. Login por PIN + endpoints de dueña del catálogo + subida de fotos.
4. `SiteContent` + `HomeSection` + `/home/` y su edición.
5. `Sale` + `Settings` + `/admin/stats/`.
6. CORS, media en producción, backups.

## Datos de muestra
```
Vestido Selene   38000  fiesta      S,M,L      Negro,Rojo       featured
Blusa Aurora     19500  casual      S,M,L      Blanco,Rosa      featured
Jean Luna        27000  casual      XS,S,M,L   Celeste
Top Estrella     15000  fiesta      S,M        Negro,Dorado     featured
Aros Media Luna   8900  accesorios  Único      Dorado
Falda Petal      21000  casual      XS,S,M     Rosa,Negro
```

## Referencia
`Luna Rosa.dc.html` (en el bundle del frontend) es el prototipo funcional: si hay dudas sobre qué dato necesita una pantalla, ahí se ve el comportamiento esperado.
