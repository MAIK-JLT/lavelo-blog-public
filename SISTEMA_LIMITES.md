# 🎯 Sistema de Límites por Tier

## 📊 Niveles de Usuario

### 1️⃣ **Anónimo** (Sin login)
- ✅ **Crear:** 10 posts/día
- ❌ **Publicar:** NO permitido
- 🔍 **Identificación:** Por IP

### 2️⃣ **Registrado Gratis** (Login con Instagram/Facebook)
- ✅ **Crear:** 10 posts/día
- ✅ **Publicar:** Máximo 20 posts en total
- 🔍 **Identificación:** user_id en sesión

### 3️⃣ **Premium** (€19/mes vía Stripe)
- ✅ **Crear:** Ilimitado
- ✅ **Publicar:** Ilimitado
- 🔍 **Identificación:** user_id + tier='premium'

---

## 🗄️ Estructura de BD

### Tabla `users`:
```sql
tier VARCHAR(20) DEFAULT 'free'  -- 'free', 'premium'
posts_published_total INT DEFAULT 0  -- Total publicados
stripe_customer_id VARCHAR(255)
stripe_subscription_id VARCHAR(255)
subscription_status VARCHAR(50)  -- 'active', 'canceled', 'past_due'
```

### Tabla `anonymous_usage`:
```sql
ip_address VARCHAR(45)  -- IPv4 o IPv6
posts_created_today INT DEFAULT 0
last_post_date DATE
```

---

## 🔧 Implementación

### Verificar Límite de Creación:
```python
# routers/posts.py
user_id = request.session.get('user_id')
client_ip = request.client.host if not user_id else None

limit_check = limits_service.check_create_limit(
    user_id=user_id,
    client_ip=client_ip
)

if not limit_check['allowed']:
    raise HTTPException(403, detail=limit_check['message'])
```

### Verificar Límite de Publicación:
```python
# services/publish_service.py
limit_check = limits_service.check_publish_limit(user_id)

if not limit_check['allowed']:
    return {
        'success': False,
        'error': limit_check['message'],
        'upgrade_required': True
    }

# Después de publicar exitosamente:
limits_service.increment_publish_count(user_id)
```

---

## 📝 Mensajes de Error

### Anónimo (10 posts/día alcanzado):
```
❌ Límite de 10 posts por día alcanzado. 
Inicia sesión para crear más: http://localhost:5001/login.html
```

### Free (10 posts/día alcanzado):
```
❌ Límite de 10 posts por día alcanzado. 
Actualiza a Premium por €19/mes para creación ilimitada.
```

### Free (20 publicaciones totales alcanzadas):
```
❌ Límite de 20 publicaciones alcanzado. 
Actualiza a Premium por €19/mes para publicaciones ilimitadas.
```

---

## 🔄 Reseteo de Contadores

### Creación (diario):
- Se resetea automáticamente cada día
- Campo `last_post_date` en `anonymous_usage`
- Compara con fecha actual al verificar límite

### Publicación (total):
- NO se resetea
- Contador acumulativo en `users.posts_published_total`
- Solo se resetea al actualizar a Premium

---

## 🎨 UI - Mostrar Límites

### En Panel Web:
```javascript
// Después de crear post
if (result.limit_info) {
    showNotification(result.limit_info);
    // Ej: "✅ Post 3/10 hoy"
}

// Si alcanza límite
if (error.status === 403) {
    showUpgradeModal(error.message);
}
```

### Mensajes Informativos:
- **Anónimo:** "Post 3/10 hoy - Inicia sesión para más"
- **Free:** "Post 5/10 hoy - Upgrade a Premium para ilimitado"
- **Free (publicar):** "Publicación 15/20 - Quedan 5"
- **Premium:** "Sin límites ✨"

---

## 🚀 Próximos Pasos

### Para Activar:

1. **Crear tablas:**
   ```bash
   cd api
   python3 create_tables.py
   ```

2. **Verificar columnas nuevas:**
   - `users.tier`
   - `users.posts_published_total`
   - `users.stripe_customer_id`
   - Tabla `anonymous_usage`

3. **Probar límites:**
   - Crear 10 posts sin login → Debe bloquear
   - Login → Crear 10 posts → Debe bloquear
   - Publicar 20 posts → Debe bloquear

4. **Integrar Stripe** (futuro):
   - Webhook para actualizar `tier` a 'premium'
   - Actualizar `subscription_status`

---

## 📊 Tracking y Analytics

### Métricas Útiles:
```sql
-- Usuarios por tier
SELECT tier, COUNT(*) FROM users GROUP BY tier;

-- Posts creados hoy (anónimos)
SELECT SUM(posts_created_today) FROM anonymous_usage 
WHERE last_post_date = CURDATE();

-- Usuarios cerca del límite de publicación
SELECT * FROM users 
WHERE tier='free' AND posts_published_total >= 18;
```

---

## ✅ Checklist de Implementación

- [x] Modelo `User` con campos de tier
- [x] Modelo `AnonymousUsage` para tracking de IPs
- [x] Servicio `limits_service` con verificaciones
- [x] Integración en endpoint de creación
- [x] Integración en servicio de publicación
- [x] Incremento de contadores
- [ ] Crear tablas en BD
- [ ] Probar flujo completo
- [ ] Integrar Stripe (futuro)
- [ ] UI para mostrar límites

---

**Sistema de límites implementado y listo para probar!** 🎉
