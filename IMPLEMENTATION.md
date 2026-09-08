# Luna Rosa Backend - Implementation Summary

## Overview

Complete Django REST Framework backend for Luna Rosa clothing store. Implements all requirements from the specification: product catalog management, image handling, sales tracking, and owner authentication via PIN.

## Project Structure

```
handoff-backend/
├── config/                 # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # URL routing
│   ├── wsgi.py            # WSGI application
│   └── asgi.py            # ASGI application
├── api/                   # Main application
│   ├── models.py          # Database models
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── admin.py           # Django admin configuration
│   └── migrations/        # Database migrations
├── media/                 # Uploaded files (gitignored)
├── staticfiles/           # Static files (gitignored)
├── manage.py              # Django CLI
├── requirements.txt       # Python dependencies
├── README.md              # Original specification
├── SETUP.md               # Setup instructions
├── IMPLEMENTATION.md      # This file
└── .gitignore             # Git ignore rules
```

## Models

### Product
- UUID primary key
- Name, price (integers, pesos), cost (for profit calculation)
- Category (casual, fiesta, accesorios)
- Sizes and colors (arrays of predefined values)
- Featured flag, active flag (soft delete), position (for ordering)
- Timestamps (created_at, updated_at)
- Profit property (auto-calculated based on cost or default margin)

### ProductPhoto
- UUID primary key, FK to Product
- Image field with auto-resizing (max 1200px) and compression (JPEG quality 82)
- Position for ordering within product
- Validates max 4 photos per product at serializer level

### HomeSection
- Slug key (unique), title, mode (featured or category-based)
- On/off toggle, position for ordering
- Pre-seeded with 4 sections (Recién llegado, Casual, Fiesta, Accesorios)

### SiteContent
- Singleton (pk=1)
- Hero title/subtitle, shipping title/subtitle, closing message
- Pre-seeded with default values

