# 📊 Estados del Workflow - Lavelo Blog

## 🎯 Resumen de Estados

El sistema usa **9 estados principales** que representan las fases del workflow de creación y publicación de contenido.

---

## 📋 Estados Detallados

### 1️⃣ **BASE_TEXT_AWAITING** 🟠
**Significado:** El post está creado pero necesita que se generen los textos adaptados para redes sociales.

**Archivos necesarios:**
- ✅ `{codigo}_base.txt` - Texto base del post (ya existe)

**Archivos a generar:**
- ⏳ `{codigo}_instagram.txt`
- ⏳ `{codigo}_linkedin.txt`
- ⏳ `{codigo}_twitter.txt`
- ⏳ `{codigo}_facebook.txt`
- ⏳ `{codigo}_tiktok.txt`

**Acción:** Validar Fase 1 → Genera textos adaptados con Claude
**Siguiente estado:** `IMAGE_PROMPT_AWAITING`

---

### 2️⃣ **IMAGE_PROMPT_AWAITING** 🟠
**Significado:** Los textos adaptados están listos, ahora necesita generar el prompt de imagen.

**Archivos necesarios:**
- ✅ Textos adaptados (instagram, linkedin, etc.)

**Archivos a generar:**
- ⏳ `{codigo}_prompt_imagen.txt` - Prompt optimizado para IA de imágenes

**Acción:** Validar Fase 2 → Genera prompt con Claude
**Siguiente estado:** `IMAGE_BASE_AWAITING`

---

### 3️⃣ **IMAGE_BASE_AWAITING** 🟠
**Significado:** El prompt está listo, ahora necesita generar las imágenes base con IA.

**Archivos necesarios:**
- ✅ `{codigo}_prompt_imagen.txt`

**Archivos a generar:**
- ⏳ `{codigo}_imagen_base.png` - Imagen generada con Fal.ai (1024x1024)
- ⏳ Variaciones opcionales (imagen_base_v1.png, v2.png, etc.)

**Acción:** Validar Fase 3 → Genera imágenes con Fal.ai SeaDream 4.0
**Siguiente estado:** `IMAGE_FORMATS_AWAITING`

---

### 4️⃣ **IMAGE_FORMATS_AWAITING** 🟠
**Significado:** La imagen base está lista, ahora necesita formatearla para cada red social.

**Archivos necesarios:**
- ✅ `{codigo}_imagen_base.png`

**Archivos a generar:**
- ⏳ `{codigo}_instagram_1x1.png` (1080x1080)
- ⏳ `{codigo}_instagram_stories_9x16.png` (1080x1920)
- ⏳ `{codigo}_linkedin_16x9.png` (1200x627)
- ⏳ `{codigo}_twitter_16x9.png` (1200x675)
- ⏳ `{codigo}_facebook_16x9.png` (1200x630)

**Acción:** Validar Fase 4 → Formatea imágenes con Pillow
**Siguiente estado:** `VIDEO_SCRIPT_AWAITING`

---

### 5️⃣ **VIDEO_SCRIPT_AWAITING** 🟠
**Significado:** Las imágenes están listas, ahora necesita generar el script del video.

**Archivos necesarios:**
- ✅ Imágenes formateadas

**Archivos a generar:**
- ⏳ `{codigo}_script_video.txt` - Script de 15 segundos dividido en escenas

**Acción:** Validar Fase 5 → Genera script con Claude
**Siguiente estado:** `VIDEO_BASE_AWAITING`

---

### 6️⃣ **VIDEO_BASE_AWAITING** 🟠
**Significado:** El script está listo, ahora necesita generar el video base con IA.

**Archivos necesarios:**
- ✅ `{codigo}_script_video.txt`
- ✅ `{codigo}_imagen_base.png` (opcional, para image-to-video)

**Archivos a generar:**
- ⏳ `{codigo}_video_base.mp4` - Video generado con Fal.ai SeeDance 1.0 Pro

**Acción:** Validar Fase 6 → Genera video con Fal.ai
**Siguiente estado:** `VIDEO_FORMATS_AWAITING`

---

### 7️⃣ **VIDEO_FORMATS_AWAITING** 🟠
**Significado:** El video base está listo, ahora necesita formatearlo para cada red social.

**Archivos necesarios:**
- ✅ `{codigo}_video_base.mp4`

**Archivos a generar:**
- ⏳ `{codigo}_feed_16x9.mp4` (1920x1080)
- ⏳ `{codigo}_stories_9x16.mp4` (1080x1920)
- ⏳ `{codigo}_shorts_9x16.mp4` (1080x1920)
- ⏳ `{codigo}_tiktok_9x16.mp4` (1080x1920)

**Acción:** Validar Fase 7 → Formatea videos con FFmpeg/Cloudinary
**Siguiente estado:** `BLOG_POST_AWAITING`

