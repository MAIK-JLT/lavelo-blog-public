"""
Servicio de generación de contenido con Claude
Usado por: MCP Server, Panel Web, API REST
"""
from typing import List, Optional, Dict
from openai import OpenAI
import sys
import os
import asyncio
import json

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
        # Límite de concurrencia para llamadas LLM
        self.max_parallel = int(os.getenv('OPENAI_MAX_PARALLEL', '3'))

    async def _openai_chat(self, messages, max_tokens=800, debug_label: str = ""):
        """Wrapper async para OpenAI chat completions."""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            max_completion_tokens=max_tokens
        )
        # Debug si viene vacío
        try:
            choice = response.choices[0]
            content = getattr(choice.message, "content", "") or ""
            if not content.strip():
                logger.warning(
                    "⚠️ OpenAI devolvió contenido vacío%s | finish_reason=%s model=%s",
                    f" ({debug_label})" if debug_label else "",
                    getattr(choice, "finish_reason", None),
                    self.model,
                )
        except Exception as e:
            logger.warning("⚠️ No se pudo inspeccionar respuesta OpenAI vacía: %s", e)
        return response.choices[0].message.content or ""

    async def _generate_post_payload(self, idea: str, system_prompt: str) -> Optional[Dict]:
        """Genera un payload JSON para create_post si el modelo no invoca tools."""
        prompt = (
            "Genera un post para un blog de triatlón. "
            "Devuelve SOLO un JSON con estas claves: titulo, categoria, tags (array), contenido. "
            "Reglas: max 800 palabras, Markdown con ## y ###, tono profesional y práctico. "
            "categoria debe ser una de: training, racing, training-science. "
            "Si no queda claro, elige training.\n\n"
            f"Idea del usuario: {idea}"
        )
        content = await self._openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1600,
            debug_label="fallback_post_json"
        )
        if not content:
            return None
        try:
            return json.loads(content)
        except Exception:
            # Intentar extraer JSON de un bloque
            try:
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    return json.loads(content[start:end + 1])
            except Exception:
                return None
        return None

    def _should_force_create_post(self, message: str, history: List[Dict]) -> bool:
        """Detecta si el usuario quiere crear un post y conviene forzar tool."""
        lower_msg = (message or "").lower().strip()
        if lower_msg in ("ayúdame a crear un nuevo post", "ayudame a crear un nuevo post", "crear un nuevo post"):
            return False
        create_keywords = [
            "crear", "nuevo post", "post", "artículo", "articulo", "escribir", "redacta", "redactar",
            "hazme", "haz un post", "genera"
        ]
        wants_post = any(k in lower_msg for k in create_keywords)
        prev_assistant = ""
        if history and history[-1].get("role") == "assistant":
            prev_assistant = (history[-1].get("content") or "").lower()
        asked_details = any(k in prev_assistant for k in ["categor", "público", "publico", "tags", "distancia", "confirma"])
        provided_details = len((message or "").strip()) > 20 and "?" not in (message or "")
        has_category = any(k in lower_msg for k in ["training", "racing", "training-science", "categoria"])
        has_audience = any(k in lower_msg for k in ["principiante", "recreativo", "age-group", "élite", "elite"])
        has_distance = any(k in lower_msg for k in ["sprint", "olímpico", "olimpico", "half", "full", "ruta", "fondo"])
        enough_details = provided_details and (has_category or has_audience or has_distance)
        return (asked_details and enough_details) or (wants_post and enough_details)
    
    async def chat(self, message: str, history: List[Dict] = None, user_id: Optional[int] = None) -> Dict:
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
        
        # System prompt (personalizable por usuario)
        default_system_prompt = """Eres un asistente especializado en crear contenido para un blog de triatlón.

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
        system_prompt = default_system_prompt
        if user_id is not None:
            try:
                user = db_service.get_user_by_id(user_id)
                if user and user.system_prompt:
                    system_prompt = user.system_prompt
            except Exception:
                pass
        
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

        force_create_post = self._should_force_create_post(message, history)
        tool_choice = {"type": "function", "function": {"name": "create_post"}} if force_create_post else "auto"

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=oa_messages,
            tools=oa_tools,
            tool_choice=tool_choice,
            max_completion_tokens=2048
        )

        assistant_message = ""
        tool_results = []

        choice = response.choices[0]
        message_obj = choice.message
        tool_calls = getattr(message_obj, "tool_calls", None)

        post_info = None

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
                            idea=parsed['contenido'],
                            user_id=user_id
                        )
                        logger.info(f"   ✅ post_service.create_post finished: {result.get('success')}")
                    except Exception as e:
                        logger.error(f"   ❌ post_service.create_post failed: {e}")
                        result = {"success": False, "error": str(e)}

                    tool_results.append({"tool": tool_name, "result": result})
                    if result.get("success"):
                        post_info = result.get("post")

                elif tool_name == "list_posts":
                    logger.info("   ➡️ Calling db_service.get_all_posts...")
                    posts = db_service.get_all_posts(user_id=user_id)
                    result = {'posts': posts}
                    tool_results.append({"tool": tool_name, "result": result})

            post_created_result = next((r for r in tool_results if r['tool'] == 'create_post' and r['result'].get('success')), None)
            if post_created_result:
                post_data = post_created_result['result'].get('post', {})
                title = post_data.get('titulo', 'Sin título')
                code = post_data.get('codigo', 'N/A')
                assistant_message = (
                    f"✅ **Post creado exitosamente**\n\n"
                    f"**Título:** {title}\n**Código:** `{code}`\n\n"
                    "✅ **Terminado.** Puedes continuar en el panel.\n\n"
                    f"[Ir al post](/panel/?codigo={code})"
                )
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
                    max_completion_tokens=1024
                )
                assistant_message = follow_up.choices[0].message.content or ""
        else:
            assistant_message = message_obj.content or ""

            # Fallback: si el usuario quiere crear post y no hubo tool_calls
            try:
                if force_create_post:
                    logger.warning("⚠️ create_post sin tool_calls; usando fallback de última instancia")
                    payload = await self._generate_post_payload(message, system_prompt)
                    if payload:
                        from services.post_service import PostService
                        post_service = PostService()
                        categoria = payload.get("categoria") or "training"
                        if categoria not in ("training", "racing", "training-science"):
                            categoria = "training"
                        result = await post_service.create_post(
                            titulo=payload.get("titulo") or "Nuevo post",
                            categoria=categoria,
                            idea=payload.get("contenido") or "",
                            user_id=user_id
                        )
                        tool_results.append({"tool": "create_post", "result": result})
                        if result.get("success"):
                            post_info = result.get("post")
                            post_data = result.get("post", {})
                            title = post_data.get("titulo", "Sin título")
                            code = post_data.get("codigo", "N/A")
                            assistant_message = (
                                f"✅ **Post creado exitosamente**\n\n"
                                f"**Título:** {title}\n**Código:** `{code}`\n\n"
                                "✅ **Terminado.** Puedes continuar en el panel.\n\n"
                                f"[Ir al post](/panel/?codigo={code})"
                            )
            except Exception as e:
                logger.error("Fallback create_post failed: %s", e)

        post_codigo = post_info.get("codigo") if post_info else None
        post_title = post_info.get("titulo") if post_info else None
        post_url = f"/panel/?codigo={post_codigo}" if post_codigo else None

        if post_codigo and "Terminado" not in (assistant_message or ""):
            assistant_message = (
                (assistant_message or "").rstrip()
                + "\n\n✅ **Terminado.** Puedes continuar en el panel.\n\n"
                + f"[Ir al post]({post_url})"
            )

        tool_used = "create_post" if post_codigo else (tool_results[0]['tool'] if tool_results else None)

        return {
            'success': True,
            'response': assistant_message,
            'tool_used': tool_used,
            'tool_results': tool_results,
            'post_codigo': post_codigo,
            'post_title': post_title,
            'post_url': post_url,
            'history': messages + [{"role": "assistant", "content": assistant_message}]
        }
    
    async def generate_adapted_texts(self, codigo: str, redes: Dict[str, bool], user_id: Optional[int] = None) -> Dict:
        """
        Genera textos adaptados para redes sociales
        
        Usado por:
        - Panel Web: Validar Fase 1 (BASE_TEXT_AWAITING)
        - API: POST /api/validate-phase
        """
        # Verificar ownership si aplica
        if user_id is not None:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

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

        if not active_platforms:
            return {
                'success': True,
                'generated': [],
                'message': "✅ No hay redes activas para generar textos"
            }

        # Una sola llamada a OpenAI que devuelve JSON con cada red
        networks_list = "\n".join([f"- {k}: {v}" for k, v in active_platforms.items()])
        base_excerpt = base_text[:3000]
        prompt = f"""Devuelve un JSON válido con los textos adaptados para cada red social.

