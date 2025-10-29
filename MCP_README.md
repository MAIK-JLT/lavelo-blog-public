# 🤖 Lavelo Blog MCP Server

Servidor MCP que expone las funcionalidades del API Flask a IAs (Claude Desktop, Cursor, etc.)

## 📦 Instalación

```bash
# 1. Instalar dependencias
pip install -r api/requirements.txt

# 2. Asegurarse de que el API Flask está corriendo
python api/server.py
```

## 🚀 Uso

### **Opción 1: Claude Desktop**

1. **Copiar configuración:**
   ```bash
   # macOS
   cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # O editar manualmente:
   # ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Reiniciar Claude Desktop**

3. **Usar herramientas:**
   ```
   Usuario: "Lista todos los posts del blog"
   Claude: [Usa tool list_posts]
   
   Usuario: "Crea un post sobre nutrición en triatlón"
   Claude: [Usa tool create_post]
   ```

### **Opción 2: Cursor IDE**

1. **Configurar en Cursor Settings:**
   ```json
   {
     "mcp.servers": {
       "lavelo-blog": {
         "command": "python",
         "args": ["/Users/julioizquierdo/lavelo-blog/mcp_server.py"]
       }
     }
   }
   ```

2. **Usar en el chat de Cursor**

### **Opción 3: Prueba Manual**

```bash
# Ejecutar servidor
python mcp_server.py

# El servidor espera comandos MCP en stdin
```

## 🛠️ Herramientas Disponibles

### **Posts:**
- `list_posts` - Lista todos los posts
- `create_post` - Crea un nuevo post
- `get_post` - Obtiene detalles de un post
- `init_post_folders` - Inicializa carpetas en Drive

### **Imágenes:**
- `generate_image` - Genera imagen con Fal.ai (✅ soporta referencias)
- `generate_instructions_from_post` - Genera instrucciones de imagen

### **Videos:**
- `generate_video_text` - Genera video desde texto (❌ no soporta referencias)
- `generate_video_image` - Genera video desde imagen (❌ no soporta referencias)

### **Chat:**
- `chat` - Interactúa con Claude para crear contenido

## 📋 Ejemplos de Uso

### **Crear un Post:**
```
Usuario: "Crea un post sobre cómo preparar un Ironman 70.3"

Claude usa: create_post({
  "titulo": "Guía Completa para Preparar tu Primer Ironman 70.3",
  "contenido": "...",
  "categoria": "training"
})
```

### **Generar Imagen:**
```
Usuario: "Genera la imagen para el post 20251024-1"

Claude usa: generate_image({
  "codigo": "20251024-1",
  "num_images": 4
})
```

### **Generar Video:**
```
Usuario: "Genera un video de un ciclista en montaña"

Claude usa: generate_video_text({
  "prompt": "Professional cyclist riding road bike in mountain landscape",
  "resolution": "720p"
})
```

## 🔧 Arquitectura

```
┌─────────────────────┐
│   Claude Desktop    │
│   Cursor IDE        │
└──────────┬──────────┘
           │ MCP Protocol
           ▼
┌─────────────────────┐
│   mcp_server.py     │
│   (Este archivo)    │
└──────────┬──────────┘
           │ HTTP Requests
           ▼
┌─────────────────────┐
│   Flask API         │
│   (server.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Google Drive       │
│  Google Sheets      │
│  Claude API         │
│  Fal.ai             │
└─────────────────────┘
```

## ⚠️ Requisitos

1. **Flask API debe estar corriendo** en `http://localhost:5001`
2. **Credenciales configuradas** en `.env`
3. **Python 3.10+**

## 🐛 Troubleshooting

### Error: "Connection refused"
```bash
# Asegúrate de que Flask está corriendo
python api/server.py
```

### Error: "Module 'mcp' not found"
```bash
# Instala dependencias
pip install mcp
```

### Claude Desktop no ve las herramientas
```bash
# Verifica la ruta en claude_desktop_config.json
# Debe ser la ruta ABSOLUTA a mcp_server.py
```

## 📝 Notas

- **MCP Server es un wrapper ligero** - Solo traduce entre MCP Protocol y HTTP
- **No duplica lógica** - Toda la lógica está en Flask API
- **Stateless** - Cada llamada es independiente
- **URLs temporales** - Videos de Fal.ai expiran en 24-48h

## 🔗 Enlaces

- **MCP Protocol:** https://modelcontextprotocol.io
- **Flask API Docs:** http://localhost:5001/api/docs
- **Blog:** https://blog.lavelo.es