### Settings
- Singleton (pk=1)
- WhatsApp number (stored as digits with country code)
- Margin percentage (10-90, default 60)
- PIN hash (bcrypt-hashed via Django's make_password)

### Sale
- UUID primary key
- FK to Product (nullable, for historical records after product deletion)
- Product name (snapshot at sale time)
- Unit price, quantity, date
- Profit (frozen at creation time)
- Timestamps

## API Endpoints

### Authentication
- `POST /api/admin/login/` - Exchange PIN for token
- `POST /api/admin/logout/` - Revoke token

### Public (no auth, GET only)
- `GET /api/products/` - List active products (filterable by category/featured)
- `GET /api/products/{id}/` - Single product with photos
- `GET /api/home/` - Homepage sections with their products
- `GET /api/settings/` - Public settings (WhatsApp only)
- `GET /api/health/` - Health check

### Admin (token required)

**Products**
- `GET /api/admin/products/` - All products including inactive
- `POST /api/admin/products/` - Create
- `PATCH /api/admin/products/{id}/` - Update
- `DELETE /api/admin/products/{id}/` - Soft delete
- `POST /api/admin/products/{id}/photos/` - Upload photos
- `DELETE /api/admin/photos/{id}/` - Delete photo

**Home**
- `PATCH /api/admin/home/` - Update content text
- `PATCH /api/admin/sections/{key}/` - Update section (title, on/off)
- `POST /api/admin/sections/reorder/` - Reorder by providing key array

**Sales**
- `GET /api/admin/sales/` - List (filterable by month)
- `POST /api/admin/sales/` - Record sale
- `DELETE /api/admin/sales/{id}/` - Delete

**Stats**
- `GET /api/admin/stats/` - Revenue, profit, units, distinct months, top 5 products

**Settings**
- `GET /api/admin/settings/` - WhatsApp and margin
- `PATCH /api/admin/settings/` - Update (can include "pin" field to change PIN)

## Key Features

### Authentication
- Single PIN-based login (default: "lunarosa")
- PIN stored as bcrypt hash
- Token-based auth for subsequent requests
- Rate limiting on login endpoint

### Image Handling
- Automatic resizing to max 1200px (maintaining aspect ratio)
- JPEG conversion + compression (quality 82)
- Validation: max 8MB, JPEG/PNG/WebP only
- Max 4 photos per product
- Photo deletion auto-reorders remaining photos

### Profit Calculation
- If product has cost > 0: profit = price - cost
- Otherwise: profit = round(price * margin / 100)
- Margin default is 60%, configurable via settings
- Profit frozen at sale creation time (historical accuracy)

### Sales Tracking
- Date validation (no future dates)
- Product reference optional (survives product deletion via product_name snapshot)
- Monthly analytics (revenue, profit, units, top products)

### Data Seeding
- 3 migrations handle initialization:
  1. Initial schema
  2. HomeSection, SiteContent, Settings with defaults
  3. 6 sample products

### Timezone
- Set to America/Argentina/Buenos_Aires
- All dates stored and calculated in this timezone
- Month grouping respects local timezone

## Configuration

### Environment Variables (via python-decouple)
- `SECRET_KEY` - Django secret (required in production)
- `DEBUG` - Debug mode (default True for dev)
- `ALLOWED_HOSTS` - Comma-separated hosts (default localhost)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL connection
- `CORS_ALLOWED_ORIGINS` - Comma-separated CORS origins

### Settings Defaults
- Timezone: America/Argentina/Buenos_Aires
- Pagination: 50 items per page
- File upload: 8MB max
- Token auth (no expiration)
- Rate limit: 100/hour anon, 1000/hour user
- Database: PostgreSQL (SQLite in dev without .env)

## Database

### Migrations
```bash
python manage.py migrate  # Runs all migrations including seeds
```

### Backup/Restore
```bash
# Backup
pg_dump -U postgres lunarosa > backup.sql

# Restore
psql -U postgres lunarosa < backup.sql
```

## Development vs Production

### Dev
- `DEBUG=True` (default)
- SQLite or local PostgreSQL
- Media files served from `MEDIA_ROOT`
- CORS allows localhost:5173, localhost:3000

### Production
- `DEBUG=False` (must set)
- PostgreSQL required
- Media via S3/Cloudflare R2 (django-storages)
- HTTPS only
- Specific CORS origins
- Gunicorn/uWSGI + Nginx

## Testing

### Manual Testing
```bash
# Login
curl -X POST http://localhost:8000/api/admin/login/ \
  -H "Content-Type: application/json" \
  -d '{"pin": "lunarosa"}'

# List products
curl http://localhost:8000/api/products/

# Create product (with token)
curl -X POST http://localhost:8000/api/admin/products/ \
  -H "Authorization: Token {token}" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Django Admin
- URL: `/admin/`
- Register all models with inline photos for Product
- Editable list fields for price and featured status
- Read-only profit display

## Performance Considerations

1. **Image Optimization**: Automatic resizing and compression reduce storage and bandwidth
2. **Database Queries**: 
   - Select related/prefetch related used in views
   - Aggregations for stats queries
3. **Caching**: Could add Redis for:
   - Homepage sections (rarely changes)
   - Product list pagination
   - Stats calculations
4. **Media Storage**: S3/R2 for production scalability

## Security

1. **Authentication**: PIN-based with bcrypt hashing
2. **CORS**: Restricted to configured origins only
3. **Rate Limiting**: Throttles on login endpoint
4. **File Upload**: 
   - Size limits (8MB)
   - Format validation
   - Stored outside web root
5. **SQL Injection**: Protected by ORM
6. **CSRF**: Django middleware enabled
7. **Headers**: Security middleware enabled

## Error Handling

- Validation errors return 400 with field details
- Authentication errors return 401
- Not found errors return 404
- Server errors return 500 with error message
- All responses in JSON

## Maintenance

### Regular Tasks
1. Monthly database backups
2. Monitor log files for errors
3. Review sales statistics
4. Update product photos and descriptions
5. Adjust margin/pricing as needed

### Monitoring
- Health check: `GET /api/health/`
- Django logs: Check `DEBUG` and error output
- Database size: `SELECT pg_size_pretty(pg_database_size('lunarosa'));`

## Future Enhancements

1. **Search/Filter**: Full-text search on products
2. **Wishlist**: User-facing wishlist feature
3. **Reviews**: Customer reviews/ratings
4. **Analytics**: Advanced reporting (trends, peak seasons)
5. **Inventory**: Stock tracking
6. **Variants**: Product variants (color/size combinations)
7. **Bulk Upload**: CSV import for products
8. **Notifications**: Email/SMS for sales
9. **Multi-language**: Spanish/English support
10. **Mobile App**: React Native or Flutter client

## Dependencies

- Django 4.2.30 - Web framework
- DRF 3.16.1 - REST API
- PostgreSQL driver (psycopg2) - Database
- Pillow - Image processing
- django-cors-headers - CORS handling
- django-storages - S3/cloud storage
- python-decouple - Environment config
- boto3 - AWS SDK (for S3)

All dependencies are frozen in requirements.txt for reproducible builds.
