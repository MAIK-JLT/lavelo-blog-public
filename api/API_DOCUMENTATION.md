# 📚 Lavelo Blog API - Documentación

## 🚀 Acceso a la Documentación Interactiva

Una vez el servidor esté corriendo, accede a:

**Swagger UI:** http://localhost:5001/api/docs

---

## 📋 Resumen de Endpoints

### **Posts**
- `GET /api/posts` - Obtener todos los posts
- `POST /api/posts/<codigo>/init-folders` - Inicializar carpetas en Drive
- `POST /api/posts/<codigo>/update` - Actualizar campo de un post

### **Generación de Contenido**
- `POST /api/generate-instructions-from-post` - Generar instrucciones desde post
- `POST /api/generate-base-text` - Generar texto base con Claude
- `POST /api/generate-adapted-texts` - Generar textos adaptados para redes
- `POST /api/generate-image-prompt` - Generar prompt de imagen
- `POST /api/generate-image` - Generar imagen con Fal.ai SeaDream 4.0 ✅ **Soporta referencias**

### **Imágenes (Prompt Builder)**
- `POST /api/improve-prompt-visual` - Mejorar prompt con selecciones visuales ✅ **Soporta referencias**
- `POST /api/test-fal` - Generar imágenes de prueba ✅ **Soporta referencias**

### **Videos**
- `POST /api/generate-video-text` - Generar video desde texto (SeeDance 1.0) ❌ **No soporta referencias**
- `POST /api/generate-video-image` - Generar video desde imagen (SeeDance 1.0) ❌ **No soporta referencias**
- `POST /api/format-videos` - Formatear videos para redes sociales

### **Chat con Claude**
- `POST /api/chat` - Chat interactivo con herramientas MCP

### **OAuth**
- `GET /api/oauth/status` - Estado de autenticación
- `GET /api/oauth/authorize` - Iniciar flujo OAuth
- `GET /api/oauth/callback` - Callback OAuth

---

## 🔧 Instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp config/.env.example .env
# Editar .env con tus credenciales

# 3. Ejecutar servidor
python api/server.py
```

---

## 🎯 Ejemplos de Uso

### **1. Obtener Posts**
```bash
curl http://localhost:5001/api/posts
```

**Respuesta:**
```json
{
  "success": true,
  "posts": [
    {
      "codigo": "20251024-1",
      "titulo": "Optimiza tu Posición de Triatlón",
      "estado": "IMAGE_PROMPT_AWAITING",
      "drive_folder_id": "1abc123def456"
    }
  ]
}
```

### **2. Generar Video desde Texto**
```bash
curl -X POST http://localhost:5001/api/generate-video-text \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Ciclista profesional en carretera de montaña",
    "resolution": "720p"
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "video_url": "https://fal.media/files/...",
  "duration": 45.2,
  "resolution": "1280x720"
}
```

### **3. Generar Imagen con Referencias**
```bash
curl -X POST http://localhost:5001/api/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "20251024-1",
    "num_images": 4,
    "reference_images": [
      {"url": "https://...", "weight": 0.8}
    ]
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "message": "4 imágenes generadas correctamente",
  "images": [
    {
      "filename": "20251024-1_imagen_base.png",
      "file_id": "1xyz789",
      "url": "https://fal.media/files/..."
    }
  ]
}
```

### **4. Chat con Claude**
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Mejora el prompt de imagen del post 20251024-1",
    "conversation_id": "conv_123"
  }'
```

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│   Frontend      │
│  (Panel Web)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Flask API     │
│  (server.py)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│ Google │ │   AI     │
│ Drive  │ │ Services │
│ Sheets │ │ (Claude, │
└────────┘ │ Fal.ai)  │
           └──────────┘
```

---

## 🔑 Variables de Entorno Requeridas

```bash
# Google APIs
GOOGLE_SHEETS_ID=...
GOOGLE_DRIVE_FOLDER_ID=...

# AI Services
ANTHROPIC_API_KEY=...
FAL_KEY=...
OPENAI_API_KEY=...
GOOGLE_GEMINI_API_KEY=...

# Cloudinary
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# Flask
SECRET_KEY=...
```

---

## 📊 Estados de Posts

| Estado | Descripción |
|--------|-------------|
| `TEXT_BASE_AWAITING` | Esperando generación de texto base |
| `TEXT_BASE_APPROVED` | Texto base aprobado |
| `IMAGE_PROMPT_AWAITING` | Esperando prompt de imagen |
| `IMAGE_BASE_AWAITING` | Esperando generación de imagen |
| `IMAGE_BASE_APPROVED` | Imagen base aprobada |
| `READY_TO_PUBLISH` | Listo para publicar |
| `PUBLISHED` | Publicado |

---

## 🛠️ Tecnologías

- **Backend:** Flask 3.0
- **IA:** Claude 3.5 Sonnet, Fal.ai (SeaDream 4.0, SeeDance 1.0)
- **Storage:** Google Drive, Google Sheets
- **Media:** Cloudinary, FFmpeg
- **Docs:** Swagger/Flasgger

---

## 📝 Notas

- **Swagger UI** está disponible en `/api/docs`
- **Especificación OpenAPI** en `/apispec.json`
- Todos los endpoints requieren que el servidor tenga acceso a Google Drive/Sheets
- Las URLs de videos de Fal.ai son temporales (24-48h)
- Las imágenes se guardan permanentemente en Google Drive

---

## 🔗 Enlaces

- **Blog:** https://blog.lavelo.es
- **Panel:** https://blog.lavelo.es/panel/
- **GitHub:** https://github.com/MAIK-JLT/lavelo-blog-public
