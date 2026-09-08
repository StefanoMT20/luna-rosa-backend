# Quick Start Guide

## 5 Minute Setup

### 1. Prerequisites
- Python 3.9+
- PostgreSQL running locally

### 2. Install & Setup
```bash
# Create venv (if not already done)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (creates all tables + seeds data)
python manage.py migrate

# Create superuser for Django admin
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### 3. Access
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Products: http://localhost:8000/api/products/
- Home: http://localhost:8000/api/home/

## Quick API Test

### Login
```bash
curl -X POST http://localhost:8000/api/admin/login/ \
  -H "Content-Type: application/json" \
  -d '{"pin": "lunarosa"}' | jq .
```

### List Products
```bash
curl http://localhost:8000/api/products/ | jq .
```

### List Products (filtered)
```bash
curl 'http://localhost:8000/api/products/?category=casual&featured=true' | jq .
```

### Get Homepage
```bash
curl http://localhost:8000/api/home/ | jq .
```

## Notes

- **Default PIN**: `lunarosa`
- **Default Margin**: 60% (adjustable via settings)
- **Database**: PostgreSQL (create database `lunarosa` first)
- **Timezone**: America/Argentina/Buenos Aires
- **Media**: Stored in `./media/` folder in development

## Troubleshooting

### "connection refused" during migrate
```bash
# Make sure PostgreSQL is running
brew services start postgresql

# Create database
createdb lunarosa
```

### Migrations fail
```bash
# Reset migrations (dev only!)
python manage.py migrate zero api
python manage.py migrate
```

### Port 8000 already in use
```bash
python manage.py runserver 8001
```

## Next Steps

1. Update settings via Django admin or API
2. Set WhatsApp number: `PATCH /api/admin/settings/`
3. Upload product photos: `POST /api/admin/products/{id}/photos/`
4. Start tracking sales: `POST /api/admin/sales/`

## Full Documentation

- `README.md` - Original specification
- `SETUP.md` - Detailed setup instructions
- `IMPLEMENTATION.md` - Technical implementation details
