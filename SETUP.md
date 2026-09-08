# Luna Rosa Backend Setup

## Prerequisites

- Python 3.9+
- PostgreSQL 16+
- pip

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root with the following variables (or use `.env.example` as template):

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=lunarosa
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Default Settings
WHATSAPP_NUMBER=5493755000000
DEFAULT_PIN=lunarosa
```

### 4. Database Setup

#### PostgreSQL (macOS with Homebrew)

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database
createdb lunarosa

# Create user (optional, if not using default postgres user)
createuser -P postgres
```

#### Run Migrations

```bash
python manage.py migrate
```

This will create all tables and seed initial data:
- HomeSection (4 sections: Featured, Casual, Fiesta, Accesorios)
- SiteContent (with default values)
- Settings (with default PIN "lunarosa" hashed)
- Sample Products (6 products for testing)

### 5. Create Superuser (for Django Admin)

```bash
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

The API will be available at: `http://localhost:8000/api/`

Django Admin: `http://localhost:8000/admin/`

## API Endpoints

### Public Endpoints (no authentication required)

- `GET /api/products/` - List all active products
  - Optional filters: `?category=casual` or `?featured=true`
- `GET /api/products/{id}/` - Get single product
- `GET /api/home/` - Get homepage content with sections
- `GET /api/settings/` - Get public settings (WhatsApp only)
- `GET /api/health/` - Health check

### Admin Endpoints (token authentication required)

#### Authentication
- `POST /api/admin/login/` - Login with PIN, returns token
- `POST /api/admin/logout/` - Logout

#### Products
- `GET /api/admin/products/` - List all products (including inactive)
- `POST /api/admin/products/` - Create product
- `PATCH /api/admin/products/{id}/` - Update product
- `DELETE /api/admin/products/{id}/` - Soft delete product
- `POST /api/admin/products/{id}/photos/` - Upload photos (max 4)
- `DELETE /api/admin/photos/{id}/` - Delete photo

#### Home Content
- `PATCH /api/admin/home/` - Update homepage text
- `PATCH /api/admin/sections/{key}/` - Update section (title, on/off status)
- `POST /api/admin/sections/reorder/` - Reorder sections

#### Sales
- `GET /api/admin/sales/` - List sales (optional filter: `?month=2026-09`)
- `POST /api/admin/sales/` - Record a sale
- `DELETE /api/admin/sales/{id}/` - Delete sale

#### Analytics
- `GET /api/admin/stats/` - Get sales stats (optional filter: `?month=2026-09`)

#### Settings
- `GET /api/admin/settings/` - Get settings (WhatsApp, margin)
- `PATCH /api/admin/settings/` - Update settings

## Usage Examples

### Login
```bash
curl -X POST http://localhost:8000/api/admin/login/ \
  -H "Content-Type: application/json" \
  -d '{"pin": "lunarosa"}'

# Returns: {"token": "your-token-here"}
```

### Get Products
```bash
curl http://localhost:8000/api/products/
```

### Create Product (with auth token)
```bash
curl -X POST http://localhost:8000/api/admin/products/ \
  -H "Authorization: Token your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Vestido Nuevo",
    "price": 25000,
    "cost": 10000,
    "category": "fiesta",
    "sizes": ["S", "M", "L"],
    "colors": ["Negro", "Rojo"],
    "featured": true
  }'
```

### Upload Photos
```bash
curl -X POST http://localhost:8000/api/admin/products/{product-id}/photos/ \
  -H "Authorization: Token your-token-here" \
  -F "image=@/path/to/photo.jpg" \
  -F "position=0"
```

### Record Sale
```bash
curl -X POST http://localhost:8000/api/admin/sales/ \
  -H "Authorization: Token your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "product-uuid",
    "unit_price": 25000,
    "qty": 1,
    "date": "2026-09-07"
  }'
```

## Production Deployment

### Environment Variables (required for production)

```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PASSWORD=your-db-password
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Database Backups

```bash
# Backup
pg_dump -U postgres lunarosa > backup.sql

# Restore
psql -U postgres lunarosa < backup.sql
```

### Media Storage

For production, configure S3/Cloudflare R2:

```bash
# Add to settings.py
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
```

## Troubleshooting

### Database Connection Error

Ensure PostgreSQL is running:
```bash
brew services list  # Check status
brew services start postgresql  # Start service
```

### Image Upload Issues

- Max file size: 8MB
- Allowed formats: JPEG, PNG, WebP
- Images are automatically resized to max 1200px and compressed to quality 82

### Reset Database

```bash
python manage.py migrate zero api
python manage.py migrate
```

## Development Tips

- Use Django Admin (`/admin/`) as a backup interface for all operations
- All timestamps use Buenos Aires timezone
- Prices are always integers (pesos without cents)
- Photos have positions (0 = main photo) and auto-reorder when deleted
- Sales profit is frozen at creation time
