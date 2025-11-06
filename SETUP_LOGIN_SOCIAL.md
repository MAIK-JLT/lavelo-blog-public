# 🔐 Setup Login Social - Lavelo Blog

## ✅ Implementación Completada

Se ha implementado un sistema de **Login Social con Instagram/Facebook** que permite:

1. **Login único:** Usuario se autentica con Instagram/Facebook
2. **Sin registro:** No necesita email ni password
3. **Multi-usuario:** Cada usuario tiene su propia cuenta
4. **Token reutilizable:** El mismo token sirve para login y publicación

---

## 📋 Pasos para Activar

### 1️⃣ Crear Tablas en Base de Datos

```bash
cd /Users/julioizquierdo/lavelo-blog/api
python3 create_tables.py
```

Esto creará las tablas:
- `users` - Usuarios autenticados
- `social_tokens` - Tokens de redes sociales por usuario
- `posts` - Posts del blog (ya existe)

---

### 2️⃣ Configurar Credenciales OAuth

Edita `/Users/julioizquierdo/lavelo-blog/.env` y agrega:

```bash
# Instagram OAuth (Facebook App)
INSTAGRAM_CLIENT_ID=tu_app_id
INSTAGRAM_CLIENT_SECRET=tu_app_secret

# Facebook OAuth
FACEBOOK_CLIENT_ID=tu_app_id
FACEBOOK_CLIENT_SECRET=tu_app_secret

# Secret Key para sesiones
SECRET_KEY=genera-una-clave-secreta-aleatoria-aqui
```

**Cómo obtener credenciales:**

#### Instagram (Facebook App):
1. Ve a https://developers.facebook.com/apps/
2. Crea una app → Tipo: "Consumer"
3. Agrega producto "Instagram Basic Display"
4. Configura OAuth Redirect URI: `http://localhost:5001/api/social/callback/instagram`
5. Copia App ID y App Secret

#### Facebook:
1. Misma app de arriba
2. Agrega producto "Facebook Login"
3. Configura OAuth Redirect URI: `http://localhost:5001/api/social/callback/facebook`

---

### 3️⃣ Reiniciar Servidor

```bash
# Detener servidor actual
# Ctrl+C

# Iniciar de nuevo
cd /Users/julioizquierdo/lavelo-blog/api
python3 main.py
```

---

## 🧪 Probar el Flujo

### Flujo Completo:

1. **Abre:** http://localhost:5001/login.html
2. **Click:** "Continuar con Instagram"
3. **Autoriza** la app en Instagram
4. **Redirige** automáticamente al panel (ya logueado)
5. **Crea/publica** posts normalmente

### Verificar Sesión:

```bash
# En consola del navegador (F12):
fetch('http://localhost:5001/api/social/me', {credentials: 'include'})
  .then(r => r.json())
  .then(console.log)

# Debería mostrar:
# {user_id: 1, platform: "instagram", username: "tu_usuario"}
```

---

## 🔄 Cómo Funciona

### Login:
```
Usuario → /login.html
  ↓ Click "Instagram"
OAuth → Instagram autoriza
  ↓ Callback
Crea/actualiza User en BD
  ↓
Guarda token en social_tokens
  ↓
Crea sesión (user_id)
  ↓
Redirige a /panel/ (logueado)
```

### Publicación:
```
Usuario publica post
  ↓
Lee user_id de sesión
  ↓
Lee token de social_tokens (user_id)
  ↓
Publica en Instagram con ese token
```

---

## 🗄️ Estructura de BD

### Tabla `users`:
```sql
id                  INT PRIMARY KEY
instagram_id        VARCHAR(255) UNIQUE
instagram_username  VARCHAR(255)
facebook_id         VARCHAR(255) UNIQUE
facebook_name       VARCHAR(255)
created_at          DATETIME
last_login          DATETIME
```

### Tabla `social_tokens`:
```sql
id              INT PRIMARY KEY
user_id         INT (FK a users)
platform        VARCHAR(50)  -- 'instagram', 'facebook', etc.
access_token    TEXT
refresh_token   TEXT
expires_at      DATETIME
username        VARCHAR(100)
connected_at    DATETIME
last_used       DATETIME
```

---

## 🔧 Endpoints Nuevos

### Autenticación:
- `GET /api/social/me` - Info del usuario logueado
- `POST /api/social/logout` - Cerrar sesión

### OAuth:
- `GET /api/social/connect/{platform}` - Iniciar OAuth
- `GET /api/social/callback/{platform}` - Callback (login automático)

---

## 🚀 Producción

### Cambios necesarios:

1. **HTTPS obligatorio:**
```python
# main.py
app.add_middleware(
    SessionMiddleware,
    https_only=True  # ← Cambiar a True
)
```

2. **Redirect URIs:**
```bash
# .env producción
INSTAGRAM_REDIRECT_URI=https://blog.lavelo.es/api/social/callback/instagram
FACEBOOK_REDIRECT_URI=https://blog.lavelo.es/api/social/callback/facebook
```

3. **Configurar en Facebook App:**
- OAuth Redirect URIs → Agregar URLs de producción
- App Domains → `blog.lavelo.es`

---

## 📝 Notas Importantes

### Multi-Usuario:
- Cada usuario tiene su propio `user_id`
- Los posts NO están asociados a usuarios (todos ven todos)
- Los tokens SÍ están asociados a usuarios (cada uno publica con su cuenta)

### MCP:
- MCP sigue funcionando igual
- Lee tokens del usuario admin (user_id=1)
- No necesita login (acceso directo a servicios)

### Seguridad:
- Sessions firmadas con SECRET_KEY
- Tokens encriptados en BD (opcional: agregar encriptación)
- HTTPS en producción obligatorio

---

## ✅ Checklist Final

- [ ] Tablas creadas en BD
- [ ] Credenciales OAuth configuradas
- [ ] Servidor reiniciado
- [ ] Login con Instagram funciona
- [ ] Sesión persiste
- [ ] Publicación funciona con token del usuario

---

**¡Sistema de Login Social implementado!** 🎉
