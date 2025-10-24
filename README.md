# 🚴 LAVELO BLOG - SISTEMA DE AUTOMATIZACIÓN DE CONTENIDO

## 📋 OBJETIVO DEL PROYECTO

Sistema automatizado end-to-end para crear y publicar contenido semanal de triatlón en:
- Blog (Hugo - blog.lavelo.es)
- Redes sociales (Instagram, LinkedIn, Twitter, Facebook, TikTok)

---

## 🏗️ ARQUITECTURA ACTUAL

### 1. REPOSITORIO ÚNICO
- **Repo local:** `~/lavelo-blog/`
- **Repo GitHub:** https://github.com/MAIK-JLT/lavelo-blog-public
- **Producción blog:** https://blog.lavelo.es
- **Panel de control:** https://blog.lavelo.es/panel/ (pendiente)

### 2. ESTRUCTURA DEL REPOSITORIO

```
~/lavelo-blog/
├── archetypes/
├── assets/
├── content/              # Posts del blog Hugo
│   └── posts/
│       ├── en/
│       └── es/
├── data/
├── i18n/
├── layouts/
├── static/
├── themes/
│   └── PaperMod/
├── public/               # Generado por Hugo (se sube a Git)
├── panel/                # Panel de control web (NUEVO - PENDIENTE)
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── api/                  # Backend para el panel (NUEVO - PENDIENTE)
│   ├── server.py
│   └── routes/
│       ├── sheets.py
│       ├── generate.py
│       └── drive.py
├── scripts/              # Scripts de automatización (NUEVO - PENDIENTE)
│   ├── generate_texts.py
│   ├── generate_images.py
│   ├── generate_videos.py
│   ├── formatters.py
│   └── publishers.py
├── config/               # Configuración y credenciales (NUEVO - PENDIENTE)
│   └── .env             # NO SE SUBE A GIT
├── hugo.toml
├── .gitignore
└── README.md
```

### 3. GOOGLE DRIVE (Almacenamiento)
- **Carpeta base:** `Lavelo Blog Content/Posts/2025/`
- **Estructura por meses:** 12 carpetas (01-Enero hasta 12-Diciembre)
- **Estructura por posts:** Ver sección "Nomenclatura"

