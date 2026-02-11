"""
Servicio de generación de contenido con Claude
Usado por: MCP Server, Panel Web, API REST
"""
from typing import List, Optional, Dict
from openai import OpenAI
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.file_service import file_service

import logging

logger = logging.getLogger(__name__)

class ContentService:
    """Servicio para generar contenido con Claude"""
    
    def __init__(self):
        self.file_service = file_service
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Modelo por defecto (puedes sobrescribir con OPENAI_MODEL en .env)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.haiku_model = self.model
    
    async def chat(self, message: str, history: List[Dict] = None) -> Dict:
        """
        Chat con Claude usando herramientas MCP
        
        Usado por:
        - Panel Web: Chat flotante
        - MCP: Interacción directa
        """
        if history is None:
            history = []
        
        # Definir herramientas MCP disponibles
        tools = [
            {
                "name": "create_post",
                "description": "Crea un nuevo post para blog de triatlón. Genera código automático, crea carpetas y guarda el texto base. IMPORTANTE: El contenido debe tener máximo 800 palabras, estar bien estructurado con títulos y subtítulos en Markdown, y ser informativo y práctico.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "Título del post (claro y atractivo)"},
                        "contenido": {"type": "string", "description": "Contenido completo del texto base en formato Markdown. MÁXIMO 800 PALABRAS. Debe incluir: introducción, desarrollo con subtítulos (##), conclusión y referencias si aplica."},
                        "categoria": {"type": "string", "description": "Categoría (racing, training, training-science)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags del post"}
                    },
                    "required": ["titulo", "contenido", "categoria"]
                }
            },
            {
                "name": "list_posts",
                "description": "Lista todos los posts existentes con su estado actual",
                "input_schema": {"type": "object", "properties": {}}
            }
        ]
        
        # Construir mensajes
        messages = history + [{"role": "user", "content": message}]
        
        # System prompt
        system_prompt = """Eres un asistente especializado en crear contenido para un blog de triatlón.

Cuando crees posts:
- Máximo 800 palabras
- Formato Markdown con títulos (##) y subtítulos (###)
- Contenido práctico, basado en ciencia y experiencia
- Tono profesional pero accesible
- Incluir ejemplos concretos cuando sea posible

Categorías disponibles:
- training: Entrenamientos y planes
- racing: Carreras y competición
- training-science: Ciencia del entrenamiento"""
        
        # Convertir history a formato OpenAI
        oa_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                oa_messages.append({"role": m["role"], "content": m.get("content", "")})

        oa_tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_post",
                    "description": tools[0]["description"],
                    "parameters": tools[0]["input_schema"]
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_posts",
                    "description": tools[1]["description"],
                    "parameters": tools[1]["input_schema"]
                }
            }
        ]

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=oa_messages,
            tools=oa_tools,
            max_tokens=2048
        )

        assistant_message = ""
        tool_results = []

        choice = response.choices[0]
        message_obj = choice.message
        tool_calls = getattr(message_obj, "tool_calls", None)

        if tool_calls:
            for call in tool_calls:
                tool_name = call.function.name
                tool_input = call.function.arguments
                logger.info(f"🛠️ Executing tool: {tool_name}")

                if tool_name == "create_post":
                    from services.post_service import PostService
                    post_service = PostService()
                    try:
                        import json
                        parsed = json.loads(tool_input) if isinstance(tool_input, str) else tool_input
                        logger.info("   ➡️ Calling post_service.create_post...")
                        result = await post_service.create_post(
                            titulo=parsed['titulo'],
                            categoria=parsed['categoria'],
                            idea=parsed['contenido']
                        )
                        logger.info(f"   ✅ post_service.create_post finished: {result.get('success')}")
                    except Exception as e:
                        logger.error(f"   ❌ post_service.create_post failed: {e}")
                        result = {"success": False, "error": str(e)}

                    tool_results.append({"tool": tool_name, "result": result})

                elif tool_name == "list_posts":
                    logger.info("   ➡️ Calling db_service.get_all_posts...")
                    posts = db_service.get_all_posts()
                    result = {'posts': posts}
                    tool_results.append({"tool": tool_name, "result": result})

            post_created_result = next((r for r in tool_results if r['tool'] == 'create_post' and r['result'].get('success')), None)
            if post_created_result:
                post_data = post_created_result['result'].get('post', {})
                title = post_data.get('titulo', 'Sin título')
                code = post_data.get('codigo', 'N/A')
                assistant_message = f"✅ **Post creado exitosamente**\n\n**Título:** {title}\n**Código:** `{code}`\n\nEl post ha sido guardado y ya puedes verlo en el panel. ¿Te gustaría generar las imágenes o adaptar el texto para redes sociales?"
            else:
                import json
                oa_messages.append({
                    "role": "assistant",
                    "content": message_obj.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.function.name, "arguments": call.function.arguments}
                        } for call in tool_calls
                    ]
                })
                for tr in tool_results:
                    oa_messages.append({
                        "role": "tool",
                        "tool_call_id": next((c.id for c in tool_calls if c.function.name == tr["tool"]), ""),
                        "name": tr["tool"],
                        "content": json.dumps(tr["result"])
                    })

                follow_up = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=oa_messages,
                    max_tokens=1024
                )
                assistant_message = follow_up.choices[0].message.content or ""
        else:
            assistant_message = message_obj.content or ""
        
        return {
            'success': True,
            'response': assistant_message,
            'tool_used': tool_results[0]['tool'] if tool_results else None,
            'tool_results': tool_results,
            'history': messages + [{"role": "assistant", "content": assistant_message}]
        }
    
    async def generate_adapted_texts(self, codigo: str, redes: Dict[str, bool]) -> Dict:
        """
        Genera textos adaptados para redes sociales
        
        Usado por:
        - Panel Web: Validar Fase 1 (BASE_TEXT_AWAITING)
        - API: POST /api/validate-phase
        """
        # Leer base.txt
        base_text = self.file_service.read_file(codigo, 'textos', f"{codigo}_base.txt")
        
        if not base_text:
            raise Exception(f"No se encontró {codigo}_base.txt")
        
        platforms = {
            'instagram': 'Instagram (2200 caracteres max, tono visual y motivacional)',
            'linkedin': 'LinkedIn (3000 caracteres max, tono profesional)',
            'twitter': 'Twitter/X (280 caracteres max, tono conciso)',
            'facebook': 'Facebook (63206 caracteres max, tono conversacional)',
            'tiktok': 'TikTok (2200 caracteres max, tono juvenil y dinámico)'
        }
        
        # Filtrar solo plataformas activas
        active_platforms = {k: v for k, v in platforms.items() if redes.get(k, True)}
        generated = []
        errors = []
        
        logger.info(f"📝 Generando textos adaptados para {codigo}. Redes: {list(active_platforms.keys())}")

        for platform, description in active_platforms.items():
            try:
                prompt = f"""Adapta el siguiente texto para {description}.

Texto original:
{base_text}

Genera SOLO el texto adaptado, sin explicaciones ni metadatos."""
                
                message = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.haiku_model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                adapted_text = message.content[0].text
                
                # Guardar archivo
                filename = f"{codigo}_{platform}.txt"
                self.file_service.save_file(codigo, 'textos', filename, adapted_text)
                
                # Actualizar checkbox en BD
                checkbox_field = f'{platform}_txt'
                db_service.update_post(codigo, {checkbox_field: True})
                
                generated.append(filename)
                logger.info(f"  ✅ {filename} generado")
            except Exception as e:
                logger.error(f"  ❌ Error generando {platform}: {e}")
                errors.append(f"{platform}: {str(e)}")
        
        return {
            'success': True,
            'generated': generated,
            'message': f"✅ {len(generated)} textos adaptados generados"
        }
    
    async def generate_image_prompt(self, codigo: str) -> Dict:
        """
        Genera prompt para imagen usando Claude
        
        Usado por:
        - Panel Web: Validar Fase 2 (ADAPTED_TEXTS_AWAITING)
        - MCP: generate_instructions_from_post
        """
        # Leer base.txt
        base_text = self.file_service.read_file(codigo, 'textos', f"{codigo}_base.txt")
        
        if not base_text:
            raise Exception(f"No se encontró {codigo}_base.txt")
        
        prompt = f"""Genera un prompt detallado para crear una imagen que represente este contenido.

Contenido:
{base_text}

El prompt debe:
- Ser descriptivo y específico
- Incluir estilo visual, colores, composición
- Máximo 900 caracteres
- En inglés
- Sin explicaciones, solo el prompt

Genera SOLO el prompt de imagen."""
        
        message = await asyncio.to_thread(
            self.client.messages.create,
            model=self.haiku_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        image_prompt = message.content[0].text
        
        # Guardar archivo
        filename = f"{codigo}_prompt_imagen.txt"
        self.file_service.save_file(codigo, 'textos', filename, image_prompt)
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'prompt_imagen_base_txt': True})
        
        return {
            'success': True,
            'prompt': image_prompt,
            'filename': filename,
            'message': f"✅ Prompt de imagen generado"
        }
    
    async def generate_video_script(self, codigo: str) -> Dict:
        """
        Genera script para video usando Claude
        
        Usado por:
        - Panel Web: Validar Fase 5 (IMAGE_FORMATS_AWAITING)
        """
        # Leer base.txt
        base_text = self.file_service.read_file(codigo, 'textos', f"{codigo}_base.txt")
        
        if not base_text:
            raise Exception(f"No se encontró {codigo}_base.txt")
        
        prompt = f"""Genera un script para un video de 15 segundos sobre este contenido.

Contenido:
{base_text}

El script debe:
- Dividirse en 4 escenas de ~3-4 segundos cada una
- Ser dinámico y visual
- Incluir descripción de cada escena
- Máximo 500 caracteres total
- En español

Formato:
Escena 1: [descripción]
Escena 2: [descripción]
Escena 3: [descripción]
Escena 4: [descripción]

Genera SOLO el script."""
        
        message = self.client.messages.create(
            model=self.haiku_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        video_script = message.content[0].text
        
        # Guardar archivo
        filename = f"{codigo}_script_video.txt"
        self.file_service.save_file(codigo, 'textos', filename, video_script)
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'script_video_base_txt': True})
        
        return {
            'success': True,
            'script': video_script,
            'filename': filename,
            'message': f"✅ Script de video generado"
        }
    
    async def improve_prompt_with_visual_selections(
        self, 
        prompt_original: str, 
        selections: Dict, 
        reference_info: List[Dict]
    ) -> str:
        """
        Mejora un prompt de imagen incorporando selecciones visuales y referencias
        
        Usado por: Prompt Builder
        """
        # Construir descripción de selecciones
        selections_text = []
        for category, value in selections.items():
            if value:
                selections_text.append(f"- {category.title()}: {value}")
        
        # Construir descripción de referencias
        references_text = ""
        if reference_info:
            references_text = "\n\nImágenes de referencia proporcionadas:\n"
            for ref in reference_info:
                references_text += f"- {ref['filename']}: {ref['label']}\n"
        
        prompt = f"""Mejora este prompt de imagen incorporando las selecciones visuales del usuario.

PROMPT ORIGINAL:
{prompt_original}

SELECCIONES VISUALES:
{chr(10).join(selections_text) if selections_text else 'Ninguna'}
{references_text}

INSTRUCCIONES:
1. Mantén la esencia y contenido del prompt original
2. Incorpora las selecciones visuales de forma natural
3. Si hay referencias, menciona que se usarán como guía visual
4. El prompt mejorado debe ser claro, descriptivo y en inglés
5. Máximo 500 palabras

Genera SOLO el prompt mejorado, sin explicaciones adicionales."""

        message = await asyncio.to_thread(
            self.client.messages.create,
            model=self.haiku_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        improved_prompt = message.content[0].text.strip()
        
        print(f"✨ Prompt mejorado ({len(improved_prompt)} chars)")
        
        return improved_prompt

# Instancia global
content_service = ContentService()
