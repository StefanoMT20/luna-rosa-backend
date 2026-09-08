# Luna Rosa API Reference

## Authentication

All admin endpoints require a Bearer token obtained from login.

### Login
```
POST /api/admin/login/
Content-Type: application/json

{
  "pin": "lunarosa"
}

Response (200 OK):
{
  "token": "abc123xyz..."
}
```

### Logout
```
POST /api/admin/logout/
Authorization: Token abc123xyz...

Response (200 OK):
{
  "status": "logged out"
}
```

**Note:** After logout, the token is invalidated and cannot be reused.

## Public Endpoints (No Auth)

### List Products
```
GET /api/products/

Query Parameters:
  ?category=casual           # Filter by category (casual, fiesta, accesorios)
  ?featured=true             # Filter featured products only

Response (200 OK):
{
  "count": 6,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "Vestido Selene",
      "price": 38000,
      "cost": 0,
      "category": "fiesta",
      "sizes": ["S", "M", "L"],
      "colors": ["Negro", "Rojo"],
      "featured": true,
      "active": true,
      "position": 0,
      "photos": [
        {
          "id": "uuid",
          "image": "http://localhost:8000/media/...",
          "position": 0
        }
      ],
      "profit": 22800
    }
  ]
}
```

### Get Product Detail
```
GET /api/products/{product_id}/

Response (200 OK):
{
  "id": "uuid",
  "name": "Vestido Selene",
  "price": 38000,
  ...
  "photos": [...]
}
```

### Get Homepage
```
GET /api/home/

Response (200 OK):
{
  "hero_title": "Ropa que te hace sentir linda",
  "hero_sub": "Elegís, nos escribís...",
  "ship_title": "Envíos y pagos",
  "ship_sub": "Entrega en Apóstoles...",
  "closing": "gracias por estar acá",
  "sections": [
    {
      "key": "nov",
      "title": "Recién llegado",
      "products": [
        { id, name, price, ..., photos, profit }
      ]
    },
    {
      "key": "cas",
      "title": "Para todos los días",
      "products": [...]
    },
    ...
  ]
}
```

### Get Settings (Public)
```
GET /api/settings/

Response (200 OK):
{
  "whatsapp": "5493755000000"
}
```

### Health Check
```
GET /api/health/

Response (200 OK):
{
  "status": "ok"
}
```

## Admin Endpoints (Token Required)

All admin endpoints require:
```
Authorization: Token {token_from_login}
```

### Products Management

#### List All Products
```
GET /api/admin/products/

Response (200 OK):
[Same as public products endpoint, but includes inactive products]
```

#### Create Product
```
POST /api/admin/products/
Content-Type: application/json
Authorization: Token ...

{
  "name": "Vestido Nuevo",
  "price": 25000,
  "cost": 10000,
  "category": "fiesta",
  "sizes": ["S", "M", "L"],
  "colors": ["Negro", "Rosa"],
  "featured": true,
  "position": 0
}

Response (201 Created):
{
  "id": "uuid",
  "name": "Vestido Nuevo",
  ...
}
```

#### Update Product
```
PATCH /api/admin/products/{product_id}/
Content-Type: application/json
Authorization: Token ...

{
  "name": "Vestido Actualizado",
  "price": 27000,
  "featured": false
}

Response (200 OK):
{ ...updated product... }
```

#### Delete Product (Soft Delete)
```
DELETE /api/admin/products/{product_id}/
Authorization: Token ...

Response (204 No Content)
```

**Note:** Products are soft-deleted (active=False), so they're hidden from public API but remain in database.

### Photo Management

#### Upload Photos
```
POST /api/admin/products/{product_id}/photos/
Content-Type: multipart/form-data
Authorization: Token ...

Form Data:
  image: [binary file] (JPEG/PNG/WebP, max 8MB)
  position: 0 (optional, auto-assigned if omitted)

Response (201 Created):
{
  "photos": [
    {
      "id": "uuid",
      "image": "http://localhost:8000/media/...",
      "position": 0
    }
  ]
}
```

**Constraints:**
- Max 4 photos per product
- Accepted formats: JPEG, PNG, WebP
- Max size: 8MB
- Images auto-resized to 1200px max and compressed to quality 82

#### Delete Photo
```
DELETE /api/admin/photos/{photo_id}/
Authorization: Token ...

Response (200 OK):
{
  "status": "photo deleted"
}
```

**Note:** Deleting a photo auto-reorders remaining photos.

### Home Content Management

#### Update Homepage Text
```
PATCH /api/admin/home/
Content-Type: application/json
Authorization: Token ...

{
  "hero_title": "New title",
  "hero_sub": "New subtitle",
  "ship_title": "New shipping title",
  "ship_sub": "New shipping subtitle",
  "closing": "New closing message"
}

Response (200 OK):
{ ...updated content... }
```

**Note:** All fields are optional. Only provided fields are updated.

#### Update Section
```
PATCH /api/admin/sections/{section_key}/
Content-Type: application/json
Authorization: Token ...

{
  "title": "New section title",
  "on": false
}

Response (200 OK):
{
  "key": "cas",
  "title": "New section title",
  "mode": "cat",
  "cat": "casual",
  "on": false,
  "position": 1
}
```