### 4. GOOGLE SHEETS (Base de Datos y Dashboard)
- **Sheet:** "Lavelo Blog - Content Calendar"
- **Función:** Control de estados, validaciones y publicación programada
- **Ver:** [Abrir Content Calendar](https://docs.google.com/spreadsheets/d/1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug/edit)

---

## 📝 NOMENCLATURA DE ARCHIVOS Y CARPETAS

### CÓDIGO DE POST
Formato: **`YYYYMMDD-ref`**

Donde:
- `YYYY` = Año (4 dígitos)
- `MM` = Mes (2 dígitos, con cero inicial)
- `DD` = Día (2 dígitos, con cero inicial)
- `ref` = Número de referencia del 1-9 (para múltiples posts el mismo día)

**Ejemplos:**
- `20251020-1` → Primer post del 20 de octubre de 2025
- `20251020-2` → Segundo post del mismo día
- `20251125-1` → Primer post del 25 de noviembre de 2025

### ESTRUCTURA DE CARPETAS POR POST

```
[MES]/
└── [CÓDIGO-POST]/
    ├── textos/
    │   ├── [CÓDIGO]_base.txt
    │   ├── [CÓDIGO]_instagram.txt
    │   ├── [CÓDIGO]_linkedin.txt
    │   ├── [CÓDIGO]_twitter.txt
    │   ├── [CÓDIGO]_facebook.txt
    │   ├── [CÓDIGO]_tiktok.txt
    │   ├── [CÓDIGO]_prompt_imagen_base.txt
    │   └── [CÓDIGO]_script_video_base.txt
    ├── imagenes/
    │   ├── [CÓDIGO]_imagen_base.png
    │   ├── [CÓDIGO]_instagram_1x1.png
    │   ├── [CÓDIGO]_instagram_stories_9x16.png
    │   ├── [CÓDIGO]_linkedin_16x9.png
    │   ├── [CÓDIGO]_twitter_16x9.png
    │   └── [CÓDIGO]_facebook_16x9.png
    └── videos/
        ├── [CÓDIGO]_video_base.mp4
        ├── [CÓDIGO]_feed_16x9.mp4
        ├── [CÓDIGO]_stories_9x16.mp4
        ├── [CÓDIGO]_shorts_9x16.mp4
        └── [CÓDIGO]_tiktok_9x16.mp4
```

**Ejemplo completo:**
```
10-Octubre/
└── 20251020-1/
    ├── textos/
    │   ├── 20251020-1_base.txt
    │   ├── 20251020-1_instagram.txt
    │   ├── 20251020-1_linkedin.txt
    │   ├── 20251020-1_twitter.txt
    │   ├── 20251020-1_facebook.txt
    │   ├── 20251020-1_tiktok.txt
    │   ├── 20251020-1_prompt_imagen_base.txt
    │   └── 20251020-1_script_video_base.txt
    ├── imagenes/
    │   ├── 20251020-1_imagen_base.png
    │   ├── 20251020-1_instagram_1x1.png
    │   ├── 20251020-1_instagram_stories_9x16.png
    │   ├── 20251020-1_linkedin_16x9.png
    │   ├── 20251020-1_twitter_16x9.png
    │   └── 20251020-1_facebook_16x9.png
    └── videos/
        ├── 20251020-1_video_base.mp4
        ├── 20251020-1_feed_16x9.mp4
        ├── 20251020-1_stories_9x16.mp4
        ├── 20251020-1_shorts_9x16.mp4
        └── 20251020-1_tiktok_9x16.mp4
```

### FORMATO DE NOMBRES DE ARCHIVOS

**Patrón:** `[CÓDIGO]_[TIPO]_[ASPECTO].[EXTENSIÓN]`

Donde:
- `[CÓDIGO]` = YYYYMMDD-ref del post
- `[TIPO]` = Tipo de contenido o plataforma
- `[ASPECTO]` = Ratio de aspecto (solo para imágenes/videos)
- `[EXTENSIÓN]` = Formato del archivo

**Ratios de aspecto:**
- `1x1` → Cuadrado (Instagram feed principal)
- `16x9` → Horizontal (LinkedIn, Twitter, Facebook, YouTube)
- `9x16` → Vertical (Instagram/Facebook Stories, Reels, TikTok, Shorts)

---

## 🔄 WORKFLOW COMPLETO CON VALIDACIÓN EN CASCADA

### FILOSOFÍA
Cada fase requiere **validación humana** antes de proceder a la siguiente, evitando desperdiciar recursos en regeneraciones completas.

### HERRAMIENTAS
- **Fases creativas (1-7):** Usuario + Claude en chat (manual)
- **Fases mecánicas (formateos/publicación):** Scripts Python con botones en panel web

---

### **FASE 1: TEXTO BASE**
```
Usuario + Claude (manual) → Crea base.txt en Drive
Estado: DRAFT → BASE_TEXT_AWAITING
        ↓
Usuario revisa y valida base.txt en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Generar Textos Adaptados"]
        ↓
Script Python genera automáticamente:
├─ instagram.txt
├─ linkedin.txt
├─ twitter.txt
├─ facebook.txt
└─ tiktok.txt
Actualiza Sheet → ADAPTED_TEXTS_AWAITING
```

**Si necesita revisión:**
- Usuario indica qué está mal (en Sheet o panel)
- Claude regenera con feedback
- Vuelve a validación

---

### **FASE 2: TEXTOS ADAPTADOS**
```
Estado: ADAPTED_TEXTS_AWAITING
        ↓
Usuario revisa todos los textos adaptados en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Generar Prompt Imagen"]
        ↓
Claude genera:
└─ prompt_imagen_base.txt (<900 caracteres)
Actualiza Sheet → IMAGE_PROMPT_AWAITING
```

---

### **FASE 3: PROMPT IMAGEN**
```
Estado: IMAGE_PROMPT_AWAITING
        ↓
Usuario revisa prompt de imagen en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Generar Imagen Base"]
        ↓
Script llama a Nano Banana API:
└─ Gemini 2.5 Flash → imagen_base.png
Sube a Drive, actualiza Sheet → IMAGE_BASE_AWAITING
```

---

### **FASE 4: IMAGEN BASE**
```
Estado: IMAGE_BASE_AWAITING
        ↓
Usuario revisa imagen_base.png en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Formatear Imágenes"]
        ↓
Script genera automáticamente (ImageMagick):
├─ instagram_1x1.png (crop/resize)
├─ instagram_stories_9x16.png
├─ linkedin_16x9.png
├─ twitter_16x9.png
└─ facebook_16x9.png
Actualiza Sheet → IMAGE_FORMATS_AWAITING
```

---

### **FASE 5: FORMATOS IMAGEN**
```
Estado: IMAGE_FORMATS_AWAITING
        ↓
Usuario revisa todos los crops/formatos en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Generar Script Video"]
        ↓
Claude genera:
└─ script_video_base.txt (15 seg, 4 escenas con narración)
Actualiza Sheet → VIDEO_PROMPT_AWAITING
```

---

### **FASE 6: PROMPT VIDEO**
```
Estado: VIDEO_PROMPT_AWAITING
        ↓
Usuario revisa script/prompt del video en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Generar Video Base"]
        ↓
Script llama a Veo 3.1 API:
└─ Con script → video_base.mp4 (15 seg, 1080p, 16:9)
Sube a Drive, actualiza Sheet → VIDEO_BASE_AWAITING
```

---

### **FASE 7: VIDEO BASE**
```
Estado: VIDEO_BASE_AWAITING
        ↓
Usuario revisa video_base.mp4 en Drive
        ↓ SI APRUEBA
[CLICK en panel: "Formatear Videos"]
        ↓
Script genera automáticamente (ffmpeg):
├─ feed_16x9.mp4
├─ stories_9x16.mp4 (crop)
├─ shorts_9x16.mp4 (crop)
└─ tiktok_9x16.mp4 (crop)
Actualiza Sheet → VIDEO_FORMATS_AWAITING
```

---

### **FASE 8: FORMATOS VIDEO**
```
Estado: VIDEO_FORMATS_AWAITING
        ↓
Usuario revisa todos los formatos de video en Drive
        ↓ SI APRUEBA
Estado → READY_TO_PUBLISH
```

---

### **FASE 9: PUBLICACIÓN PROGRAMADA** 🚀
```
Usuario configura en Sheet:
├─ Fecha Programada: 2025-10-25
└─ Hora Programada: 09:00
        ↓
Estado: READY_TO_PUBLISH (esperando)
        ↓
[CLICK en panel: "Publicar Ahora" o espera a fecha/hora]
        ↓
Script publica:
├─ Blog (genera .md en Hugo, compila, push a Git)
├─ Instagram (Graph API)
├─ LinkedIn (API)
├─ Twitter (API v2)
├─ Facebook (Graph API)
└─ TikTok (API)
Actualiza Sheet → PUBLISHED ✅
```

---

## 🎯 ESTADOS DEL SISTEMA

```
DRAFT                          → En desarrollo manual
BASE_TEXT_AWAITING             → ⏸️ Espera validación texto base
BASE_TEXT_NEEDS_REVISION       → 🔄 Regenerando texto base
BASE_TEXT_APPROVED             → ✅ Texto base aprobado
ADAPTED_TEXTS_AWAITING         → ⏸️ Espera validación textos adaptados
ADAPTED_TEXTS_NEEDS_REVISION   → 🔄 Regenerando textos adaptados
TEXTS_APPROVED                 → ✅ Todos los textos aprobados
IMAGE_PROMPT_AWAITING          → ⏸️ Espera validación prompt imagen
IMAGE_PROMPT_NEEDS_REVISION    → 🔄 Regenerando prompt imagen
IMAGE_PROMPT_APPROVED          → ✅ Prompt imagen aprobado
IMAGE_BASE_AWAITING            → ⏸️ Espera validación imagen base
IMAGE_BASE_NEEDS_REVISION      → 🔄 Regenerando imagen base
IMAGE_BASE_APPROVED            → ✅ Imagen base aprobada
IMAGE_FORMATS_AWAITING         → ⏸️ Espera validación formatos imagen
IMAGE_FORMATS_NEEDS_REVISION   → 🔄 Regenerando formatos imagen
IMAGES_APPROVED                → ✅ Todas las imágenes aprobadas
VIDEO_PROMPT_AWAITING          → ⏸️ Espera validación prompt video
VIDEO_PROMPT_NEEDS_REVISION    → 🔄 Regenerando prompt video
VIDEO_PROMPT_APPROVED          → ✅ Prompt video aprobado
VIDEO_BASE_AWAITING            → ⏸️ Espera validación video base
VIDEO_BASE_NEEDS_REVISION      → 🔄 Regenerando video base
VIDEO_BASE_APPROVED            → ✅ Video base aprobado
VIDEO_FORMATS_AWAITING         → ⏸️ Espera validación formatos video
VIDEO_FORMATS_NEEDS_REVISION   → 🔄 Regenerando formatos video
READY_TO_PUBLISH               → ⏳ Esperando fecha/hora programada
PUBLISHING                     → 🚀 Publicando en plataformas
PUBLISHED                      → 🎉 Completado
ERROR                          → ❌ Error (ver Notas)
```

---

## 📊 ESTRUCTURA DEL GOOGLE SHEET

### Columnas:
```
A: Fecha Programada
B: Hora Programada (HH:MM)
C: Código Post (YYYYMMDD-ref)
D: Título
E: Idea/Brief
F: ESTADO (dropdown con todos los estados)
G: Drive Folder ID
H: URLs (separadas por comas)

TEXTOS (checkboxes):
I: ☑ base.txt
J: ☑ instagram.txt
K: ☑ linkedin.txt
L: ☑ twitter.txt
M: ☑ facebook.txt
N: ☑ tiktok.txt
O: ☑ prompt_imagen_base.txt

IMÁGENES (checkboxes):
P: ☑ imagen_base.png
Q: ☑ instagram_1x1.png
R: ☑ instagram_stories_9x16.png
S: ☑ linkedin_16x9.png
T: ☑ twitter_16x9.png
U: ☑ facebook_16x9.png

VIDEOS (checkboxes):
V: ☑ script_video_base.txt
W: ☑ video_base.mp4
X: ☑ feed_16x9.mp4
Y: ☑ stories_9x16.mp4
Z: ☑ shorts_9x16.mp4
AA: ☑ tiktok_9x16.mp4

PUBLICACIÓN (checkboxes):
AB: ☑ Blog
AC: ☑ Instagram
AD: ☑ LinkedIn
AE: ☑ Twitter
AF: ☑ Facebook
AG: ☑ TikTok

CONTROL:
AH: Fecha Real Publicación (auto-rellenado)
AI: Notas/Errores
AJ: Feedback (para regeneraciones)
```

### Conditional Formatting:
```
Estados "*_AWAITING" → 🟠 Naranja (requiere acción del usuario)
Estados "*_NEEDS_REVISION" → 🟡 Amarillo (regenerando)
Estados "*_APPROVED" → 🟢 Verde (fase completada)
Estado "READY_TO_PUBLISH" → 🔵 Azul claro (esperando)
Estado "PUBLISHED" → 🔵 Azul oscuro (completado)
Estado "ERROR" → 🔴 Rojo (revisar)
```

---

## 🛠️ HERRAMIENTAS Y TECNOLOGÍA

### Generación de Contenido:
- **Claude 3.5 Sonnet (claude-3-5-sonnet-20241022):** Chat integrado, creación de posts, mejora de prompts
- **Claude Haiku 4.5 (claude-haiku-4-5-20251001):** Textos adaptados y prompts (rápido y económico)
- **DALL-E 3 (OpenAI):** Generación de imágenes ($0.04/imagen 1024x1024)
- **Veo 3.1 Fast (Google):** Generación de videos (15 seg, 1080p) con API

### Procesamiento:
- **Pillow (PIL):** Crop y resize de imágenes
- **FFmpeg:** Procesamiento y conversión de videos
- **Cloudinary AI:** Smart reframing de videos con detección de sujetos

### Backend:
- **Flask:** API REST para el panel web
- **Python 3.13:** Lenguaje principal
- **Google Sheets API:** Lectura de estados y actualización
- **Google Drive API:** Almacenamiento y gestión de archivos
- **Anthropic API:** Integración con Claude

### Frontend:
- **HTML5 + CSS3:** Interfaz del panel
- **JavaScript (Vanilla):** Lógica del cliente
- **Fetch API:** Comunicación con backend
- **LocalStorage:** Persistencia de datos del cliente

### Publicación:
- **Instagram Graph API**
- **LinkedIn API**
- **Twitter API v2**
- **Facebook Graph API**
- **TikTok API**
- **Hugo + GitHub + Plesk:** Blog deployment

---

## 🎨 FUNCIONALIDADES DEL PANEL WEB

### **Panel Principal (index.html)**
- ✅ Vista de todos los posts desde Google Sheets
- ✅ Selector de posts con navegación
- ✅ Visualización de 9 fases del workflow
- ✅ Estados visuales: 🔒 Pendiente / 📋 Activo / ✅ Validado
- ✅ Botones "Ver Detalles" en TODAS las fases (activas y completadas)
- ✅ Botón "VALIDATE" para avanzar a siguiente fase
- ✅ Widget de chat con Claude (flotante, siempre accesible)

### **Vista de Detalles (details.html)**
- ✅ Edición de contenido por fase
- ✅ Guardado individual de textos en Drive
- ✅ Detección de cambios (botón "Guardar" solo si hay modificaciones)
- ✅ Preview de imágenes desde Drive
- ✅ **Subida manual de imágenes** (alternativa a generación con IA)
  - Formatos: PNG, JPG, JPEG
  - Máximo: 10MB
  - Sin validación de dimensiones
  - Preview antes de confirmar
  - Overlay con spinner durante subida
- ✅ **Sistema de advertencia para editar fases validadas**
  - Modal con lista de fases que se resetearán
  - Botones: "Cancelar" (vuelve al panel) / "Continuar" (permite editar)
  - Reseteo automático de fases dependientes al guardar
- ✅ Chat integrado en cada fase para mejoras con IA

### **Chat con Claude**
- ✅ Conversación persistente (se mantiene entre aperturas)
- ✅ Historial de mensajes
- ✅ Herramientas MCP disponibles:
  - `create_post()` - Crear nuevo post
  - `list_posts()` - Listar posts existentes
  - `update_image_prompt()` - Actualizar prompt sin regenerar
  - `update_video_script()` - Actualizar script de video
  - `regenerate_image()` - Actualizar prompt Y marcar para regenerar imagen
- ✅ System prompt optimizado (breve, ejecutivo, proactivo)
- ✅ Confirmación explícita antes de guardar cambios
- ✅ Feedback visual de acciones ejecutadas

### **Mejora de Prompts con IA**
- ✅ Botón "✨ Mejorar con IA" en Fase 3 (Prompt Imagen) y Fase 6 (Script Video)
- ✅ Botón "🔄 Regenerar con IA" en Fase 4 (Imagen ya generada)
- ✅ Botón "📤 Reemplazar con mi Imagen" en Fase 4
- ✅ Contexto automático: Claude recibe el contenido actual
- ✅ Flujo conversacional: Claude pregunta qué mejorar
- ✅ Regeneración inteligente: Si cambias prompt, se resetean fases posteriores

### **Subida Manual de Imágenes**
**Fase 3 (Prompt de Imagen):**
- Opción "— O —" para subir imagen propia
- Evita necesidad de generar con IA
- Crea prompt placeholder con metadatos

**Fase 4 (Imagen Generada):**
- Botón "Reemplazar con mi Imagen"
- Útil si la IA no generó lo esperado
- Reemplaza imagen y prompt

**Flujo:**
1. Click "Seleccionar Imagen"
2. Preview de la imagen
3. Validación: formato (PNG/JPG) y tamaño (<10MB)
4. Click "Confirmar y Subir"
5. Overlay con spinner: "Guardando en Google Drive..."
6. Imagen se guarda como `imagen_base.png`
7. Prompt placeholder se crea automáticamente
8. Checkboxes se actualizan
9. Estado cambia a `IMAGE_BASE_AWAITING`

### **Edición de Fases Validadas**
**Problema resuelto:** Antes no podías volver a editar fases ya completadas.

**Solución implementada:**
1. Todas las fases (validadas o no) tienen botón "Ver Detalles"
2. Al abrir una fase validada, aparece modal de advertencia
3. Modal muestra qué fases se resetearán si guardas cambios
4. Usuario decide: "Cancelar" o "Continuar"
5. Si continúa y guarda, se resetean automáticamente las fases dependientes

**Mapeo de dependencias:**
```
Fase 1 (Texto Base) → Resetea: 2, 3, 4, 5, 6, 7, 8
Fase 2 (Textos Adaptados) → No resetea nada
Fase 3 (Prompt Imagen) → Resetea: 4, 5
Fase 4 (Imagen Base) → Resetea: 5
Fase 5 (Formatos Imagen) → No resetea nada
Fase 6 (Script Video) → Resetea: 7, 8
Fase 7 (Video Base) → Resetea: 8
Fase 8 (Formatos Video) → No resetea nada
```

**Ejemplo:**
- Tienes Fase 3, 4 y 5 validadas ✅
- Quieres cambiar el prompt de imagen (Fase 3)
- Click "Ver Detalles" en Fase 3
- Modal: "⚠️ Se resetearán: Fase 4 (Imagen Base), Fase 5 (Formatos)"
- Click "Continuar"
- Editas el prompt
- Click "Guardar"
- Backend resetea automáticamente:
  - `image_base = FALSE`
  - `instagram_image = FALSE` (y demás formatos)
  - Estado vuelve a `IMAGE_PROMPT_AWAITING`
- Mensaje: "✅ Cambios guardados. Fases posteriores reseteadas."
- Vuelves al panel y haces VALIDATE para regenerar

---

## 📋 ROADMAP - PRÓXIMOS PASOS

### ✅ FASE ACTUAL: PANEL WEB OPERATIVO (COMPLETADO)
- [x] Blog Hugo funcionando en producción
- [x] Estructura de carpetas en Google Drive
- [x] MCP de Google Drive configurado
- [x] Google Sheet con estructura completa
- [x] README.md con workflow definitivo
- [x] Proyecto Google Cloud con APIs habilitadas
- [x] Panel web HTML + CSS + JavaScript funcionando
- [x] Backend Flask con API REST completa
- [x] Integración con Google Sheets y Drive
- [x] Chat con Claude para crear y mejorar contenido
- [x] Sistema de validación y edición de fases completadas
- [x] Subida manual de imágenes (alternativa a IA)
- [x] Regeneración de prompts con IA
- [x] Reseteo automático de fases dependientes

---

### 🎯 PRÓXIMOS PASOS

### 🔧 PASO 1: GENERACIÓN AUTOMÁTICA DE CONTENIDO (PRÓXIMO)

**Objetivo:** Implementar botones VALIDATE que ejecuten scripts de generación automática.

**1.1 Implementar generación de textos adaptados**
- Script que lee `base.txt` desde Drive
- Llama a Claude API para adaptar a cada red social
- Guarda 5 archivos: instagram.txt, linkedin.txt, twitter.txt, facebook.txt, tiktok.txt
- Actualiza checkboxes en Sheet
- Cambia estado a `ADAPTED_TEXTS_AWAITING`

**1.2 Implementar generación de prompt de imagen**
- Lee `base.txt` desde Drive
- Claude genera prompt optimizado (<900 caracteres)
- Guarda `prompt_imagen.txt` en Drive
- Actualiza Sheet

**1.3 Implementar generación de imagen base**
- Lee `prompt_imagen.txt`
- Llama a DALL-E 3 / Gemini API
- Guarda `imagen_base.png` (1024x1024)
- Actualiza Sheet

**1.4 Implementar formateo de imágenes**
- Lee `imagen_base.png`
- Usa Pillow para generar 5 formatos:
  - instagram_1x1.png (1080x1080)
  - instagram_stories_9x16.png (1080x1920)
  - linkedin_16x9.png (1200x627)
  - twitter_16x9.png (1200x675)
  - facebook_16x9.png (1200x630)
- Guarda en Drive
- Actualiza Sheet

**1.5 Implementar generación de script de video**
- Lee `base.txt`
- Claude genera script de 15 seg con 4 escenas
- Guarda `script_video.txt`
- Actualiza Sheet

**1.6 Implementar generación de video base**
- Lee `script_video.txt`
- Llama a Veo 3.1 API
- Genera video 16:9, 1080p, 15 seg
- Guarda `video_base.mp4`
- Actualiza Sheet

**1.7 Implementar formateo de videos**
- Lee `video_base.mp4`
- Usa FFmpeg para generar 4 formatos:
  - feed_16x9.mp4 (1920x1080)
  - stories_9x16.mp4 (1080x1920, crop)
  - shorts_9x16.mp4 (1080x1920, crop)
  - tiktok_9x16.mp4 (1080x1920, crop)
- Guarda en Drive
- Actualiza Sheet

---

### 🚀 PASO 2: PUBLICACIÓN AUTOMÁTICA

**Objetivo:** Implementar publicación en todas las plataformas desde el panel.

**2.1 Publicación en Blog (Hugo)**
- Generar archivo .md con frontmatter
- Copiar imágenes a carpeta static
- Compilar Hugo (`hugo`)
- Commit y push a GitHub
- Webhook a Plesk para deploy

**2.2 Publicación en Instagram**
- Instagram Graph API
- Subir imagen + caption
- Programar publicación

**2.3 Publicación en LinkedIn**
- LinkedIn API
- Crear post con imagen
- Compartir en perfil/página

**2.4 Publicación en Twitter/X**
- Twitter API v2
- Tweet con imagen
- Manejo de hilos si es necesario

**2.5 Publicación en Facebook**
- Facebook Graph API
- Post en página
- Programar publicación

**2.6 Publicación en TikTok**
- TikTok API
- Subir video
- Añadir descripción y hashtags

---

### 🔐 PASO 5: CONFIGURAR CREDENCIALES

**5.1 Crear config/.env**
```bash
# Claude
CLAUDE_API_KEY=sk-xxx

# Google
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_SHEET_ID=1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug

# Gemini (Nano Banana)
GEMINI_API_KEY=xxx

# Veo 3.1
VEO_API_KEY=xxx

# Social Media
INSTAGRAM_ACCESS_TOKEN=xxx
LINKEDIN_ACCESS_TOKEN=xxx
TWITTER_API_KEY=xxx
FACEBOOK_ACCESS_TOKEN=xxx
TIKTOK_ACCESS_TOKEN=xxx
```

**5.2 Copiar credenciales OAuth de Google**
```bash
cp ~/.config/google-drive-mcp/gcp-oauth.keys.json config/credentials.json
```

---

### 🚀 PASO 6: DEPLOY Y PRUEBAS

**6.1 Subir a Git**
```bash
git add .
git commit -m "Add complete automation system"
git push origin main
```

**6.2 Deploy en Plesk**
- Pull Now → Deploy Now
- Configurar Python en servidor
- Probar acceso a https://blog.lavelo.es/panel/

**6.3 Proteger con contraseña**
```
# .htaccess en /panel/
AuthType Basic
AuthName "Panel de Control"
AuthUserFile /path/to/.htpasswd
Require valid-user
```

**6.4 Test end-to-end**
- Crear post de prueba en Sheet
- Ir fase por fase
- Validar cada output
- Publicar en modo test

---

### 🎯 PASO 7: OBTENER API KEYS DE REDES SOCIALES

**7.1 Instagram**
- Facebook Developer Console
- Crear app
- Permisos: instagram_basic, instagram_content_publish

**7.2 LinkedIn**
- LinkedIn Developer
- Crear app
- OAuth 2.0 flow

**7.3 Twitter**
- Twitter Developer Portal
- API v2 con write permissions

**7.4 Facebook**
- Facebook Developer
- Pages API

**7.5 TikTok**
- TikTok Developer Portal
- Content Posting API

---

### ⚡ PASO 8: OPTIMIZACIONES FUTURAS

- [ ] Webhooks para notificaciones
- [ ] Métricas de publicaciones
- [ ] A/B testing de contenidos
- [ ] Plantillas de posts
- [ ] Integración con analytics
- [ ] Multi-idioma automático (EN/ES/FR/DE)

---

## 🎓 CÓMO USAR ESTE SISTEMA

### Para crear un nuevo post:

1. **Abre el panel web** → http://localhost:5001 (desarrollo) o https://blog.lavelo.es/panel/ (producción)
2. **Click en el chat flotante** → Icono 💬 en la esquina inferior derecha
3. **Habla con Claude** → "Quiero crear un post sobre [tema]"
4. **Claude te guía** → Te hace preguntas y genera el contenido
5. **Confirma creación** → Claude ejecuta `create_post()` y crea carpetas en Drive
6. **Navega por las fases** → Usa los botones "Ver Detalles" y "VALIDATE"
7. **Edita si es necesario** → Puedes volver a cualquier fase y editarla
8. **Mejora con IA** → Usa botones "✨ Mejorar con IA" para optimizar prompts
9. **Sube imágenes propias** → Alternativa a generación con IA
10. **Valida cada fase** → Click "VALIDATE" para avanzar
11. **Publica** → Cuando llegues a READY_TO_PUBLISH, click "Publicar"

### Funcionalidades clave:

**Chat con Claude:**
- Siempre disponible (icono flotante)
- Conversación persistente
- Puede crear posts, listar posts, mejorar prompts
- Pide confirmación antes de guardar

**Edición de fases validadas:**
- Puedes volver a cualquier fase completada
- Sistema de advertencia te avisa qué se reseteará
- Reseteo automático de fases dependientes

**Subida manual de imágenes:**
- Alternativa a generación con IA
- Formatos: PNG, JPG (máx 10MB)
- Preview antes de confirmar
- Feedback visual durante subida

**Mejora de prompts con IA:**
- Botones específicos en cada fase
- Claude analiza y mejora el contenido
- Regeneración inteligente de fases posteriores

---

## 📞 INFORMACIÓN DEL PROYECTO

**Proyecto:** Lavelo Blog Automation  
**Inicio:** Octubre 2025  
**Última actualización:** 23 de octubre de 2025

**Google Cloud:**
- Proyecto: `lavelo-blog-automation`
- APIs habilitadas: Drive, Docs, Sheets, Slides
- Modo: Testing (usuarios de prueba configurados)

**Credenciales:**
- OAuth tokens: `~/.config/google-drive-mcp/`
- Tokens se refrescan automáticamente cada 7 días

---

## 🔐 PRINCIPIOS DE DISEÑO

1. **Validación en cascada:** Cada fase valida antes de proceder
2. **Regeneración selectiva:** Solo se regenera lo que falló
3. **Eficiencia de recursos:** No gastar en generaciones innecesarias
4. **Control total:** Usuario aprueba cada elemento crítico
5. **Publicación programada:** Posts salen en fecha/hora exacta
6. **Trazabilidad:** Todos los estados quedan registrados en Sheet
7. **Simplicidad:** Botones en lugar de cron jobs o timers complejos
8. **Accesibilidad:** Panel web disponible desde cualquier dispositivo
9. **Sin dependencias externas:** Todo en el propio servidor