Redes y requisitos:
{networks_list}

Texto original:
{base_excerpt}

Reglas:
- Responde SOLO con JSON válido (sin explicaciones, sin markdown).
- El JSON debe contener exactamente las claves: {list(active_platforms.keys())}
- Cada valor debe ser el texto final adaptado y listo para publicar.
- Escribe en español.
"""

        raw = await self._openai_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            debug_label="adapted_texts_json"
        )

        # Parsear JSON (limpiar posibles fences)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"❌ Error parseando JSON de textos adaptados: {e}")
            errors.append(f"json_parse: {str(e)}")
            data = {}

        # Fallback: si no hay datos útiles, generar uno por uno por red
        if not data:
            logger.warning("⚠️ JSON vacío en textos adaptados. Usando fallback por red.")
            for platform, desc in active_platforms.items():
                per_prompt = f"""Adapta este texto para {desc}.

Texto original:
{base_excerpt}

Reglas:
- Devuelve SOLO el texto final, sin JSON ni explicaciones.
- Escribe en español.
"""
                try:
                    # max_tokens por plataforma: LinkedIn 3000 chars ≈ 750 tokens, Instagram/TikTok ≈ 550, Twitter ≈ 70
                    platform_max_tokens = {
                        'twitter': 200,
                        'instagram': 800,
                        'tiktok': 800,
                        'facebook': 800,
                        'linkedin': 1200,
                    }
                    data[platform] = await self._openai_chat(
                        messages=[{"role": "user", "content": per_prompt}],
                        max_tokens=platform_max_tokens.get(platform, 1000),
                        debug_label=f"adapted_text_{platform}"
                    )
                except Exception as e:
                    logger.error(f"  ❌ Error generando {platform} en fallback: {e}")
                    errors.append(f"{platform}: {str(e)}")

        for platform in active_platforms.keys():
            adapted_text = data.get(platform)
            if not adapted_text:
                errors.append(f"{platform}: texto vacío o no generado")
                continue

            try:
                filename = f"{codigo}_{platform}.txt"
                self.file_service.save_file(codigo, 'textos', filename, adapted_text)

                checkbox_field = f'{platform}_txt'
                db_service.update_post(codigo, {checkbox_field: True}, user_id=user_id)

                generated.append(filename)
                logger.info(f"  ✅ {filename} generado")
            except Exception as e:
                logger.error(f"  ❌ Error guardando {platform}: {e}")
                errors.append(f"{platform}: {str(e)}")
        
        return {
            'success': True,
            'generated': generated,
            'errors': errors,
            'message': f"✅ {len(generated)} textos adaptados generados"
        }
    
    async def generate_image_prompt(self, codigo: str, user_id: Optional[int] = None) -> Dict:
        """
        Genera prompt para imagen usando Claude
        
        Usado por:
        - Panel Web: Validar Fase 2 (ADAPTED_TEXTS_AWAITING)
        - MCP: generate_instructions_from_post
        """
        if user_id is not None:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

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
- En español
- Sin explicaciones, solo el prompt

Genera SOLO el prompt de imagen."""
        
        image_prompt = await self._openai_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            debug_label="generate_image_prompt"
        )

        image_prompt = (image_prompt or "").strip()

        # Reintentar una vez si el modelo devuelve vacío
        if not image_prompt:
            logger.warning("⚠️ Prompt de imagen vacío, reintentando una vez...")
            image_prompt = await self._openai_chat(
                messages=[{"role": "user", "content": prompt + "\n\nDevuelve un prompt no vacío."}],
                max_tokens=700,
                debug_label="generate_image_prompt_retry"
            )
            image_prompt = (image_prompt or "").strip()

        if not image_prompt:
            raise Exception("Prompt de imagen vacío. Reintenta en Fase 3.")
        
        # Guardar archivo
        filename = f"{codigo}_prompt_imagen.txt"
        self.file_service.save_file(codigo, 'textos', filename, image_prompt)
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'prompt_imagen_base_txt': True}, user_id=user_id)
        
        return {
            'success': True,
            'prompt': image_prompt,
            'filename': filename,
            'message': f"✅ Prompt de imagen generado"
        }
    
    async def generate_video_script(self, codigo: str, user_id: Optional[int] = None) -> Dict:
        """
        Genera script para video usando Claude
        
        Usado por:
        - Panel Web: Validar Fase 5 (IMAGE_FORMATS_AWAITING)
        """
        if user_id is not None:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

        # Leer base.txt
        base_text = self.file_service.read_file(codigo, 'textos', f"{codigo}_base.txt")
        
        if not base_text:
            raise Exception(f"No se encontró {codigo}_base.txt")
        
        # Limitar longitud del contenido para evitar cortes por límite
        base_excerpt = base_text[:3500]
        prompt = f"""Genera un script para un video de 15 segundos sobre este contenido.

Contenido:
{base_excerpt}

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
        
        video_script = await self._openai_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            debug_label="generate_video_script"
        )

        video_script = (video_script or "").strip()

        # Reintentar una vez si viene vacío
        if not video_script:
            logger.warning("⚠️ Script de video vacío, reintentando una vez...")
            retry_prompt = prompt + "\n\nReturn a non-empty script."
            video_script = await self._openai_chat(
                messages=[{"role": "user", "content": retry_prompt}],
                max_tokens=1200,
                debug_label="generate_video_script_retry"
            )
            video_script = (video_script or "").strip()

        if not video_script:
            raise Exception("Script de video vacío. Reintenta en Fase 6.")
        
        # Guardar archivo
        filename = f"{codigo}_script_video.txt"
        self.file_service.save_file(codigo, 'textos', filename, video_script)
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'script_video_base_txt': True}, user_id=user_id)
        
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
4. El prompt mejorado debe ser claro, descriptivo y en español
5. Máximo 500 palabras

Genera SOLO el prompt mejorado, sin explicaciones adicionales."""

        improved_prompt = (await self._openai_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1600,
            debug_label="improve_prompt_visual"
        )).strip()
        
        print(f"✨ Prompt mejorado ({len(improved_prompt)} chars)")
        
        return improved_prompt

# Instancia global
content_service = ContentService()
