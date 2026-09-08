# Luna Rosa Backend - Dokploy Deployment Guide

## Docker & Dokploy Configuration

### Dockerfile Setup
The `Dockerfile` is pre-configured for production deployment with:
- Multi-stage build (optimized image size)
- Python 3.9-slim base
- Gunicorn application server
- Health checks included
- 4 workers configured

### Local Development with Docker
Use `docker-compose.yml` for local testing:

```bash
# Start services (db + app)
docker-compose up

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access at http://localhost:8000/api/
```

### Deploy to Dokploy
1. Push code to Git repository
2. In Dokploy: Create new app from Git
3. Select repository and branch
4. Dokploy will auto-detect Dockerfile
5. Configure environment variables (see below)
6. Deploy

## Environment Variables for Production

Create a `.env` file with these variables (replace placeholder values):

### 1. Django Core Settings
```bash
# NEVER use default value in production
SECRET_KEY=your-very-long-random-secret-key-here

# Always False in production
DEBUG=False

# Your production domain(s)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

Generate SECRET_KEY:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 2. Database Configuration
```bash
# PostgreSQL (provided by Dokploy or your hosting)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=lunarosa
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=postgres-service  # Dokploy service name or hostname
DB_PORT=5432
```

**In Dokploy:**
- Create a PostgreSQL 16 service
- Link environment variables (Dokploy auto-generates DB_* values)
- Use service name as DB_HOST

### 3. CORS Configuration (Critical!)
```bash
# List your frontend URL(s), separated by comma, NO SPACES
# HTTPS required in production
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# If frontend is on different domain:
# CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com

# Multiple environments:
# CORS_ALLOWED_ORIGINS=https://app.prod.com,https://app.staging.com
```

**⚠️ CORS Security Notes:**
- Never use `*` in production (security risk)
- Match EXACTLY: protocol (https), domain, and port
- If frontend is at `https://app.example.com`, add exactly that
- No trailing slashes

### 4. File Storage Configuration

#### Option A: Local Storage (Disk)
```bash
# Default - files stored on server
# Requires Nginx to serve /media/ and /static/
# Good for: Single server deployment
```

Nginx config:
```nginx
location /media/ {
    alias /app/media/;
}

location /static/ {
    alias /app/staticfiles/;
}
```

#### Option B: S3 / AWS (Recommended)
```bash
USE_S3=True
AWS_STORAGE_BUCKET_NAME=luna-rosa-bucket
AWS_S3_REGION_NAME=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_CUSTOM_DOMAIN=luna-rosa-bucket.s3.amazonaws.com
```

#### Option C: Cloudflare R2 (la que usa Luna Rosa)

```bash
USE_S3=True
AWS_ACCESS_KEY_ID=<tu-access-key-de-R2>
AWS_SECRET_ACCESS_KEY=<tu-secret-de-R2>
AWS_STORAGE_BUCKET_NAME=luna-rosa-media
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
```

Sin dominio público conectado al bucket, las fotos se sirven con **URLs
firmadas** contra el endpoint privado (`*.r2.cloudflarestorage.com`), válidas
por `AWS_QUERYSTRING_EXPIRE` segundos (default: 7 días). Cada `GET` a
`/api/products/` o `/api/home/` genera las URLs en ese momento, así que se
renuevan solas en cada visita — el único caso límite es una pestaña del
navegador quedando abierta más de 7 días sin recargar.

Si más adelante conectás un dominio público al bucket (subdominio `r2.dev` o
uno propio), agregá `AWS_S3_CUSTOM_DOMAIN=<ese-host>` y las URLs vuelven a
salir limpias y sin expiración, sin tocar nada más.

Lo que ya queda resuelto en `config/settings.py`, sin tocar nada:

| Ajuste | Por qué |
|---|---|
| `AWS_DEFAULT_ACL = None` | R2 no implementa ACLs; mandar `public-read` hace fallar la subida |
| `AWS_S3_SIGNATURE_VERSION = 's3v4'` | R2 solo acepta firma v4 |
| `AWS_QUERYSTRING_AUTH = True` | Sin dominio público, es la única forma de que el navegador abra la foto |
| `AWS_QUERYSTRING_EXPIRE = 604800` | 7 días; ajustable por env, es el máximo que permite SigV4 |
| `AWS_S3_FILE_OVERWRITE = False` | Reusar el nombre deja a la CDN sirviendo la foto vieja |
| `CacheControl: immutable` | Los nombres son únicos, así que se cachean para siempre |

Crear un bucket **propio para Luna Rosa**: no compartir el de otro proyecto,
porque las claves de R2 dan acceso a todos los buckets de la cuenta.

### 5. Luna Rosa Specific Settings
```bash
# Store's WhatsApp number (for customer contact)
# Format: country code + number, no spaces
# Example: 5493755000000 (Argentina)
WHATSAPP_NUMBER=5493755000000

# Default profit margin (10-90)
# Can be changed via admin API
DEFAULT_MARGIN=60
```

### 6. Security Settings
```bash
# Redirect all HTTP to HTTPS
SECURE_SSL_REDIRECT=True

# Secure cookies
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Prevent clickjacking
X_FRAME_OPTIONS=DENY

# Prevent MIME type sniffing
SECURE_CONTENT_TYPE_NOSNIFF=True

# Enable XSS protection
SECURE_BROWSER_XSS_FILTER=True
```