#### Reorder Sections
```
POST /api/admin/sections/reorder/
Content-Type: application/json
Authorization: Token ...

{
  "keys": ["fie", "nov", "cas", "acc"]
}

Response (200 OK):
{
  "status": "sections reordered"
}
```

**Note:** Provide all section keys in desired order. Position is auto-set based on array index.

### Sales Management

#### List Sales
```
GET /api/admin/sales/

Query Parameters:
  ?month=2026-09             # Filter by month (YYYY-MM format)

Response (200 OK):
{
  "results": [
    {
      "id": "uuid",
      "product_name": "Vestido Selene",
      "unit_price": 38000,
      "qty": 1,
      "profit": 22800,
      "date": "2026-09-05",
      "created_at": "2026-09-05T10:30:00Z"
    }
  ]
}
```

#### Record Sale
```
POST /api/admin/sales/
Content-Type: application/json
Authorization: Token ...

{
  "product_id": "uuid",    # Optional, can be omitted
  "unit_price": 38000,
  "qty": 1,
  "date": "2026-09-05"
}

Response (201 Created):
{
  "id": "uuid",
  "product_name": "Vestido Selene",
  "unit_price": 38000,
  "qty": 1,
  "profit": 22800,
  "date": "2026-09-05",
  "created_at": "2026-09-05T10:30:00Z"
}
```

**Rules:**
- `product_id` is optional (sale can exist for deleted products)
- `date` cannot be in the future
- `unit_price` and `qty` must be > 0
- `profit` is calculated server-side based on product cost or default margin

#### Delete Sale
```
DELETE /api/admin/sales/{sale_id}/
Authorization: Token ...

Response (200 OK):
{
  "status": "sale deleted"
}
```

### Analytics

#### Get Statistics
```
GET /api/admin/stats/

Query Parameters:
  ?month=2026-09             # Filter stats by month (YYYY-MM)

Response (200 OK):
{
  "revenue": 152000,
  "profit": 91200,
  "units": 4,
  "months": ["2026-09", "2026-08", "2026-07"],
  "top": [
    {
      "name": "Vestido Selene",
      "total": 76000,
      "qty": 2
    },
    {
      "name": "Blusa Aurora",
      "total": 39000,
      "qty": 2
    },
    ...
  ]
}
```

**Fields:**
- `revenue`: Total unit_price * qty
- `profit`: Sum of all profits
- `units`: Sum of all quantities
- `months`: List of distinct months with sales (desc order)
- `top`: Top 5 products by revenue

### Settings Management

#### Get Settings
```
GET /api/admin/settings/
Authorization: Token ...

Response (200 OK):
{
  "whatsapp": "5493755000000",
  "margin": 60
}
```

#### Update Settings
```
PATCH /api/admin/settings/
Content-Type: application/json
Authorization: Token ...

{
  "whatsapp": "5493755111111",
  "margin": 50,
  "pin": "newpin"             # Optional, change PIN
}

Response (200 OK):
{
  "whatsapp": "5493755111111",
  "margin": 50
}
```

**Rules:**
- `margin` must be 10-90
- `whatsapp` is stored as digits with country code (e.g., 5493755000000 for Argentina)
- Use "pin" field to change PIN (not returned in response)

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "error": "Invalid PIN"
}
```

### 404 Not Found
```json
{
  "error": "Section not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

## Data Types & Constraints

### Sizes
Valid sizes: `XS`, `S`, `M`, `L`, `XL`, `Único`

### Colors
Valid colors: `Negro`, `Blanco`, `Rosa`, `Fucsia`, `Rojo`, `Beige`, `Celeste`, `Dorado`

### Categories
Valid categories: `casual`, `fiesta`, `accesorios`

### Prices
- Always integers (pesos, no cents)
- Minimum: 1
- No decimal values

### Dates
- Format: `YYYY-MM-DD`
- Cannot be in the future (sales only)
- All dates stored in Buenos Aires timezone

### Pagination
- Default: 50 items per page
- Use `?page=2` to get next page
- Responses include `count`, `next`, `previous`, `results`

## Response Format

All responses are JSON with consistent structure:

**List Response:**
```json
{
  "count": 10,
  "next": "http://../?page=2",
  "previous": null,
  "results": [...]
}
```

**Detail Response:**
```json
{
  "id": "uuid",
  "field": "value",
  ...
}
```

**Error Response:**
```json
{
  "error": "message" | "field": ["message"]
}
```

## Rate Limiting

- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Login endpoint: 5 attempts/minute per IP

Headers returned:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1631234567
```

## Timezone

All timestamps use `America/Argentina/Buenos_Aires` timezone.

Example: `2026-09-05T10:30:00-03:00`

## CORS

Allow-Origin headers respect configured CORS origins:
- Development: `localhost:5173`, `localhost:3000`
- Production: Must be configured via environment variable

## Notes

- All timestamps are ISO 8601 format
- UUIDs are standard RFC 4122 format
- Profit calculation frozen at sale creation (historical accuracy)
- Product deletion is soft (sets active=False)
- Token never expires by default
