#!/usr/bin/env python3
"""
MCP Server para Lavelo Blog
Llama directamente a servicios (no usa HTTP)
"""

import asyncio
import sys
import os
import logging
from typing import Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Agregar path para importar servicios
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Importar servicios
from services.post_service import PostService
from services.image_service import ImageService
from services.video_service import VideoService
from services.content_service import ContentService
from services.publish_service import publish_service
from services.file_service import file_service

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

# Crear servidor MCP
server = Server("lavelo-blog")

# Inicializar servicios
post_service = PostService()
image_service = ImageService()
video_service = VideoService()
content_service = ContentService()

logger.info("🚀 MCP Server iniciado (modo directo a servicios)")

# ============================================
# TOOLS - Posts
# ============================================

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista todas las herramientas disponibles"""
    return [
        Tool(
            name="generate_complete_post",
            title="Generate Complete Post",
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
            title="List All Posts",
            description="Obtiene la lista de todos los posts del blog desde la base de datos local",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_post",
            title="Get Post Details",
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
            title="Initialize Post Folders",
            description="Inicializa la estructura de carpetas (textos, imagenes, videos) en storage local para un post",
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
            title="Generate Images with AI",
            description="Genera imágenes para un post usando Fal.ai SeaDream 4.0 (soporta hasta 2 referencias)",
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
            title="Generate Video from Text",
            description="Genera video desde texto usando Fal.ai SeeDance 1.0 Pro",
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
            title="Generate Video from Image",
            description="Genera video desde imagen usando Fal.ai SeeDance 1.0 Pro (anima una imagen estática)",
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
            title="Chat with Claude",
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
            title="Generate Image Prompt",
            description="Genera instrucciones/prompt de imagen optimizado basándose en el contenido del post",
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
            title="Generate Complete Images",
            description="🚀 Genera prompt + 4 imágenes automáticamente. Lee el contenido del post, genera prompt optimizado con Claude, genera 4 variaciones con Fal.ai y guarda todo. Ideal para flujo rápido.",
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
            name="get_social_status",
            title="Get Social Media Status",
            description="Obtiene el estado de todas las conexiones a redes sociales (Instagram, LinkedIn, Twitter, Facebook, TikTok). Muestra si están conectadas, nombre de usuario y fecha de expiración.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="disconnect_social",
            title="Disconnect Social Platform",
            description="Desconecta una plataforma social (elimina tokens de acceso). Útil para renovar conexiones o desconectar cuentas.",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Plataforma a desconectar",
                        "enum": ["instagram", "linkedin", "twitter", "facebook", "tiktok"]
                    }
                },
                "required": ["platform"]
            }
        ),
        Tool(
            name="publish_post",
            title="Publish to Social Media",
            description="Publica un post en una o varias redes sociales. Usa los textos e imágenes ya generados del post. Solo funciona con plataformas conectadas.",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del post a publicar"
                    },
                    "platforms": {
                        "type": "array",
                        "description": "Plataformas donde publicar (opcional, usa todas las conectadas si no se especifica)",
                        "items": {
                            "type": "string",
                            "enum": ["instagram", "facebook", "linkedin", "twitter", "tiktok"]
                        }
                    }
                },
                "required": ["codigo"]
            }
        )
    ]

# ============================================
# RESOURCES - Documentación
# ============================================

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """Lista recursos disponibles (documentación)"""
    return [
        Resource(
            uri="file:///ESTADOS_WORKFLOW.md",
            name="Estados del Workflow",
            description="Documentación completa de todos los estados del sistema (BASE_TEXT_AWAITING, IMAGE_BASE_AWAITING, etc.) con archivos necesarios y acciones para cada fase",
            mimeType="text/markdown"
        ),
        Resource(
            uri="file:///README.md",
            name="README del Proyecto",
            description="Documentación principal del proyecto Lavelo Blog - arquitectura, estructura y guía completa",
            mimeType="text/markdown"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Lee el contenido de un resource"""
    logger.info(f"📖 Leyendo resource: {uri}")
    
    # Mapear URIs a rutas reales
    base_path = os.path.dirname(__file__)
    
    if uri == "file:///ESTADOS_WORKFLOW.md":
        file_path = os.path.join(base_path, "ESTADOS_WORKFLOW.md")
    elif uri == "file:///README.md":
        file_path = os.path.join(base_path, "README.md")
    else:
        raise ValueError(f"Resource no encontrado: {uri}")
    
    # Leer archivo
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.info(f"✅ Resource leído: {len(content)} caracteres")
    return content