### 7. Dokploy Specific
```bash
# Port (used by Dokploy)
PORT=8000

# Python path
PYTHONUNBUFFERED=1

# Gunicorn workers (formula: 2*CPU + 1)
# Dokploy default: 4
GUNICORN_WORKERS=4
```

## Complete .env Example

```bash
# Django
SECRET_KEY=django-insecure-abc123xyz...
DEBUG=False
ALLOWED_HOSTS=lunarosa.com,www.lunarosa.com

# Database
DB_NAME=lunarosa
DB_USER=postgres
DB_PASSWORD=secure_password_here
DB_HOST=postgres-service
DB_PORT=5432

# CORS (CRITICAL)
CORS_ALLOWED_ORIGINS=https://lunarosa.com,https://www.lunarosa.com

# Storage
USE_S3=True
AWS_STORAGE_BUCKET_NAME=luna-rosa-media
AWS_S3_REGION_NAME=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Luna Rosa
WHATSAPP_NUMBER=5493755000000
DEFAULT_MARGIN=60

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Deployment Steps with Dokploy

### 1. Create Application
- New App → Select Django
- Connect Git repository
- Select branch (main/production)

### 2. Add PostgreSQL Service
- Services → PostgreSQL 16
- Name: `postgres-service`
- Password: Generate secure password
- Link environment variables

### 3. Configure Environment
- Paste `.env` content
- Or upload `.env` file
- Dokploy will encrypt sensitive values

### 4. Build Configuration
```
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start Command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 5. Domain & HTTPS
- Add domain
- Enable SSL (automatic with Let's Encrypt)
- Add to CORS_ALLOWED_ORIGINS in .env

### 6. Deploy
- Deploy → Start deployment
- Monitor build logs
- Check application logs for errors

## Post-Deployment

### 1. Create Superuser
```bash
dokploy exec python manage.py createsuperuser
```

Or via Django shell:
```bash
dokploy exec python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_superuser('admin', 'admin@example.com', 'password')
```

### 2. Configure Store Settings
```bash
# Via API
curl -X POST https://yourdomain.com/api/admin/login/ \
  -H "Content-Type: application/json" \
  -d '{"pin": "lunarosa"}'

# Via Django Admin
https://yourdomain.com/admin/
```

### 3. Test API
```bash
# Public endpoints
curl https://yourdomain.com/api/products/
curl https://yourdomain.com/api/home/

# Admin login (test CORS)
curl -X POST https://yourdomain.com/api/admin/login/ \
  -H "Content-Type: application/json" \
  -H "Origin: https://yourdomain.com" \
  -d '{"pin": "lunarosa"}'
```

## CORS Troubleshooting

### Issue: "No 'Access-Control-Allow-Origin' header"

**Check:**
1. Frontend URL matches CORS_ALLOWED_ORIGINS exactly
2. Using HTTPS (not HTTP)
3. No trailing slash

**Fix:**
```bash
# Wrong
CORS_ALLOWED_ORIGINS=https://example.com/

# Right
CORS_ALLOWED_ORIGINS=https://example.com
```

### Issue: "403 Forbidden - CORS check failed"

**Likely causes:**
1. Protocol mismatch (http vs https)
2. Subdomain mismatch (www vs no-www)
3. Port mismatch
4. Typo in domain

**Debug:**
- Check browser console for exact Origin header
- Match it exactly in CORS_ALLOWED_ORIGINS

## Monitoring

### Check Logs
```bash
# Dokploy dashboard: View application logs
# Or SSH: tail -f /var/log/dokploy/luna-rosa.log
```

### Check Database
```bash
# Connect to database
psql -h {DB_HOST} -U postgres -d lunarosa

# Check tables
\dt

# Check data
SELECT COUNT(*) FROM api_product;
```

### Performance
- Monitor CPU/Memory in Dokploy dashboard
- Check database query performance
- Monitor S3 bucket size

## Scaling

For high traffic:

1. **Database:** Upgrade PostgreSQL resources
2. **Storage:** Use S3/R2 (scales automatically)
3. **Workers:** Increase GUNICORN_WORKERS
4. **Caching:** Add Redis for session storage
5. **CDN:** CloudFlare for static files

## Backup Strategy

### Automated (Dokploy)
- Enable automatic backups
- Store in S3 bucket
- Test restore regularly

### Manual
```bash
# Backup
dokploy exec pg_dump -U postgres lunarosa > backup.sql

# Restore
dokploy exec psql -U postgres lunarosa < backup.sql
```

## Maintenance Checklist

- [ ] Set up automated backups
- [ ] Test backup restoration
- [ ] Configure monitoring alerts
- [ ] Set up error tracking (Sentry)
- [ ] Configure email for admin alerts
- [ ] Document recovery procedures
- [ ] Test CORS with real frontend
- [ ] Verify HTTPS redirect
- [ ] Check database size
- [ ] Monitor API performance
- [ ] Update Python packages monthly
- [ ] Review Django security checklist

## Need Help?

- API Reference: `API_REFERENCE.md`
- Setup Guide: `SETUP.md`
- Implementation: `IMPLEMENTATION.md`
- Dokploy Docs: https://dokploy.com/docs
