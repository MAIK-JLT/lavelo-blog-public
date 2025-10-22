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
- **Claude Haiku 4.5 (claude-haiku-4-5-20251001):** Textos adaptados y prompts (rápido y económico)
- **DALL-E 3 (OpenAI):** Generación de imágenes ($0.04/imagen 1024x1024)
- **Veo 3.1 Fast (Google):** Generación de videos (15 seg, 1080p) con API

### Procesamiento:
- **Pillow (PIL):** Crop y resize de imágenes
- **Cloudinary AI:** Smart reframing de videos con detección de sujetos

### Orquestación:
- **Panel Web HTML + Flask API:** Control manual con botones
- **Google Sheets API:** Lectura de estados y actualización
- **Google Drive API:** Almacenamiento y gestión de archivos

### Publicación:
- **Instagram Graph API**
- **LinkedIn API**
- **Twitter API v2**
- **Facebook Graph API**
- **TikTok API**
- **Hugo + GitHub + Plesk:** Blog deployment

---

## 📋 ROADMAP - PRÓXIMOS PASOS

### ✅ FASE ACTUAL: FUNDAMENTOS (COMPLETADO)
- [x] Blog Hugo funcionando en producción
- [x] Estructura de carpetas en Google Drive
- [x] MCP de Google Drive configurado
- [x] Google Sheet con estructura completa
- [x] README.md con workflow definitivo
- [x] Proyecto Google Cloud con APIs habilitadas

---

### 🔧 PASO 1: PREPARAR ESTRUCTURA LOCAL (PRÓXIMO)

**1.1 Crear carpetas en el repo local**
```bash
cd ~/lavelo-blog
mkdir -p panel/css panel/js
mkdir -p api/routes
mkdir scripts
mkdir config
```

**1.2 Crear .gitignore actualizado**
```
# Credenciales (NO SUBIR)
config/.env
config/credentials.json
config/*.json

# Python
__pycache__/
*.pyc
venv/
.venv/

# Hugo
public/
.hugo_build.lock
resources/_gen/
```

**1.3 Commit y push estructura**
```bash
git add .gitignore panel/ api/ scripts/ config/.gitignore
git commit -m "Add panel structure and scripts folders"
git push origin main
```

---

### 🎨 PASO 2: CREAR PANEL WEB BÁSICO

**2.1 Crear panel/index.html**
- Dashboard visual con estado actual
- Botones para cada fase
- Enlaces a Drive
- Visor de progreso

**2.2 Crear panel/css/style.css**
- Diseño responsive
- Colores según estados
- Iconos para cada fase

**2.3 Crear panel/js/app.js**
- Leer estado desde API
- Ejecutar acciones con clicks
- Refrescar automáticamente
- Mostrar notificaciones

---

### 🐍 PASO 3: CREAR API BACKEND

**3.1 Instalar dependencias en servidor**
```bash
# En Plesk/servidor
python3 -m venv venv
source venv/bin/activate
pip install flask google-auth google-api-python-client anthropic pillow
```

**3.2 Crear api/server.py**
- Endpoints REST para cada acción
- Autenticación básica
- Manejo de errores
- Logging

