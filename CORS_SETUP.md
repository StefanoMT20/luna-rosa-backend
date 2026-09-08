# CORS Configuration Guide - Luna Rosa Backend

## Overview

CORS (Cross-Origin Resource Sharing) controla qué dominios pueden hacer requests a tu API desde el navegador.

**Tu arquitectura:**
- Backend: `https://api.lunarosaclothing.com`
- Frontend: `https://lunarosaclothing.com`

## How It Works

Cuando el frontend en `https://lunarosaclothing.com` hace un request a `https://api.lunarosaclothing.com`, el navegador envía:

```
Origin: https://lunarosaclothing.com
```

Django responde con los headers CORS:

```
Access-Control-Allow-Origin: https://lunarosaclothing.com
Access-Control-Allow-Methods: DELETE, GET, OPTIONS, PATCH, POST, PUT
Access-Control-Allow-Headers: accept, authorization, content-type, user-agent, x-csrftoken, x-requested-with
Access-Control-Max-Age: 86400
```

Nota: NO se manda `Access-Control-Allow-Credentials`. Solo aparece si
activas `CORS_ALLOW_CREDENTIALS = True`, que hace falta unicamente si
autenticaras con cookies de sesion. Con tokens Bearer no se necesita.

## Configuration

### 1. Environment Variable

En tu `.env` en producción:

```bash
# Para un solo dominio
CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com

# Para múltiples dominios (con y sin www)
CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com,https://www.lunarosaclothing.com

# Para staging + production
CORS_ALLOWED_ORIGINS=https://prod.lunarosaclothing.com,https://staging.lunarosaclothing.com
```

### 2. Cómo funciona en Django

**File:** `config/settings.py`

```python
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000',  # Dev
    cast=lambda v: [s.strip() for s in v.split(',')]
)
```

El middleware `django-cors-headers` está incluido:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # ← Está aquí
    'django.contrib.sessions.middleware.SessionMiddleware',
    ...
]
```

### 3. Configuración automática de headers

Django genera automáticamente:

```
Access-Control-Allow-Origin: {tu-dominio}
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, Accept, Origin
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
```

No necesitas hacer nada manualmente.

## Development vs Production

### Development (localhost)

```bash
# .env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Permite requests desde:
- `http://localhost:5173` (React dev server típico)
- `http://localhost:3000` (Next.js / Express típico)

### Production (Dokploy)

```bash
# .env
CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com,https://www.lunarosaclothing.com
```

Permite requests SOLO desde:
- `https://lunarosaclothing.com`
- `https://www.lunarosaclothing.com`

## Testing CORS

### Test 1: Verificar que CORS headers se envían

```bash
# Sin CORS (error esperado si frontend fuera diferente)
curl -i https://api.lunarosaclothing.com/api/products/

# Con CORS (test desde frontend origin)
curl -i -H "Origin: https://lunarosaclothing.com" \
  https://api.lunarosaclothing.com/api/products/
```

Deberías ver:
```
Access-Control-Allow-Origin: https://lunarosaclothing.com
```

### Test 2: Verificar preflight (OPTIONS)

Algunos requests (POST, PUT, etc) requieren un preflight OPTIONS:

```bash
curl -i -X OPTIONS \
  -H "Origin: https://lunarosaclothing.com" \
  -H "Access-Control-Request-Method: POST" \
  https://api.lunarosaclothing.com/api/admin/login/
```

Respuesta esperada:
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://lunarosaclothing.com
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### Test 3: Desde el browser (DevTools)

En la consola del navegador del frontend:

```javascript
// Este request debe funcionar
fetch('https://api.lunarosaclothing.com/api/products/')
  .then(r => r.json())
  .then(data => console.log(data))
  .catch(e => console.error('CORS Error:', e))
```

Si ves "CORS policy: No 'Access-Control-Allow-Origin'" → problema de configuración.

## Common Issues

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Cause:** El dominio del frontend no está en `CORS_ALLOWED_ORIGINS`

**Solution:**
1. Verifica que el frontend URL es exacto (protocolo, dominio, puerto)
2. Actualiza `.env`:
   ```bash
   CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com
   ```
3. Redeploy en Dokploy
4. Limpia cache del navegador

### Issue: CORS funciona en dev pero no en production

**Cause:** Probablemente DEBUG=True en dev, pero False en prod

**Solution:**
- CORS headers se envían en ambos casos
- Verifica que CORS_ALLOWED_ORIGINS en `.env` de prod sea correcto
- No uses `*` en producción

### Issue: Preflight OPTIONS falla con 403

**Cause:** Throttle rate limit en login endpoint

**Solution:**
- Login endpoint tiene rate limit: 5 intentos/minuto por IP
- Preflight OPTIONS no consume intentos
- Si muchos usuarios = aumentar limit en settings.py:
  ```python
  'DEFAULT_THROTTLE_RATES': {
      'anon': '100/hour',  # Aumenta este
      'user': '1000/hour',
  }
  ```

## Browser Behavior

### Requests sin CORS (no requieren preflight)

```javascript
// GET, HEAD, POST (con Content-Type: application/x-www-form-urlencoded)
fetch('https://api.lunarosaclothing.com/api/products/')
```

### Requests con CORS (requieren preflight OPTIONS)

```javascript
// POST con Content-Type: application/json
// PUT, PATCH, DELETE
// Authorization header

fetch('https://api.lunarosaclothing.com/api/admin/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer token...'
  },
  body: JSON.stringify({ pin: 'lunarosa' })
})
```

El navegador automáticamente:
1. Envía OPTIONS preflight
2. Espera los headers CORS
3. Si OK → envía el request real
4. Si NO → bloquea con error CORS

## Seguridad

### ✅ Lo que hicimos bien

- `CORS_ALLOWED_ORIGINS` configurable por ambiente
- No usar `*` (allowiese to any origin)
- Especificar solo dominios necesarios
- Usar HTTPS en producción

### ⚠️ Evitar en producción

```bash
# ❌ NUNCA hagas esto
CORS_ALLOWED_ORIGINS=*

# ❌ NUNCA hagas esto
CORS_ALLOWED_ORIGINS=http://*

# ❌ No permitir subdominio comodín
CORS_ALLOWED_ORIGINS=https://*.example.com
```

### ✅ Lo correcto

```bash
# Especificar exactamente
CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com,https://www.lunarosaclothing.com

# O para staging
CORS_ALLOWED_ORIGINS=https://staging.lunarosaclothing.com
```

## Después de Deploy en Dokploy

1. **Actualiza `.env`:**
   ```bash
   CORS_ALLOWED_ORIGINS=https://lunarosaclothing.com
   DEBUG=False
   SECURE_SSL_REDIRECT=True
   ```

2. **Redeploy** en Dokploy

3. **Test:**
   ```bash
   curl -H "Origin: https://lunarosaclothing.com" \
     https://api.lunarosaclothing.com/api/products/
   ```
   Debe mostrar:
   ```
   Access-Control-Allow-Origin: https://lunarosaclothing.com
   ```

4. **Desde el frontend**, verifica console (no debe haber CORS errors)

## Reference

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [django-cors-headers docs](https://github.com/adamchainz/django-cors-headers)
- [Browser CORS Flow](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios)
