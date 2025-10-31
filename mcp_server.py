#!/usr/bin/env python3
"""
MCP Server para Lavelo Blog
Expone las funcionalidades del API Flask a IAs (Claude, Cursor, etc.)
"""

import asyncio
import requests
import sys
import logging
from typing import Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configurar logging a archivo
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Configuración
API_BASE_URL = "http://localhost:5001"

# Crear servidor MCP
server = Server("lavelo-blog")

logger.info("🚀 MCP Server iniciado")

# ============================================
# TOOLS - Posts
# ============================================

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista todas las herramientas disponibles"""
    return [
        Tool(
            name="generate_complete_post",
            description="🚀 HERRAMIENTA MAESTRA: Genera un post completo de principio a fin. Crea tema (si no se da), genera título y contenido profesional sobre triatlón, crea el post en Google Sheets + Drive, genera prompt de imagen optimizado, genera 4 variaciones de imagen con IA, y guarda todo. Es la forma más rápida de crear contenido de calidad.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tema": {
                        "type": "string",
                        "description": "Tema del post (OPCIONAL). Si no se proporciona, se genera automáticamente un tema relevante sobre triatlón/ciclismo. Ejemplos: 'Nutrición en Ironman 70.3', 'Técnicas de escalada'"
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Categoría del post",
                        "enum": ["training", "racing", "training-science"],
                        "default": "training"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="list_posts",
            description="Obtiene la lista de todos los posts del blog desde Google Sheets",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_post",
            description="Obtiene los detalles de un post específico por su código",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post (formato: YYYYMMDD-N)"
                    }
                },
                "required": ["codigo"]
            }
        ),
        Tool(
            name="init_post_folders",
            description="Inicializa la estructura de carpetas (textos, imagenes, videos) en Drive para un post",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post"
                    }
                },
                "required": ["codigo"]
            }
        ),
        Tool(
            name="generate_image",
            description="Genera imagen base para un post usando Fal.ai SeaDream 4.0 (soporta hasta 2 referencias)",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post"
                    },
                    "num_images": {
                        "type": "integer",
                        "description": "Número de variaciones a generar (1-4)",
                        "default": 4
                    }
                },
                "required": ["codigo"]
            }
        ),
        Tool(
            name="generate_video_text",
            description="Genera video desde texto usando SeeDance 1.0 Pro (NO soporta referencias)",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Descripción del video a generar"
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Resolución del video (720p o 1024p)",
                        "enum": ["720p", "1024p"],
                        "default": "720p"
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="generate_video_image",
            description="Genera video desde imagen usando SeeDance 1.0 Pro (NO soporta referencias adicionales)",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Descripción del movimiento/animación"
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL de la imagen base a animar"
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Resolución del video (720p o 1024p)",
                        "enum": ["720p", "1024p"],
                        "default": "720p"
                    }
                },
                "required": ["prompt", "image_url"]
            }
        ),
        Tool(
            name="chat",
            description="Interactúa con Claude para crear o mejorar contenido del post",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Mensaje para Claude"
                    },
                    "history": {
                        "type": "array",
                        "description": "Historial de conversación",
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="generate_instructions_from_post",
            description="Genera instrucciones de imagen basándose en el contenido del post",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post"
                    }
                },
                "required": ["codigo"]
            }
        ),
        Tool(
            name="generate_post_images_complete",
            description="🚀 ENDPOINT COMPUESTO: Genera prompt + 4 imágenes automáticamente. Lee base.txt, genera prompt optimizado con Claude, genera 4 variaciones con Fal.ai y guarda todo en Drive. Ideal para flujo rápido.",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post"
                    }
                },
                "required": ["codigo"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta una herramienta"""
    
    logger.info(f"📞 Llamada a herramienta: {name}")
    logger.debug(f"   Argumentos: {arguments}")
    
    try:
        if name == "generate_complete_post":
            logger.info("🚀 Generando post completo...")
            response = requests.post(
                f"{API_BASE_URL}/api/generate-complete-post",
                json={
                    "tema": arguments.get('tema'),
                    "categoria": arguments.get('categoria', 'training')
                },
                timeout=120  # 2 minutos (genera contenido + imágenes)
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ {result.get('message')}\n\n" +
                         f"📝 Código: {result.get('codigo')}\n" +
                         f"📄 Título: {result.get('titulo')}\n" +
                         f"📋 Preview: {result.get('contenido_preview')}\n\n" +
                         f"🎨 Prompt: {result.get('prompt')[:100]}...\n" +
                         f"🖼️  Imágenes: {result.get('images_count')}\n\n" +
                         f"✨ Todo guardado en Google Sheets y Drive"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "list_posts":
            logger.info("📋 Listando posts...")
            response = requests.get(f"{API_BASE_URL}/api/posts")
            result = response.json()
            return [TextContent(
                type="text",
                text=f"Posts encontrados: {len(result.get('posts', []))}\n\n" + 
                     "\n".join([f"- {p['codigo']}: {p['titulo']} ({p['estado']})" 
                               for p in result.get('posts', [])])
            )]
        
        elif name == "create_post":
            logger.info(f"📝 Creando post: {arguments.get('titulo', 'Sin título')}")
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/chat",
                    json={
                        "message": f"Crea un post con título '{arguments['titulo']}' y contenido: {arguments['contenido']}"
                    },
                    timeout=30
                )
                logger.info(f"   Status code: {response.status_code}")
                result = response.json()
                logger.info(f"   Respuesta: {str(result)[:200]}...")
                return [TextContent(
                    type="text",
                    text=f"✅ Post creado exitosamente\n\n{result.get('response', '')}"
                )]
            except requests.exceptions.Timeout:
                logger.error("⏱️  Timeout al crear post")
                return [TextContent(type="text", text="❌ Error: Timeout al crear post (>30s)")]
            except Exception as e:
                logger.error(f"❌ Error creando post: {str(e)}")
                return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
        
        elif name == "get_post":
            response = requests.get(f"{API_BASE_URL}/api/posts")
            result = response.json()
            post = next((p for p in result.get('posts', []) if p['codigo'] == arguments['codigo']), None)
            if post:
                return [TextContent(
                    type="text",
                    text=f"Post: {post['codigo']}\n" +
                         f"Título: {post['titulo']}\n" +
                         f"Estado: {post['estado']}\n" +
                         f"Drive Folder: {post.get('drive_folder_id', 'N/A')}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Post {arguments['codigo']} no encontrado")]
        
        elif name == "init_post_folders":
            response = requests.post(
                f"{API_BASE_URL}/api/posts/{arguments['codigo']}/init-folders"
            )
            result = response.json()
            return [TextContent(
                type="text",
                text=f"✅ Carpetas inicializadas: {', '.join(result.get('folders_created', []))}"
            )]
        
        elif name == "generate_image":
            response = requests.post(
                f"{API_BASE_URL}/api/generate-image",
                json={
                    "codigo": arguments['codigo'],
                    "num_images": arguments.get('num_images', 4)
                }
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ {result.get('message')}\n" +
                         f"Imágenes generadas: {len(result.get('images', []))}\n" +
                         f"Referencias usadas: {result.get('references_used', 0)}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_video_text":
            response = requests.post(
                f"{API_BASE_URL}/api/generate-video-text",
                json={
                    "prompt": arguments['prompt'],
                    "resolution": arguments.get('resolution', '720p')
                }
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Video generado\n" +
                         f"URL: {result.get('video_url')}\n" +
                         f"Resolución: {result.get('resolution')}\n" +
                         f"Duración: {result.get('duration')}s"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_video_image":
            response = requests.post(
                f"{API_BASE_URL}/api/generate-video-image",
                json={
                    "prompt": arguments['prompt'],
                    "image_url": arguments['image_url'],
                    "resolution": arguments.get('resolution', '720p')
                }
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Video generado desde imagen\n" +
                         f"URL: {result.get('video_url')}\n" +
                         f"Resolución: {result.get('resolution')}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "chat":
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                json={
                    "message": arguments['message'],
                    "history": arguments.get('history', [])
                }
            )
            result = response.json()
            return [TextContent(
                type="text",
                text=result.get('response', 'Sin respuesta')
            )]
        
        elif name == "generate_instructions_from_post":
            response = requests.post(
                f"{API_BASE_URL}/api/generate-instructions-from-post",
                json={"codigo": arguments['codigo']}
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Instrucciones generadas:\n\n{result.get('instructions')}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_post_images_complete":
            response = requests.post(
                f"{API_BASE_URL}/api/generate-post-images-complete",
                json={"codigo": arguments['codigo']}
            )
            result = response.json()
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ {result.get('message')}\n\n" +
                         f"📝 Prompt: {result.get('prompt')}\n\n" +
                         f"🖼️  Imágenes generadas: {len(result.get('images', []))}\n" +
                         f"📎 Referencias usadas: {result.get('references_used', 0)}\n\n" +
                         "Archivos guardados en Drive:\n" +
                         "\n".join([f"  • {img['filename']}" for img in result.get('images', [])])
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        else:
            logger.warning(f"⚠️  Herramienta desconocida: {name}")
            return [TextContent(type="text", text=f"❌ Herramienta desconocida: {name}")]
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando {name}: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error ejecutando {name}: {str(e)}")]

async def main():
    """Ejecuta el servidor MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="lavelo-blog",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