# ============================================
# TOOLS - Handlers
# ============================================

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta una herramienta"""
    
    logger.info(f"📞 Llamada a herramienta: {name}")
    logger.debug(f"   Argumentos: {arguments}")
    
    try:
        if name == "generate_complete_post":
            tema = arguments.get('tema')
            categoria = arguments.get('categoria', 'training')
            
            logger.info("🚀 Generando post completo...")
            
            try:
                # Paso 1: Crear post
                if not tema:
                    tema = "Tema de triatlón generado automáticamente"
                
                create_result = await post_service.create_post(
                    titulo=tema,
                    categoria=categoria,
                    idea=tema
                )
                
                if not create_result.get('success'):
                    return [TextContent(type="text", text=f"❌ Error creando post: {create_result.get('error')}")]
                
                codigo = create_result.get('codigo')
                
                # Paso 2: Generar instrucciones de imagen
                instructions_result = await content_service.generate_image_instructions(codigo)
                if not instructions_result.get('success'):
                    return [TextContent(type="text", text=f"❌ Error generando prompt: {instructions_result.get('error')}")]
                
                # Paso 3: Generar imágenes
                images_result = await image_service.generate_image(codigo, num_images=4)
                
                if images_result.get('success'):
                    return [TextContent(
                        type="text",
                        text=f"✅ Post completo generado\n\n" +
                             f"📝 Código: {codigo}\n" +
                             f"📄 Título: {tema}\n" +
                             f"🖼️  Imágenes: {len(images_result.get('images', []))}\n\n" +
                             f"✨ Todo guardado en storage local"
                    )]
                else:
                    return [TextContent(type="text", text=f"❌ Error generando imágenes: {images_result.get('error')}")]
                    
            except Exception as e:
                logger.error(f"❌ Error en generate_complete_post: {str(e)}")
                return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
        
        elif name == "list_posts":
            logger.info("📋 Listando posts...")
            posts = await post_service.list_posts()
            return [TextContent(
                type="text",
                text=f"📋 Posts disponibles ({len(posts)}):\n\n" +
                     '\n'.join([f"• {p['codigo']}: {p['titulo']} ({p['estado']})" 
                               for p in posts])
            )]
        
        elif name == "create_post":
            titulo = arguments.get('titulo', 'Sin título')
            categoria = arguments.get('categoria', 'training')
            idea = arguments.get('contenido', '')
            
            logger.info(f"📝 Creando post: {titulo}")
            
            try:
                result = await post_service.create_post(titulo, categoria, idea)
                
                if result.get('success'):
                    return [TextContent(
                        type="text",
                        text=f"✅ Post creado exitosamente\n\n" +
                             f"📋 Código: {result.get('codigo')}\n" +
                             f"📝 Título: {titulo}\n" +
                             f"📂 Categoría: {categoria}"
                    )]
                else:
                    return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
                    
            except Exception as e:
                logger.error(f"❌ Error creando post: {str(e)}")
                return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
        
        elif name == "get_post":
            post = await post_service.get_post(arguments['codigo'])
            if post:
                archivos = post.get('archivos', {})
                
                response = f"📋 Post: {post['codigo']}\n"
                response += f"📝 Título: {post['titulo']}\n"
                response += f"📊 Estado: {post['estado']}\n"
                response += f"📂 Categoría: {post.get('categoria', 'N/A')}\n"
                response += f"📅 Creado: {post.get('fecha_creacion', 'N/A')}\n\n"
                
                # Archivos disponibles
                response += "📁 Archivos disponibles:\n\n"
                
                if archivos.get('textos'):
                    response += f"📄 Textos ({len(archivos['textos'])}):\n"
                    for archivo in archivos['textos']:
                        response += f"  • {archivo}\n"
                    response += "\n"
                
                if archivos.get('imagenes'):
                    response += f"🖼️  Imágenes ({len(archivos['imagenes'])}):\n"
                    for archivo in archivos['imagenes']:
                        response += f"  • {archivo}\n"
                    response += "\n"
                
                if archivos.get('videos'):
                    response += f"🎬 Videos ({len(archivos['videos'])}):\n"
                    for archivo in archivos['videos']:
                        response += f"  • {archivo}\n"
                
                return [TextContent(type="text", text=response)]
            else:
                return [TextContent(type="text", text=f"❌ Post {arguments['codigo']} no encontrado")]
        
        elif name == "init_post_folders":
            codigo = arguments['codigo']
            result = file_service.init_post_folders(codigo)
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Carpetas inicializadas: {', '.join(result.get('folders_created', []))}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_image":
            codigo = arguments['codigo']
            num_images = arguments.get('num_images', 4)
            
            result = await image_service.generate_image(codigo, num_images)
            
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
            prompt = arguments['prompt']
            resolution = arguments.get('resolution', '720p')
            
            logger.info(f"🎬 Generando video desde texto ({resolution})...")
            result = await video_service.generate_video_from_text(prompt, resolution)
            
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Video generado exitosamente\n" +
                         f"🎬 URL: {result.get('video_url')}\n" +
                         f"⏱️  Duración: {result.get('duration', 'N/A')}s"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_video_image":
            prompt = arguments['prompt']
            image_url = arguments['image_url']
            resolution = arguments.get('resolution', '720p')
            
            logger.info(f"🎬 Generando video desde imagen ({resolution})...")
            result = await video_service.generate_video_from_image(prompt, image_url, resolution)
            
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Video generado desde imagen\n" +
                         f"🎬 URL: {result.get('video_url')}\n" +
                         f"⏱️  Duración: {result.get('duration', 'N/A')}s"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "chat":
            message = arguments['message']
            history = arguments.get('history', [])
            
            logger.info(f"💬 Chat: {message[:50]}...")
            result = await content_service.chat(message, history)
            
            return [TextContent(
                type="text",
                text=result.get('response', 'Sin respuesta')
            )]
        
        elif name == "generate_instructions_from_post":
            codigo = arguments['codigo']
            
            logger.info(f"🎨 Generando prompt de imagen para {codigo}...")
            result = await content_service.generate_image_prompt(codigo)
            
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Prompt generado:\n\n{result.get('prompt')}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error')}")]
        
        elif name == "generate_post_images_complete":
            codigo = arguments['codigo']
            
            logger.info(f"🚀 Generando prompt + imágenes completo para {codigo}...")
            
            # Paso 1: Generar prompt
            prompt_result = await content_service.generate_image_prompt(codigo)
            if not prompt_result.get('success'):
                return [TextContent(type="text", text=f"❌ Error generando prompt: {prompt_result.get('error')}")]
            
            prompt = prompt_result.get('prompt')
            
            # Paso 2: Generar imágenes
            images_result = await image_service.generate_image(codigo, num_images=4)
            
            if images_result.get('success'):
                return [TextContent(
                    type="text",
                    text=f"✅ Post completo generado\n\n" +
                         f"📝 Prompt: {prompt[:100]}...\n\n" +
                         f"🖼️  Imágenes generadas: {len(images_result.get('images', []))}\n" +
                         f"📎 Referencias usadas: {images_result.get('references_used', 0)}"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error generando imágenes: {images_result.get('error')}")]
        
        elif name == "get_social_status":
            logger.info("🔗 Obteniendo estado de redes sociales...")
            
            # Importar db_service para obtener tokens
            import db_service
            tokens = db_service.get_social_tokens()
            
            status_text = "📱 Estado de Redes Sociales:\n\n"
            platforms = ['instagram', 'linkedin', 'twitter', 'facebook', 'tiktok']
            
            for platform in platforms:
                if platform in tokens and tokens[platform]:
                    token_data = tokens[platform]
                    status_text += f"✅ **{platform.title()}**: "
                    username = token_data.get('username', 'N/A')
                    expires = token_data.get('expires_at', 'N/A')
                    status_text += f"Conectado como {username}\n"
                    if expires != 'N/A':
                        status_text += f"   Expira: {expires[:10]}\n"
                elif platform == 'facebook' and 'instagram' in tokens and tokens['instagram']:
                    # Facebook comparte token con Instagram
                    token_data = tokens['instagram']
                    status_text += f"✅ **{platform.title()}**: "
                    status_text += f"Conectado (compartido con Instagram)\n"
                else:
                    status_text += f"❌ **{platform.title()}**: No conectado\n"
            
            return [TextContent(type="text", text=status_text)]
        
        elif name == "disconnect_social":
            platform = arguments['platform']
            logger.info(f"🔌 Desconectando {platform}...")
            
            # Importar db_service para eliminar token
            import db_service
            result = db_service.delete_social_token(platform)
            
            if result:
                return [TextContent(
                    type="text",
                    text=f"✅ {platform.title()} desconectado exitosamente"
                )]
            else:
                return [TextContent(type="text", text=f"❌ Error al desconectar {platform}")]
        
        elif name == "publish_post":
            codigo = arguments['codigo']
            platforms = arguments.get('platforms', [])
            
            logger.info(f"📤 Publicando post {codigo}...")
            
            # Importar servicio directamente
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))
            from services.publish_service import publish_service
            
            # Publicar
            if platforms:
                # Publicar en plataformas específicas
                results = {}
                for platform in platforms:
                    if platform == 'instagram':
                        results['instagram'] = publish_service.publish_to_instagram(codigo)
                    elif platform == 'facebook':
                        results['facebook'] = publish_service.publish_to_facebook(codigo)
                    elif platform == 'linkedin':
                        results['linkedin'] = publish_service.publish_to_linkedin(codigo)
                    elif platform == 'twitter':
                        results['twitter'] = publish_service.publish_to_twitter(codigo)
                    elif platform == 'tiktok':
                        results['tiktok'] = publish_service.publish_to_tiktok(codigo)
                
                successful = sum(1 for r in results.values() if r.get('success'))
                total = len(results)
                
                result = {
                    'success': successful > 0,
                    'published': successful,
                    'total': total,
                    'results': results
                }
            else:
                # Publicar en todas las conectadas
                result = publish_service.publish_to_all(codigo)
            
            # Formatear respuesta
            if result.get('success'):
                response_text = f"✅ Post {codigo} publicado exitosamente\n\n"
                response_text += f"📊 Resultado: {result['published']}/{result['total']} plataformas\n\n"
                
                for platform, platform_result in result['results'].items():
                    emoji = "✅" if platform_result.get('success') else "❌"
                    response_text += f"{emoji} **{platform.title()}**: "
                    if platform_result.get('success'):
                        post_id = platform_result.get('post_id') or platform_result.get('tweet_id')
                        response_text += f"Publicado (ID: {post_id})\n"
                    else:
                        response_text += f"Error - {platform_result.get('error')}\n"
                
                return [TextContent(type="text", text=response_text)]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Error publicando: No se pudo publicar en ninguna plataforma"
                )]
        
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