---

### 8️⃣ **BLOG_POST_AWAITING** 🟠
**Significado:** Todo el contenido multimedia está listo, ahora necesita crear el post del blog.

**Archivos necesarios:**
- ✅ Todos los textos, imágenes y videos

**Archivos a generar:**
- ⏳ `content/posts/{codigo}/index.md` - Post de Hugo con frontmatter
- ⏳ Copia de imágenes a `content/posts/{codigo}/`

**Acción:** Validar Fase 8 → Crea post de Hugo y hace commit a Git
**Siguiente estado:** `READY_TO_PUBLISH`

---

### 9️⃣ **READY_TO_PUBLISH** 🔵
**Significado:** Todo está listo para publicar en redes sociales.

**Archivos necesarios:**
- ✅ Post del blog publicado
- ✅ Todos los assets (textos, imágenes, videos)

**Acción:** Publicar → Publica en las redes sociales seleccionadas
**Siguiente estado:** `PUBLISHED`

---

### ✅ **PUBLISHED** 🔵
**Significado:** El post ha sido publicado exitosamente en todas las plataformas.

**Checkboxes marcados:**
- ✅ Blog
- ✅ Instagram (si se publicó)
- ✅ LinkedIn (si se publicó)
- ✅ Twitter (si se publicó)
- ✅ Facebook (si se publicó)
- ✅ TikTok (si se publicó)

**Fecha Real Publicación:** Se auto-rellena con la fecha/hora actual

---

## 🔴 Estados de Error

### **ERROR**
**Significado:** Ocurrió un error en alguna fase del proceso.

**Información adicional:**
- Columna `Notas/Errores` contiene el mensaje de error
- Se debe revisar y corregir manualmente
- Puede volver a intentarse desde la fase que falló

---

## 🟡 Estados Especiales

### **{FASE}_NEEDS_REVISION** 🟡
**Significado:** El contenido de esta fase necesita revisión manual antes de continuar.

**Ejemplo:** `IMAGE_BASE_NEEDS_REVISION`
- Las imágenes se generaron pero el usuario quiere revisarlas/editarlas
- Puede regenerarse o subirse manualmente
- Una vez aprobado, se marca como `{FASE}_APPROVED`

### **{FASE}_APPROVED** 🟢
**Significado:** El contenido de esta fase ha sido revisado y aprobado por el usuario.

**Ejemplo:** `IMAGE_BASE_APPROVED`
- Las imágenes fueron revisadas y están OK
- Se puede proceder a la siguiente fase
- No se regenerará automáticamente

---

## 📊 Flujo Visual

```
BASE_TEXT_AWAITING 🟠
    ↓ [Validar Fase 1: Generar textos adaptados]
IMAGE_PROMPT_AWAITING 🟠
    ↓ [Validar Fase 2: Generar prompt de imagen]
IMAGE_BASE_AWAITING 🟠
    ↓ [Validar Fase 3: Generar imágenes con IA]
IMAGE_FORMATS_AWAITING 🟠
    ↓ [Validar Fase 4: Formatear imágenes]
VIDEO_SCRIPT_AWAITING 🟠
    ↓ [Validar Fase 5: Generar script de video]
VIDEO_BASE_AWAITING 🟠
    ↓ [Validar Fase 6: Generar video con IA]
VIDEO_FORMATS_AWAITING 🟠
    ↓ [Validar Fase 7: Formatear videos]
BLOG_POST_AWAITING 🟠
    ↓ [Validar Fase 8: Crear post de Hugo]
READY_TO_PUBLISH 🔵
    ↓ [Publicar en redes sociales]
PUBLISHED 🔵 ✅
```

---

## 🎨 Colores en Google Sheets

- 🟠 **Naranja** - `*_AWAITING` - Esperando acción
- 🟡 **Amarillo** - `*_NEEDS_REVISION` - Necesita revisión
- 🟢 **Verde** - `*_APPROVED` - Aprobado
- 🔵 **Azul claro** - `READY_TO_PUBLISH` - Listo para publicar
- 🔵 **Azul oscuro** - `PUBLISHED` - Publicado
- 🔴 **Rojo** - `ERROR` - Error

---

## 🔧 Comandos MCP Relacionados

```bash
# Ver estado actual de un post
get_post codigo="20251104-2"

# Listar todos los posts y sus estados
list_posts

# Generar contenido completo (crea post + prompt + imágenes)
generate_complete_post tema="Nutrición en Ironman" categoria="training"

# Generar solo imágenes (prompt + 4 variaciones)
generate_post_images_complete codigo="20251104-2"

# Publicar en redes sociales
publish_post codigo="20251104-2" platforms=["instagram", "linkedin"]
```

---

**Última actualización:** 2025-11-04