**3.3 Crear api/routes/**
- `sheets.py` - Leer/escribir Google Sheets
- `generate.py` - Ejecutar scripts de generación
- `drive.py` - Subir/leer archivos de Drive

---

### 📜 PASO 4: CREAR SCRIPTS DE AUTOMATIZACIÓN

**4.1 scripts/generate_texts.py**
- Llama a Claude API
- Genera textos adaptados desde base.txt
- Sube a Drive
- Actualiza Sheet

**4.2 scripts/generate_images.py**
- Llama a Nano Banana API
- Genera imagen desde prompt
- Sube a Drive
- Actualiza Sheet

**4.3 scripts/generate_videos.py**
- Llama a Veo 3.1 API
- Genera video base
- Sube a Drive
- Actualiza Sheet

**4.4 scripts/formatters.py**
- `format_images()` - ImageMagick para crops
- `format_videos()` - ffmpeg para recortes
- Guarda todos los formatos en Drive

**4.5 scripts/publishers.py**
- `publish_blog()` - Crea .md, compila Hugo, push Git
- `publish_instagram()` - Graph API
- `publish_linkedin()` - LinkedIn API
- `publish_twitter()` - Twitter API v2
- `publish_facebook()` - Graph API
- `publish_tiktok()` - TikTok API

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

1. **Habla con Claude** → Desarrolla idea y genera base.txt
2. **Abre panel web** → https://blog.lavelo.es/panel/
3. **Sigue el wizard visual** → Click en cada botón según fase
4. **Valida cada output** → Revisa en Drive antes de siguiente fase
5. **Programa publicación** → Establece fecha/hora en Sheet
6. **Click "Publicar"** → Va automáticamente a todas las plataformas

---

## 📞 INFORMACIÓN DEL PROYECTO

**Proyecto:** Lavelo Blog Automation  
**Inicio:** Octubre 2025  
**Última actualización:** 21 de octubre de 2025

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

---

TRANSICIONES Y ACCIONES
0 → 1: DRAFT → BASE_TEXT_AWAITING
Acción manual (fuera del panel):

Usuario crea base.txt en Drive con Claude
Usuario marca columna I = TRUE en Excel
Usuario marca columna F = BASE_TEXT_AWAITING
1 → 2: BASE_TEXT_AWAITING → ADAPTED_TEXTS_AWAITING
Acción automática:

Leer base.txt de Drive
Llamar Claude API con prompt: "Adapta este texto para Instagram, LinkedIn, Twitter, Facebook, TikTok"
Guardar 5 archivos en Drive: instagram.txt, linkedin.txt, twitter.txt, facebook.txt, tiktok.txt
Marcar columnas J-N = TRUE
Cambiar columna F = ADAPTED_TEXTS_AWAITING
2 → 3: ADAPTED_TEXTS_AWAITING → IMAGE_PROMPT_AWAITING
Acción automática:

Leer base.txt de Drive
Llamar Claude API con prompt: "Genera un prompt para crear una imagen que represente este contenido"
Guardar prompt_imagen.txt en Drive
Marcar columna O = TRUE
Cambiar columna F = IMAGE_PROMPT_AWAITING
3 → 4: IMAGE_PROMPT_AWAITING → IMAGE_BASE_AWAITING
Acción automática:

Leer prompt_imagen.txt de Drive
Llamar Gemini/DALL-E API para generar imagen
Guardar imagen_base.png en Drive
Marcar columna P = TRUE
Cambiar columna F = IMAGE_BASE_AWAITING
4 → 5: IMAGE_BASE_AWAITING → IMAGE_FORMATS_AWAITING
Acción automática:

Leer imagen_base.png de Drive
Redimensionar a 5 formatos:
instagram_1x1.png (1080x1080)
instagram_stories.png (1080x1920)
linkedin.png (1200x627)
twitter.png (1200x675)
facebook.png (1200x630)
Guardar en Drive
Marcar columnas Q-U = TRUE
Cambiar columna F = IMAGE_FORMATS_AWAITING
5 → 6: IMAGE_FORMATS_AWAITING → VIDEO_PROMPT_AWAITING
Acción automática:

Leer base.txt de Drive
Llamar Claude API con prompt: "Genera un script de video de 15 seg con 4 escenas sobre este tema"
Guardar script_video.txt en Drive
Marcar columna V = TRUE
Cambiar columna F = VIDEO_PROMPT_AWAITING
6 → 7: VIDEO_PROMPT_AWAITING → VIDEO_BASE_AWAITING
Acción automática:

Leer script_video.txt + imagen_base.png de Drive
Llamar API de video (Veo 3.1 o alternativa)
Generar video base (16x9, 15 seg, 4 escenas)
Guardar video_base.mp4 en Drive
Marcar columna W = TRUE
Cambiar columna F = VIDEO_BASE_AWAITING
7 → 8: VIDEO_BASE_AWAITING → VIDEO_FORMATS_AWAITING
Acción automática:

Leer video_base.mp4 de Drive
Subir a Cloudinary
Generar 4 formatos con AI smart reframing (gravity: auto:subject):
feed_16x9.mp4 (1920x1080)
stories_9x16.mp4 (1080x1920)
shorts_9x16.mp4 (1080x1920)
tiktok_9x16.mp4 (1080x1920)
Descargar y guardar en Drive
Marcar columnas X-AA = TRUE
Cambiar columna F = VIDEO_FORMATS_AWAITING
8 → 9: VIDEO_FORMATS_AWAITING → READY_TO_PUBLISH
Acción automática:

Verificar que todos los archivos existen en Drive
Cambiar columna F = READY_TO_PUBLISH
9 → 10: READY_TO_PUBLISH → PUBLISHED
Acción semi-automática:

Publicar en Blog (Hugo)
Publicar en Instagram (API)
Publicar en LinkedIn (API)
Publicar en Twitter (API)
Publicar en Facebook (API)
Publicar en TikTok (API)
Marcar columnas AB-AF = TRUE
Cambiar columna F = PUBLISHED
📊 RESUMEN:
Transición	Tipo	Herramienta	Tiempo estimado
0→1	Manual	Claude chat	10-20 min
1→2	Auto	Claude API	30 seg
2→3	Auto	Claude API	15 seg
3→4	Auto	Gemini API	30 seg
4→5	Auto	Python/PIL	5 seg
5→6	Auto	Claude API	15 seg
6→7	Auto	API video	2-5 min
7→8	Auto	FFmpeg	30 seg
8→9	Auto	Validación	1 seg
9→10	Semi-auto	APIs redes	1 min

**📌 IMPORTANTE:** Este documento es la fuente de verdad del proyecto. Claude debe leer este README al comenzar cualquier sesión de trabajo en el proyecto Lavelo Blog para mantener el contexto completo del sistema.