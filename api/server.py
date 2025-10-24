import os
import time
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Cargar variables de entorno ANTES de importar sheets_service
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

from sheets_service import sheets_service
from anthropic import Anthropic
from openai import OpenAI
from google import genai
from google.genai import types
import requests
from io import BytesIO
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import tempfile

# Permitir HTTP en desarrollo (solo para localhost)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Deshabilitar validación estricta de scopes
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

app = Flask(__name__, static_folder='../panel', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configurar CORS correctamente
CORS(app, 
     resources={r"/api/*": {
         "origins": ["http://localhost:8080", "http://localhost:5001"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type"],
         "supports_credentials": True
     }})

# Cache simple para posts (evitar múltiples llamadas simultáneas a Sheets)
posts_cache = {'data': None, 'timestamp': 0}
CACHE_TTL = 5  # 5 segundos

def get_cached_posts():
    """Obtener posts con cache para evitar múltiples llamadas simultáneas"""
    import time
    current_time = time.time()
    
    if posts_cache['data'] is None or (current_time - posts_cache['timestamp']) > CACHE_TTL:
        posts_cache['data'] = sheets_service.get_posts()
        posts_cache['timestamp'] = current_time
    
    return posts_cache['data']

# Ruta principal del panel
@app.route('/')
def index():
    return app.send_static_file('index.html')

# OAuth2: Iniciar autenticación
@app.route('/api/auth/login')
def auth_login():
    flow = sheets_service.get_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

# OAuth2: Callback
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = sheets_service.get_oauth_flow()
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    sheets_service.authenticate(session['credentials'])
    return redirect('/')

# API: Obtener todos los posts
@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        posts = sheets_service.get_posts()
        return jsonify({'success': True, 'posts': posts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: Inicializar estructura de carpetas de un post
@app.route('/api/posts/<codigo>/init-folders', methods=['POST'])
def init_post_folders(codigo):
    try:
        # Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado o sin Drive Folder ID'}), 404
        
        folder_id = post['drive_folder_id']
        print(f"📁 Inicializando carpetas para post {codigo} (Drive ID: {folder_id})")
        
        # Crear las 3 subcarpetas si no existen
        subfolders = ['textos', 'imagenes', 'videos']
        created = []
        
        for subfolder in subfolders:
            subfolder_id = sheets_service.get_subfolder_id(folder_id, subfolder, create_if_missing=True)
            if subfolder_id:
                created.append(subfolder)
        
        return jsonify({
            'success': True,
            'message': f'Estructura de carpetas inicializada',
            'folders_created': created
        })
        
    except Exception as e:
        print(f"❌ Error inicializando carpetas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/file', methods=['GET'])
def get_drive_file():
    try:
        codigo = request.args.get('codigo')
        folder = request.args.get('folder')
        filename = request.args.get('filename')
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener subfolder
        folder_id = post['drive_folder_id']
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder)
        
        if not subfolder_id:
            return jsonify({'error': f'Carpeta {folder} no encontrada'}), 404
        
        # Leer archivo
        content = sheets_service.get_file_from_drive(subfolder_id, filename)
        
        if content is None:
            return jsonify({'error': 'Archivo no encontrado'}), 404
        
        return jsonify({'success': True, 'content': content})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/image', methods=['GET'])
def get_drive_image():
    """Servir imágenes desde Google Drive con reintentos"""
    try:
        from flask import send_file
        import time
        codigo = request.args.get('codigo')
        folder = request.args.get('folder')
        filename = request.args.get('filename')
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post (usando cache)
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener subfolder
        folder_id = post['drive_folder_id']
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder)
        
        if not subfolder_id:
            return jsonify({'error': f'Carpeta {folder} no encontrada'}), 404
        
        # Leer imagen con reintentos para errores de SSL
        max_retries = 3
        image_bytes = None
        
        for attempt in range(max_retries):
            try:
                image_bytes = sheets_service.get_image_from_drive(subfolder_id, filename)
                if image_bytes:
                    break
            except Exception as retry_error:
                if 'SSL' in str(retry_error) or 'ssl' in str(retry_error).lower():
                    print(f"⚠️ Error SSL en intento {attempt + 1}/{max_retries}: {retry_error}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))  # Espera incremental
                        continue
                raise retry_error
        
        if not image_bytes:
            return jsonify({'error': 'Imagen no encontrada'}), 404
        
        # Servir imagen
        return send_file(
            BytesIO(image_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error sirviendo imagen {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/video', methods=['GET'])
def get_drive_video():
    """Servir videos desde Google Drive con reintentos"""
    try:
        from flask import send_file
        import time
        codigo = request.args.get('codigo')
        folder = request.args.get('folder')
        filename = request.args.get('filename')
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post (usando cache)
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener subfolder
        folder_id = post['drive_folder_id']
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder)
        
        if not subfolder_id:
            return jsonify({'error': f'Carpeta {folder} no encontrada'}), 404
        
        # Leer video con reintentos para errores de SSL
        max_retries = 3
        video_bytes = None
        
        for attempt in range(max_retries):
            try:
                video_bytes = sheets_service.get_image_from_drive(subfolder_id, filename)
                if video_bytes:
                    break
            except Exception as retry_error:
                if 'SSL' in str(retry_error) or 'ssl' in str(retry_error).lower():
                    print(f"⚠️ Error SSL en intento {attempt + 1}/{max_retries}: {retry_error}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                raise retry_error
        
        if not video_bytes:
            return jsonify({'error': 'Video no encontrado'}), 404
        
        # Servir video
        return send_file(
            BytesIO(video_bytes),
            mimetype='video/mp4',
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error sirviendo video {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/save-file', methods=['POST'])
def save_drive_file():
    try:
        data = request.json
        codigo = data.get('codigo')
        folder = data.get('folder')
        filename = data.get('filename')
        content = data.get('content')
        
        if not all([codigo, folder, filename, content is not None]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener subfolder (crear si no existe)
        folder_id = post['drive_folder_id']
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder, create_if_missing=True)
        
        if not subfolder_id:
            return jsonify({'error': f'No se pudo crear/encontrar carpeta {folder}'}), 404
        
        # Guardar archivo
        sheets_service.save_file_to_drive(subfolder_id, filename, content)
        print(f"✅ Archivo guardado: {filename}")
        
        # Actualizar checkbox correspondiente en Excel
        checkbox_updated = False
        estado_updated = False
        if folder == 'textos':
            if f'{codigo}_base.txt' in filename:
                sheets_service.update_post_field(codigo, 'base_text', 'TRUE')
                sheets_service.update_post_field(codigo, 'estado', 'BASE_TEXT_AWAITING')
                checkbox_updated = True
                estado_updated = True
                print(f"✅ Checkbox base_text actualizado a TRUE")
                print(f"✅ Estado actualizado a BASE_TEXT_AWAITING")
            elif f'{codigo}_instagram.txt' in filename:
                sheets_service.update_post_field(codigo, 'adapted_texts_instagram', 'TRUE')
                checkbox_updated = True
            elif f'{codigo}_linkedin.txt' in filename:
                sheets_service.update_post_field(codigo, 'adapted_texts_linkedin', 'TRUE')
                checkbox_updated = True
            elif f'{codigo}_twitter.txt' in filename:
                sheets_service.update_post_field(codigo, 'adapted_texts_twitter', 'TRUE')
                checkbox_updated = True
            elif f'{codigo}_facebook.txt' in filename:
                sheets_service.update_post_field(codigo, 'adapted_texts_facebook', 'TRUE')
                checkbox_updated = True
            elif f'{codigo}_tiktok.txt' in filename:
                sheets_service.update_post_field(codigo, 'adapted_texts_tiktok', 'TRUE')
                checkbox_updated = True
            elif 'prompt_imagen' in filename:
                sheets_service.update_post_field(codigo, 'image_prompt', 'TRUE')
                sheets_service.update_post_field(codigo, 'estado', 'IMAGE_PROMPT_AWAITING')
                checkbox_updated = True
                estado_updated = True
                print(f"✅ Checkbox image_prompt actualizado a TRUE")
                print(f"✅ Estado actualizado a IMAGE_PROMPT_AWAITING")
            elif 'script_video' in filename:
                sheets_service.update_post_field(codigo, 'video_prompt', 'TRUE')
                sheets_service.update_post_field(codigo, 'estado', 'VIDEO_PROMPT_AWAITING')
                checkbox_updated = True
                estado_updated = True
                print(f"✅ Checkbox video_prompt actualizado a TRUE")
                print(f"✅ Estado actualizado a VIDEO_PROMPT_AWAITING")
        elif folder == 'imagenes':
            if 'imagen_base' in filename:
                sheets_service.update_post_field(codigo, 'image_base', 'TRUE')
                checkbox_updated = True
        elif folder == 'videos':
            if 'video_base' in filename:
                sheets_service.update_post_field(codigo, 'video_base', 'TRUE')
                checkbox_updated = True
        
        return jsonify({
            'success': True, 
            'message': 'Archivo guardado',
            'checkbox_updated': checkbox_updated,
            'estado_updated': estado_updated
        })
        
    except Exception as e:
        print(f"❌ Error en save_drive_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API: Obtener estado actual (legacy)
@app.route('/api/status', methods=['GET'])
def get_status():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sheets_service.authenticate(session['credentials'])
    posts = sheets_service.get_posts()
    
    if posts:
        return jsonify(posts[0])
    
    return jsonify({'error': 'No posts found'}), 404

# API: Validar fase y avanzar estado (MOCK - sin generar contenido real)
@app.route('/api/validate-phase', methods=['POST'])
def validate_phase():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    codigo = data.get('codigo')
    current_state = data.get('current_state')
    redes = data.get('redes', {})  # Redes seleccionadas desde el frontend
    
    if not codigo or not current_state:
        return jsonify({'error': 'Código y estado requeridos'}), 400
    
    try:
        sheets_service.authenticate(session['credentials'])
        
        # Guardar configuración de redes en Sheet (columnas AK-AP)
        print(f"📱 Redes seleccionadas: {redes}")
        for network, active in redes.items():
            field_name = f'redes_{network}'
            value = 'TRUE' if active else 'FALSE'
            sheets_service.update_post_field(codigo, field_name, value)
            print(f"  ✅ {field_name} = {value}")
        
        # Máquina de estados: definir transiciones
        state_transitions = {
            'BASE_TEXT_AWAITING': {
                'next': 'ADAPTED_TEXTS_AWAITING',
                'action': 'Generar textos adaptados',
                'checkboxes': ['adapted_texts_instagram', 'adapted_texts_linkedin', 
                              'adapted_texts_twitter', 'adapted_texts_facebook', 'adapted_texts_tiktok']
            },
            'ADAPTED_TEXTS_AWAITING': {
                'next': 'IMAGE_PROMPT_AWAITING',
                'action': 'Generar prompt de imagen',
                'checkboxes': ['image_prompt']
            },
            'IMAGE_PROMPT_AWAITING': {
                'next': 'IMAGE_BASE_AWAITING',
                'action': 'Generar imagen base',
                'checkboxes': ['image_base']
            },
            'IMAGE_BASE_AWAITING': {
                'next': 'IMAGE_FORMATS_AWAITING',
                'action': 'Generar formatos de imagen',
                'checkboxes': []  # Se marcan múltiples en formato
            },
            'IMAGE_FORMATS_AWAITING': {
                'next': 'VIDEO_PROMPT_AWAITING',
                'action': 'Generar script de video',
                'checkboxes': ['video_prompt']
            },
            'VIDEO_PROMPT_AWAITING': {
                'next': 'VIDEO_BASE_AWAITING',
                'action': 'Generar video base',
                'checkboxes': ['video_base']
            },
            'VIDEO_BASE_AWAITING': {
                'next': 'VIDEO_FORMATS_AWAITING',
                'action': 'Generar formatos de video',
                'checkboxes': ['video_feed_16x9', 'video_stories_9x16', 'video_shorts_9x16', 'video_tiktok_9x16']
            },
            'VIDEO_FORMATS_AWAITING': {
                'next': 'READY_TO_PUBLISH',
                'action': 'Verificar y marcar como listo',
                'checkboxes': []
            },
            'READY_TO_PUBLISH': {
                'next': 'PUBLISHED',
                'action': 'Publicar',
                'checkboxes': []
            }
        }
        
        transition = state_transitions.get(current_state)
        if not transition:
            return jsonify({'error': f'Estado {current_state} no reconocido'}), 400
        
        print(f"🔧 Validando fase: {current_state} → {transition['next']}")
        print(f"📝 Acción: {transition['action']}")
        
        # CASO ESPECIAL: BASE_TEXT_AWAITING → Generar textos adaptados con Claude
        if current_state == 'BASE_TEXT_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post:
                return jsonify({'error': f'Post {codigo} no encontrado en el Excel'}), 400
            
            if not post.get('drive_folder_id'):
                return jsonify({'error': f'El post {codigo} no tiene Drive Folder ID configurado en la columna G del Excel'}), 400
            
            folder_id = post['drive_folder_id']
            print(f"📁 Drive Folder ID del post: {folder_id}")
            
            # Buscar subcarpeta 'textos'
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            if not textos_folder_id:
                return jsonify({'error': f'No se encontró la carpeta "textos" dentro de la carpeta de Drive con ID: {folder_id}. Verifica que exista la estructura: [carpeta-post]/textos/'}), 400
            
            # Leer CODIGO_base.txt de Drive/textos/
            base_filename = f"{codigo}_base.txt"
            base_text = sheets_service.get_file_from_drive(textos_folder_id, base_filename)
            if not base_text:
                return jsonify({'error': f'No se encontró {base_filename} en textos/'}), 400
            
            # Llamar a Claude para generar textos adaptados (solo para redes activas)
            print("🤖 Llamando a Claude API...")
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            platforms = {
                'instagram': 'Instagram (2200 caracteres max, tono visual y motivacional)',
                'linkedin': 'LinkedIn (3000 caracteres max, tono profesional)',
                'twitter': 'Twitter/X (280 caracteres max, tono conciso)',
                'facebook': 'Facebook (63206 caracteres max, tono conversacional)',
                'tiktok': 'TikTok (2200 caracteres max, tono juvenil y dinámico)'
            }
            
            # Filtrar solo plataformas activas
            active_platforms = {k: v for k, v in platforms.items() if redes.get(k, True)}
            print(f"📱 Generando textos para: {list(active_platforms.keys())}")
            
            for platform, description in active_platforms.items():
                prompt = f"""Adapta el siguiente texto para {description}.

Texto original:
{base_text}

Genera SOLO el texto adaptado, sin explicaciones ni metadatos."""
                
                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",  # Claude Haiku 4.5 (último modelo)
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                adapted_text = message.content[0].text
                
                # Guardar en Drive/textos/ con nomenclatura: CODIGO_platform.txt
                filename = f"{codigo}_{platform}.txt"
                sheets_service.save_file_to_drive(textos_folder_id, filename, adapted_text)
                
                # Marcar checkbox solo para redes activas
                checkbox_field = f'adapted_texts_{platform}'
                sheets_service.update_post_field(codigo, checkbox_field, 'TRUE')
                print(f"  ✅ {filename} generado y guardado")
        
        # CASO ESPECIAL: ADAPTED_TEXTS_AWAITING → Generar prompt de imagen
        if current_state == 'ADAPTED_TEXTS_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            if not textos_folder_id:
                return jsonify({'error': 'No se encontró la carpeta textos/'}), 400
            
            # Leer base.txt
            base_filename = f"{codigo}_base.txt"
            base_text = sheets_service.get_file_from_drive(textos_folder_id, base_filename)
            if not base_text:
                return jsonify({'error': f'No se encontró {base_filename}'}), 400
            
            # Llamar a Claude para generar prompt de imagen
            print("🤖 Generando prompt de imagen con Claude...")
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            prompt = f"""Genera un prompt detallado para crear una imagen que represente visualmente el siguiente contenido de triatlón.

IMPORTANTE: El prompt debe evitar:
- Personas específicas o atletas profesionales
- Rostros o cuerpos humanos detallados
- Marcas comerciales

El prompt debe enfocarse en:
- Equipamiento deportivo (bicicletas, zapatillas, cascos)
- Paisajes y locaciones (playas, carreteras, zonas de transición)
- Elementos abstractos y conceptuales
- Colores y atmósfera
- En inglés
- Máximo 400 caracteres

Contenido:
{base_text}

Genera SOLO el prompt en inglés, sin explicaciones."""
            
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            image_prompt = message.content[0].text
            
            # Guardar prompt en Drive/textos/
            prompt_filename = f"{codigo}_prompt_imagen.txt"
            sheets_service.save_file_to_drive(textos_folder_id, prompt_filename, image_prompt)
            print(f"  ✅ {prompt_filename} generado y guardado")
        
        # CASO ESPECIAL: IMAGE_PROMPT_AWAITING → Generar imagen base
        if current_state == 'IMAGE_PROMPT_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
            
            if not textos_folder_id or not imagenes_folder_id:
                return jsonify({'error': 'No se encontraron las carpetas textos/ o imagenes/'}), 400
            
            # Leer prompt de imagen
            prompt_filename = f"{codigo}_prompt_imagen.txt"
            image_prompt = sheets_service.get_file_from_drive(textos_folder_id, prompt_filename)
            if not image_prompt:
                return jsonify({'error': f'No se encontró {prompt_filename}'}), 400
            
            # Configurar OpenAI para DALL-E 3
            print("🤖 Generando imagen con DALL-E 3...")
            print(f"📝 Prompt: {image_prompt}")
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Generar imagen con DALL-E 3
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            # Descargar imagen desde URL
            image_url = response.data[0].url
            image_response = requests.get(image_url)
            
            if image_response.status_code != 200:
                return jsonify({'error': 'No se pudo descargar la imagen generada'}), 500
            
            image_bytes = image_response.content
            
            # Guardar imagen en Drive/imagenes/
            image_filename = f"{codigo}_imagen_base.png"
            sheets_service.save_image_to_drive(imagenes_folder_id, image_filename, image_bytes)
            print(f"  ✅ {image_filename} generado y guardado")
        
        # CASO ESPECIAL: IMAGE_BASE_AWAITING → Formatear imágenes con Cloudinary
        if current_state == 'IMAGE_BASE_AWAITING':
            print("🖼️ Formateando imágenes con Cloudinary (crop inteligente)...")
            
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
            
            if not imagenes_folder_id:
                return jsonify({'error': 'No se encontró la carpeta imagenes/'}), 400
            
            # Buscar imagen_base.png en Drive
            base_image_filename = f"{codigo}_imagen_base.png"
            print(f"  🔍 Buscando {base_image_filename}...")
            
            files = sheets_service.drive_service.files().list(
                q=f"name='{base_image_filename}' and '{imagenes_folder_id}' in parents and trashed=false",
                fields='files(id, name)'
            ).execute().get('files', [])
            
            if not files:
                return jsonify({'error': f'Imagen base {base_image_filename} no encontrada en Drive'}), 404
            
            base_image_file_id = files[0]['id']
            print(f"  ✅ Encontrada: {base_image_file_id}")
            
            # Descargar imagen base
            print(f"  📥 Descargando imagen base...")
            request_download = sheets_service.drive_service.files().get_media(fileId=base_image_file_id)
            
            import io
            fh = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request_download)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            image_bytes = fh.getvalue()
            print(f"  ✅ Descargada: {len(image_bytes)} bytes")
            
            # Subir a Cloudinary
            print(f"  📤 Subiendo a Cloudinary...")
            
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(image_bytes)
            
            try:
                # Subir imagen a Cloudinary
                upload_result = cloudinary.uploader.upload(
                    tmp_path,
                    resource_type='image',
                    public_id=f"lavelo_blog/{codigo}_imagen_base",
                    overwrite=True
                )
                
                public_id = upload_result['public_id']
                print(f"  ✅ Subida a Cloudinary: {public_id}")
                
                # Definir formatos con crop inteligente
                all_formats = {
                    'instagram_1x1': {
                        'width': 1080, 'height': 1080,
                        'crop': 'fill', 'gravity': 'auto:subject',
                        'network': 'instagram'
                    },
                    'instagram_stories_9x16': {
                        'width': 1080, 'height': 1920,
                        'crop': 'fill', 'gravity': 'auto:subject',
                        'network': 'instagram'
                    },
                    'linkedin_16x9': {
                        'width': 1200, 'height': 627,
                        'crop': 'fill', 'gravity': 'auto:subject',
                        'network': 'linkedin'
                    },
                    'twitter_16x9': {
                        'width': 1200, 'height': 675,
                        'crop': 'fill', 'gravity': 'auto:subject',
                        'network': 'twitter'
                    },
                    'facebook_16x9': {
                        'width': 1200, 'height': 630,
                        'crop': 'fill', 'gravity': 'auto:subject',
                        'network': 'facebook'
                    }
                }
                
                # Filtrar solo formatos para redes activas
                formats = {k: v for k, v in all_formats.items() if redes.get(v['network'], True)}
                print(f"📱 Generando formatos de imagen para: {[v['network'] for v in formats.values()]}")
                
                # Generar cada formato
                for format_name, specs in formats.items():
                    print(f"  🖼️  Generando {format_name}...")
                    
                    # Crear transformación
                    transformation = {
                        'width': specs['width'],
                        'height': specs['height'],
                        'crop': specs['crop'],
                        'gravity': specs['gravity'],
                        'quality': 'auto:best',
                        'format': 'png'
                    }
                    
                    try:
                        # Generar transformación explícita
                        explicit_result = cloudinary.uploader.explicit(
                            public_id,
                            type='upload',
                            resource_type='image',
                            eager=[transformation],
                            eager_async=False
                        )
                        
                        # Obtener URL de la transformación
                        if 'eager' in explicit_result and len(explicit_result['eager']) > 0:
                            url = explicit_result['eager'][0]['secure_url']
                            print(f"     ✅ URL generada: {url}")
                            
                            # Descargar imagen transformada
                            image_response = requests.get(url, timeout=60)
                            
                            if image_response.status_code == 200:
                                formatted_image_bytes = image_response.content
                                print(f"     📦 Descargada: {len(formatted_image_bytes)} bytes")
                                
                                # Guardar en Drive
                                format_filename = f"{codigo}_{format_name}.png"
                                sheets_service.save_image_to_drive(imagenes_folder_id, format_filename, formatted_image_bytes)
                                
                                # Marcar checkbox correspondiente
                                checkbox_field = format_name.replace('_', '_image').replace('image', '', 1) if 'instagram' not in format_name else format_name.replace('_', '_image', 1)
                                # Mapeo correcto de nombres
                                checkbox_map = {
                                    'instagram_1x1': 'instagram_image',
                                    'instagram_stories_9x16': 'instagram_stories_image',
                                    'linkedin_16x9': 'linkedin_image',
                                    'twitter_16x9': 'twitter_image',
                                    'facebook_16x9': 'facebook_image'
                                }
                                checkbox_field = checkbox_map.get(format_name, format_name)
                                sheets_service.update_post_field(codigo, checkbox_field, 'TRUE')
                                
                                print(f"  ✅ {format_filename} generado ({specs['width']}x{specs['height']})")
                            else:
                                print(f"  ❌ Error descargando {format_name}: {image_response.status_code}")
                        else:
                            print(f"  ❌ No se generó transformación para {format_name}")
                            
                    except Exception as e:
                        print(f"  ❌ Error generando {format_name}: {str(e)}")
                        continue
                        
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # CASO ESPECIAL: IMAGE_FORMATS_AWAITING → Generar script de video
        if current_state == 'IMAGE_FORMATS_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            
            if not textos_folder_id:
                return jsonify({'error': 'No se encontró la carpeta textos/'}), 400
            
            # Leer base.txt
            base_filename = f"{codigo}_base.txt"
            base_text = sheets_service.get_file_from_drive(textos_folder_id, base_filename)
            if not base_text:
                return jsonify({'error': f'No se encontró {base_filename}'}), 400
            
            # Llamar a Claude para generar script de video
            print("🤖 Generando script de video con Claude...")
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            prompt = f"""Genera un script para un video corto de EXACTAMENTE 15 segundos sobre el siguiente contenido de triatlón.

El script debe incluir:
- EXACTAMENTE 4 escenas (3-4 segundos cada una)
- Narración clara y concisa (voz en off)
- Descripción de escenas visuales
- Tono motivacional y educativo
- Formato: [ESCENA X - Xseg] Narración | Visual

Contenido:
{base_text}

Genera SOLO el script con 4 escenas, sin explicaciones adicionales."""
            
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            video_script = message.content[0].text
            
            # Guardar script en Drive/textos/
            script_filename = f"{codigo}_script_video.txt"
            sheets_service.save_file_to_drive(textos_folder_id, script_filename, video_script)
            print(f"  ✅ {script_filename} generado y guardado")
        
        # CASO ESPECIAL: VIDEO_PROMPT_AWAITING → Generar video base con Sora
        if current_state == 'VIDEO_PROMPT_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            videos_folder_id = sheets_service.get_subfolder_id(folder_id, 'videos')
            
            if not textos_folder_id or not videos_folder_id:
                return jsonify({'error': 'No se encontraron las carpetas textos/ o videos/'}), 400
            
            # Leer script de video
            script_filename = f"{codigo}_script_video.txt"
            video_script = sheets_service.get_file_from_drive(textos_folder_id, script_filename)
            if not video_script:
                return jsonify({'error': f'No se encontró {script_filename}'}), 400
            
            # Extraer prompt del script de video
            # El script puede tener diferentes formatos, intentamos extraer el contenido útil
            print(f"📝 Script de video:\n{video_script[:500]}...")
            
            # Opción 1: Si tiene formato estructurado con "Narración:"
            narrations = []
            for line in video_script.split('\n'):
                if 'Narración:' in line:
                    narration = line.split('Narración:')[1].strip().strip('"*')
                    if narration:
                        narrations.append(narration)
            
            if narrations:
                video_prompt = ' '.join(narrations)
            else:
                # Opción 2: Usar el script completo limpio
                video_prompt = video_script.strip()
            
            # Validar que tenemos un prompt
            if not video_prompt or len(video_prompt) < 10:
                return jsonify({'error': 'El script de video está vacío o es demasiado corto. Verifica el contenido del script.'}), 400
            
            # Limitar a 500 caracteres (límite de Veo)
            if len(video_prompt) > 500:
                video_prompt = video_prompt[:500]
            
            # Configurar Google GenAI para Veo 3.1
            print("🎬 Generando video con Veo 3.1...")
            print(f"📝 Prompt ({len(video_prompt)} chars): {video_prompt[:200]}...")
            client = genai.Client(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
            
            # Generar video con Veo 3.1
            operation = client.models.generate_videos(
                model="veo-3.1-fast-generate-preview",
                prompt=video_prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    resolution="1080p"
                )
            )
            
            # Esperar a que se genere el video (puede tardar 2-5 min)
            print("⏳ Esperando generación de video...")
            while not operation.done:
                time.sleep(20)
                operation = client.operations.get(operation)
                state = operation.metadata.get('state', 'processing') if operation.metadata else 'processing'
                print(f"  Estado: {state}...")
            
            # Obtener video generado
            generated_video = operation.response.generated_videos[0]
            
            # Descargar video (ya devuelve bytes)
            video_bytes = client.files.download(file=generated_video.video)
            
            # Guardar video en Drive/videos/
            video_filename = f"{codigo}_video_base.mp4"
            sheets_service.save_image_to_drive(videos_folder_id, video_filename, video_bytes)
            print(f"  ✅ {video_filename} generado y guardado")
        
        # CASO ESPECIAL: VIDEO_BASE_AWAITING → Formatear videos con Cloudinary
        if current_state == 'VIDEO_BASE_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            videos_folder_id = sheets_service.get_subfolder_id(folder_id, 'videos')
            
            if not videos_folder_id:
                return jsonify({'error': 'No se encontró la carpeta videos/'}), 400
            
            # Leer video base
            base_video_filename = f"{codigo}_video_base.mp4"
            video_bytes = sheets_service.get_image_from_drive(videos_folder_id, base_video_filename)
            if not video_bytes:
                return jsonify({'error': f'No se encontró {base_video_filename}'}), 400
            
            # Formatear videos con Cloudinary (smart reframing con IA)
            print("🎬 Formateando videos con Cloudinary AI...")
            
            # Crear archivo temporal para subir a Cloudinary
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_file.write(video_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Subir video a Cloudinary
                print(f"  📤 Subiendo {base_video_filename} a Cloudinary...")
                upload_result = cloudinary.uploader.upload(
                    tmp_path,
                    resource_type='video',
                    public_id=f"lavelo_blog/{codigo}_video_base",
                    overwrite=True
                )
                
                public_id = upload_result['public_id']
                print(f"  ✅ Subido: {public_id}")
                
                # Definir formatos con transformaciones (usando gravity: center para free tier)
                formats = {
                    'feed_16x9': {
                        'width': 1920, 'height': 1080,
                        'crop': 'fill', 'gravity': 'center'
                    },
                    'stories_9x16': {
                        'width': 1080, 'height': 1920,
                        'crop': 'fill', 'gravity': 'center'
                    },
                    'shorts_9x16': {
                        'width': 1080, 'height': 1920,
                        'crop': 'fill', 'gravity': 'center'
                    },
                    'tiktok_9x16': {
                        'width': 1080, 'height': 1920,
                        'crop': 'fill', 'gravity': 'center'
                    }
                }
                
                # Generar cada formato usando Explicit API (crea la transformación)
                for format_name, specs in formats.items():
                    print(f"  🎬 Generando {format_name}...")
                    
                    # Crear transformación explícita en Cloudinary
                    transformation = {
                        'width': specs['width'],
                        'height': specs['height'],
                        'crop': specs['crop'],
                        'gravity': specs['gravity'],
                        'quality': 'auto',
                        'format': 'mp4'
                    }
                    
                    try:
                        print(f"     Transformación: {transformation}")
                        
                        # Generar transformación explícita (esto fuerza a Cloudinary a crearla)
                        explicit_result = cloudinary.uploader.explicit(
                            public_id,
                            type='upload',
                            resource_type='video',
                            eager=[transformation],
                            eager_async=False  # Esperar a que se genere
                        )
                        
                        print(f"     Resultado: {explicit_result.get('eager', 'No eager')}")
                        
                        # Obtener URL de la transformación generada
                        if 'eager' in explicit_result and len(explicit_result['eager']) > 0:
                            url = explicit_result['eager'][0]['secure_url']
                            print(f"     ✅ URL generada: {url}")
                            
                            # Descargar video transformado
                            video_response = requests.get(url, timeout=120)
                            
                            if video_response.status_code == 200:
                                formatted_video_bytes = video_response.content
                                print(f"     📦 Descargado: {len(formatted_video_bytes)} bytes")
                                
                                # Guardar en Drive
                                format_filename = f"{codigo}_{format_name}.mp4"
                                sheets_service.save_image_to_drive(videos_folder_id, format_filename, formatted_video_bytes)
                                print(f"  ✅ {format_filename} generado ({specs['width']}x{specs['height']})")
                            else:
                                print(f"  ⚠️ Error HTTP {video_response.status_code} descargando {format_name}")
                        else:
                            print(f"  ⚠️ No se generó transformación para {format_name}")
                            print(f"     Response completo: {explicit_result}")
                            
                    except Exception as e:
                        print(f"  ❌ Error generando {format_name}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        # CASO ESPECIAL: VIDEO_FORMATS_AWAITING → Verificar archivos
        if current_state == 'VIDEO_FORMATS_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
            imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
            videos_folder_id = sheets_service.get_subfolder_id(folder_id, 'videos')
            
            print("🔍 Verificando archivos generados (solo redes activas)...")
            
            # Textos base (siempre requeridos)
            textos_esperados = [
                f"{codigo}_base.txt",
                f"{codigo}_prompt_imagen.txt",
                f"{codigo}_script_video.txt"
            ]
            
            # Añadir textos de redes activas
            if redes.get('instagram', True):
                textos_esperados.append(f"{codigo}_instagram.txt")
            if redes.get('linkedin', True):
                textos_esperados.append(f"{codigo}_linkedin.txt")
            if redes.get('twitter', True):
                textos_esperados.append(f"{codigo}_twitter.txt")
            if redes.get('facebook', True):
                textos_esperados.append(f"{codigo}_facebook.txt")
            if redes.get('tiktok', True):
                textos_esperados.append(f"{codigo}_tiktok.txt")
            
            # Imágenes base (siempre requeridas)
            imagenes_esperadas = [f"{codigo}_imagen_base.png"]
            
            # Añadir formatos de imagen de redes activas
            if redes.get('instagram', True):
                imagenes_esperadas.extend([
                    f"{codigo}_instagram_1x1.png",
                    f"{codigo}_instagram_stories_9x16.png"
                ])
            if redes.get('linkedin', True):
                imagenes_esperadas.append(f"{codigo}_linkedin_16x9.png")
            if redes.get('twitter', True):
                imagenes_esperadas.append(f"{codigo}_twitter_16x9.png")
            if redes.get('facebook', True):
                imagenes_esperadas.append(f"{codigo}_facebook_16x9.png")
            
            # Videos base (siempre requeridos)
            videos_esperados = [f"{codigo}_video_base.mp4"]
            
            # Añadir formatos de video de redes activas
            if redes.get('instagram', True):
                videos_esperados.extend([
                    f"{codigo}_feed_16x9.mp4",
                    f"{codigo}_stories_9x16.mp4"
                ])
            if redes.get('tiktok', True):
                videos_esperados.append(f"{codigo}_tiktok_9x16.mp4")
            
            archivos_faltantes = []
            
            # Verificar textos
            for archivo in textos_esperados:
                contenido = sheets_service.get_file_from_drive(textos_folder_id, archivo)
                if not contenido:
                    archivos_faltantes.append(f"textos/{archivo}")
                else:
                    print(f"  ✅ {archivo}")
            
            # Verificar imágenes
            for archivo in imagenes_esperadas:
                imagen = sheets_service.get_image_from_drive(imagenes_folder_id, archivo)
                if not imagen:
                    archivos_faltantes.append(f"imagenes/{archivo}")
                else:
                    print(f"  ✅ {archivo}")
            
            # Verificar videos
            for archivo in videos_esperados:
                video = sheets_service.get_image_from_drive(videos_folder_id, archivo)
                if not video:
                    archivos_faltantes.append(f"videos/{archivo}")
                else:
                    print(f"  ✅ {archivo}")
            
            if archivos_faltantes:
                print(f"⚠️ Archivos faltantes: {', '.join(archivos_faltantes)}")
                return jsonify({
                    'error': 'Faltan archivos',
                    'missing_files': archivos_faltantes
                }), 400
            
            print("✅ Todos los archivos verificados correctamente")
        
        # Marcar checkboxes como TRUE
        for checkbox in transition['checkboxes']:
            sheets_service.update_post_field(codigo, checkbox, 'TRUE')
            print(f"  ✅ {checkbox} = TRUE")
        
        # Actualizar estado en columna F
        sheets_service.update_post_field(codigo, 'estado', transition['next'])
        print(f"✅ Estado actualizado: {current_state} → {transition['next']}")
        
        return jsonify({
            'success': True,
            'message': f"{transition['action']} completado",
            'previous_state': current_state,
            'new_state': transition['next']
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API: Generar prompt de imagen
@app.route('/api/generate-image-prompt', methods=['POST'])
def generate_image_prompt():
    return jsonify({'success': True, 'message': 'Prompt generado'})

# API: Generar imagen base
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    return jsonify({'success': True, 'message': 'Imagen generada'})

# API: Formatear imágenes
@app.route('/api/format-images', methods=['POST'])
def format_images():
    """Formatear imagen base en múltiples formatos usando Cloudinary"""
    try:
        data = request.json
        codigo = data.get('codigo')
        
        if not codigo:
            return jsonify({'error': 'Código requerido'}), 400
        
        print(f"\n🎨 Formateando imágenes para {codigo}...")
        
        # 1. Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return jsonify({'error': f'Post {codigo} no encontrado'}), 404
        
        if not post.get('drive_folder_id'):
            return jsonify({'error': f'Post {codigo} no tiene carpeta en Drive'}), 404
        
        folder_id = post['drive_folder_id']
        
        # 2. Obtener carpeta imagenes
        imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
        if not imagenes_folder_id:
            return jsonify({'error': 'Carpeta imagenes no encontrada'}), 404
        
        # 3. Buscar imagen_base.png en Drive
        base_image_filename = f"{codigo}_imagen_base.png"
        print(f"  🔍 Buscando {base_image_filename}...")
        
        files = sheets_service.drive_service.files().list(
            q=f"name='{base_image_filename}' and '{imagenes_folder_id}' in parents and trashed=false",
            fields='files(id, name)'
        ).execute().get('files', [])
        
        if not files:
            return jsonify({'error': f'Imagen base {base_image_filename} no encontrada en Drive'}), 404
        
        base_image_file_id = files[0]['id']
        print(f"  ✅ Encontrada: {base_image_file_id}")
        
        # 4. Descargar imagen base
        print(f"  📥 Descargando imagen base...")
        request_download = sheets_service.drive_service.files().get_media(fileId=base_image_file_id)
        
        import io
        fh = io.BytesIO()
        from googleapiclient.http import MediaIoBaseDownload
        downloader = MediaIoBaseDownload(fh, request_download)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        image_bytes = fh.getvalue()
        print(f"  ✅ Descargada: {len(image_bytes)} bytes")
        
        # 5. Subir a Cloudinary
        print(f"  📤 Subiendo a Cloudinary...")
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(image_bytes)
        
        try:
            # Subir imagen a Cloudinary
            upload_result = cloudinary.uploader.upload(
                tmp_path,
                resource_type='image',
                public_id=f"lavelo_blog/{codigo}_imagen_base",
                overwrite=True
            )
            
            public_id = upload_result['public_id']
            print(f"  ✅ Subida a Cloudinary: {public_id}")
            
            # 6. Definir formatos con crop inteligente
            formats = {
                'instagram_1x1': {
                    'width': 1080, 'height': 1080,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'instagram_stories_9x16': {
                    'width': 1080, 'height': 1920,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'linkedin_16x9': {
                    'width': 1200, 'height': 627,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'twitter_16x9': {
                    'width': 1200, 'height': 675,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'facebook_16x9': {
                    'width': 1200, 'height': 630,
                    'crop': 'fill', 'gravity': 'auto:subject'
                }
            }
            
            # 7. Generar cada formato
            for format_name, specs in formats.items():
                print(f"  🖼️  Generando {format_name}...")
                
                # Crear transformación
                transformation = {
                    'width': specs['width'],
                    'height': specs['height'],
                    'crop': specs['crop'],
                    'gravity': specs['gravity'],
                    'quality': 'auto',
                    'format': 'png'
                }
                
                try:
                    # Generar transformación explícita
                    explicit_result = cloudinary.uploader.explicit(
                        public_id,
                        type='upload',
                        resource_type='image',
                        eager=[transformation],
                        eager_async=False
                    )
                    
                    # Obtener URL de la transformación
                    if 'eager' in explicit_result and len(explicit_result['eager']) > 0:
                        url = explicit_result['eager'][0]['secure_url']
                        print(f"     ✅ URL generada: {url}")
                        
                        # Descargar imagen transformada
                        image_response = requests.get(url, timeout=60)
                        
                        if image_response.status_code == 200:
                            formatted_image_bytes = image_response.content
                            print(f"     📦 Descargada: {len(formatted_image_bytes)} bytes")
                            
                            # Guardar en Drive
                            format_filename = f"{codigo}_{format_name}.png"
                            sheets_service.save_image_to_drive(imagenes_folder_id, format_filename, formatted_image_bytes)
                            print(f"  ✅ {format_filename} generado ({specs['width']}x{specs['height']})")
                        else:
                            print(f"  ❌ Error descargando {format_name}: {image_response.status_code}")
                    else:
                        print(f"  ❌ No se generó transformación para {format_name}")
                        
                except Exception as e:
                    print(f"  ❌ Error generando {format_name}: {str(e)}")
                    continue
            
            # 8. Actualizar checkboxes en Sheet
            sheets_service.update_post_field(codigo, 'instagram_image', 'TRUE')
            sheets_service.update_post_field(codigo, 'instagram_stories_image', 'TRUE')
            sheets_service.update_post_field(codigo, 'linkedin_image', 'TRUE')
            sheets_service.update_post_field(codigo, 'twitter_image', 'TRUE')
            sheets_service.update_post_field(codigo, 'facebook_image', 'TRUE')
            
            # 9. Cambiar estado
            sheets_service.update_post_field(codigo, 'estado', 'IMAGE_FORMATS_AWAITING')
            
            print(f"✅ Formatos de imagen generados correctamente")
            
            return jsonify({
                'success': True,
                'message': 'Formatos de imagen generados con Cloudinary (crop inteligente)',
                'formats': list(formats.keys())
            })
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
    except Exception as e:
        print(f"❌ Error formateando imágenes: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API: Generar script video
@app.route('/api/generate-video-script', methods=['POST'])
def generate_video_script():
    return jsonify({'success': True, 'message': 'Script generado'})

# API: Generar video base
@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    return jsonify({'success': True, 'message': 'Video generado'})

# API: Formatear videos
@app.route('/api/format-videos', methods=['POST'])
def format_videos():
    return jsonify({'success': True, 'message': 'Videos formateados'})

# API: Actualizar campo de post
@app.route('/api/posts/<codigo>/update', methods=['POST'])
def update_post(codigo):
    if 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sheets_service.authenticate(session['credentials'])
    
    data = request.json
    field = data.get('field')
    value = data.get('value')
    
    success = sheets_service.update_post_field(codigo, field, value)
    
    if success:
        return jsonify({'success': True, 'message': f'{field} actualizado'})
    
    return jsonify({'success': False, 'message': 'Error al actualizar'}), 500

# API: Publicar
@app.route('/api/publish', methods=['POST'])
def publish():
    return jsonify({'success': True, 'message': 'Publicado correctamente'})

# API: Resetear fases dependientes
@app.route('/api/posts/<codigo>/reset-phases', methods=['POST'])
def reset_phases(codigo):
    """Resetear fases dependientes cuando se edita una fase validada"""
    try:
        data = request.json
        estado = data.get('estado')
        
        if not estado:
            return jsonify({'error': 'Estado requerido'}), 400
        
        # Llamar a la función de sheets_service
        success = sheets_service.reset_dependent_phases(codigo, estado)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Fases dependientes reseteadas correctamente'
            })
        else:
            return jsonify({'error': 'Error reseteando fases'}), 500
            
    except Exception as e:
        print(f"❌ Error en reset_phases: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API: Eliminar post (Sheet + Drive)
@app.route('/api/posts/<codigo>/delete', methods=['DELETE'])
def delete_post(codigo):
    """Eliminar post de Sheet y Drive"""
    try:
        print(f"🗑️ Eliminando post {codigo}...")
        
        # 1. Obtener post para tener el Drive Folder ID
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return jsonify({'error': f'Post {codigo} no encontrado'}), 404
        
        # 2. Eliminar carpeta de Drive si existe
        if post.get('drive_folder_id'):
            try:
                sheets_service.drive_service.files().delete(fileId=post['drive_folder_id']).execute()
                print(f"  ✅ Carpeta de Drive eliminada: {post['drive_folder_id']}")
            except Exception as e:
                print(f"  ⚠️ Error eliminando carpeta de Drive: {e}")
        
        # 3. Eliminar fila de Sheet
        # Buscar fila del post
        SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')
        result = sheets_service.service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!C2:C'
        ).execute()
        
        rows = result.get('values', [])
        row_index = None
        
        for i, row in enumerate(rows):
            if row and row[0] == codigo:
                row_index = i + 2  # +2 porque empezamos en fila 2
                break
        
        if row_index:
            # Eliminar fila
            request_body = {
                'requests': [{
                    'deleteDimension': {
                        'range': {
                            'sheetId': 0,  # Asumiendo que es la primera hoja
                            'dimension': 'ROWS',
                            'startIndex': row_index - 1,
                            'endIndex': row_index
                        }
                    }
                }]
            }
            
            sheets_service.service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=request_body
            ).execute()
            
            print(f"  ✅ Fila {row_index} eliminada de Sheet")
        
        return jsonify({
            'success': True,
            'message': f'Post {codigo} eliminado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error eliminando post: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API: Actualizar configuración de redes de un post
@app.route('/api/posts/<codigo>/update-networks', methods=['POST'])
def update_networks(codigo):
    """Actualizar configuración de redes sociales de un post"""
    try:
        data = request.json
        redes = data.get('redes', {})
        
        if not redes:
            return jsonify({'error': 'Configuración de redes requerida'}), 400
        
        print(f"📱 Actualizando redes para post {codigo}: {redes}")
        
        # Guardar todas las redes en una sola llamada batch
        success = sheets_service.batch_update_networks(codigo, redes)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Configuración de redes actualizada'
            })
        else:
            return jsonify({'error': 'Error actualizando redes en Sheet'}), 500
        
    except Exception as e:
        print(f"❌ Error actualizando redes: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API: Subir imagen manual
@app.route('/api/posts/<codigo>/upload-image', methods=['POST'])
def upload_manual_image(codigo):
    """Subir imagen manual del usuario"""
    try:
        # 1. Verificar que hay archivo
        if 'image' not in request.files:
            return jsonify({'error': 'No se envió ninguna imagen'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        # 2. Validar formato
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Formato no permitido. Usa PNG o JPG'}), 400
        
        # 3. Validar tamaño (10MB)
        file.seek(0, 2)  # Ir al final
        file_size = file.tell()
        file.seek(0)  # Volver al inicio
        
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return jsonify({'error': 'Archivo muy grande. Máximo 10MB'}), 400
        
        # 4. Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return jsonify({'error': f'Post {codigo} no encontrado'}), 404
        
        if not post.get('drive_folder_id'):
            return jsonify({'error': f'Post {codigo} no tiene carpeta en Drive'}), 404
        
        # 5. Obtener carpeta imagenes
        folder_id = post['drive_folder_id']
        imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes', create_if_missing=True)
        
        if not imagenes_folder_id:
            return jsonify({'error': 'No se pudo acceder a la carpeta imagenes'}), 500
        
        # 6. Leer bytes de la imagen
        image_bytes = file.read()
        
        # 7. Guardar en Drive como imagen_base.png
        filename = f"{codigo}_imagen_base.png"
        success = sheets_service.save_image_to_drive(imagenes_folder_id, filename, image_bytes)
        
        if not success:
            return jsonify({'error': 'Error guardando imagen en Drive'}), 500
        
        print(f"✅ Imagen manual guardada: {filename} ({file_size} bytes)")
        
        # 8. Crear prompt placeholder
        from datetime import datetime
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        prompt_placeholder = f"Imagen subida manualmente por el usuario\nFecha: {fecha}\nArchivo original: {file.filename}\nTamaño: {file_size} bytes"
        
        # 9. Guardar prompt placeholder
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        sheets_service.save_file_to_drive(textos_folder_id, f"{codigo}_prompt_imagen.txt", prompt_placeholder)
        
        # 10. Actualizar checkboxes
        sheets_service.update_post_field(codigo, 'image_prompt', 'TRUE')
        sheets_service.update_post_field(codigo, 'image_base', 'TRUE')
        
        # 11. Cambiar estado a IMAGE_BASE_AWAITING (para que revise)
        sheets_service.update_post_field(codigo, 'estado', 'IMAGE_BASE_AWAITING')
        
        print(f"✅ Checkboxes actualizados, estado: IMAGE_BASE_AWAITING")
        
        return jsonify({
            'success': True,
            'message': f'✅ Imagen subida correctamente!\n\nArchivo: {file.filename}\nTamaño: {round(file_size / 1024, 2)} KB\n\n🔄 Recarga la página para verla.',
            'filename': filename
        })
        
    except Exception as e:
        print(f"❌ Error subiendo imagen: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API: Chat con IA para crear posts
@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint de chat con Claude para crear posts"""
    try:
        data = request.json
        message = data.get('message')
        history = data.get('history', [])
        
        if not message:
            return jsonify({'error': 'Mensaje requerido'}), 400
        
        # Llamar a Claude con herramientas MCP
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Definir herramientas MCP disponibles
        tools = [
            {
                "name": "create_post",
                "description": "Crea un nuevo post en Google Sheets y Drive. Genera código automático, crea carpeta en Drive y guarda el texto base.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "titulo": {
                            "type": "string",
                            "description": "Título del post"
                        },
                        "contenido": {
                            "type": "string",
                            "description": "Contenido completo del texto base del post"
                        },
                        "categoria": {
                            "type": "string",
                            "description": "Categoría del post (racing, training, training-science)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags del post"
                        }
                    },
                    "required": ["titulo", "contenido", "categoria"]
                }
            },
            {
                "name": "list_posts",
                "description": "Lista todos los posts existentes con su estado actual",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "update_image_prompt",
                "description": "Actualiza el prompt de generación de imagen de un post existente. Guarda el nuevo prompt en Drive y marca el checkbox correspondiente.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "codigo": {
                            "type": "string",
                            "description": "Código del post (ej: 20251023-1)"
                        },
                        "nuevo_prompt": {
                            "type": "string",
                            "description": "Nuevo prompt optimizado para generación de imagen"
                        }
                    },
                    "required": ["codigo", "nuevo_prompt"]
                }
            },
            {
                "name": "update_video_script",
                "description": "Actualiza el script de video de un post existente. Guarda el nuevo script en Drive y marca el checkbox correspondiente.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "codigo": {
                            "type": "string",
                            "description": "Código del post (ej: 20251023-1)"
                        },
                        "nuevo_script": {
                            "type": "string",
                            "description": "Nuevo script optimizado para video"
                        }
                    },
                    "required": ["codigo", "nuevo_script"]
                }
            },
            {
                "name": "regenerate_image",
                "description": "Actualiza el prompt de imagen Y marca el post para regenerar la imagen. Esto vuelve el post a la fase IMAGE_PROMPT_AWAITING para que se genere una nueva imagen con el prompt mejorado.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "codigo": {
                            "type": "string",
                            "description": "Código del post (ej: 20251023-1)"
                        },
                        "nuevo_prompt": {
                            "type": "string",
                            "description": "Nuevo prompt optimizado para regenerar la imagen"
                        }
                    },
                    "required": ["codigo", "nuevo_prompt"]
                }
            }
        ]
        
        # Construir mensajes para Claude
        messages = history + [{"role": "user", "content": message}]
        
        # System prompt para optimizar respuestas
        system_prompt = """Eres un asistente de contenido para Lavelo Triathlon Training.

ESTILO:
- Sé directo y ejecutivo
- Genera contenido de calidad sin preguntar demasiado
- Si falta info crítica, pregunta lo mínimo necesario
- Propón soluciones en vez de solo preguntar

CREAR POSTS:
- Genera contenido completo basándote en el tema
- Usa tono profesional pero motivador
- Cuando esté listo, pregunta: "¿Lo guardo?"
- Al confirmar, usa create_post()

MEJORAR PROMPTS:
- Analiza el prompt actual que te proporcionen
- Genera versión mejorada directamente
- Explica brevemente los cambios
- Pregunta: "¿Lo guardo?"
- Si menciona "regenerar imagen", usa regenerate_image()
- Si solo mejora prompt, usa update_image_prompt()
- Para scripts de video, usa update_video_script()

REGLAS:
- NO uses list_posts() sin que lo pidan
- NO guardes sin confirmación
- Sé conciso pero completo

Categorías: racing, training, training-science"""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
        
        # Si Claude quiere usar una herramienta
        if response.stop_reason == "tool_use":
            tool_use = next((block for block in response.content if block.type == "tool_use"), None)
            
            if tool_use:
                tool_name = tool_use.name
                tool_input = tool_use.input
                
                # Ejecutar herramienta
                if tool_name == "create_post":
                    result = execute_create_post(tool_input)
                elif tool_name == "list_posts":
                    result = execute_list_posts()
                elif tool_name == "update_image_prompt":
                    result = execute_update_image_prompt(tool_input)
                elif tool_name == "update_video_script":
                    result = execute_update_video_script(tool_input)
                elif tool_name == "regenerate_image":
                    result = execute_regenerate_image(tool_input)
                else:
                    result = {"error": f"Herramienta {tool_name} no implementada"}
                
                # Devolver resultado
                return jsonify({
                    'success': True,
                    'message': result.get('message', str(result)),
                    'tool_used': tool_name,
                    'tool_result': result
                })
        
        # Respuesta normal de texto
        text_content = next((block.text for block in response.content if hasattr(block, 'text')), '')
        
        return jsonify({
            'success': True,
            'message': text_content
        })
        
    except Exception as e:
        print(f"❌ Error en chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def execute_create_post(tool_input):
    """Ejecuta la herramienta create_post - Crea post completo en Sheets y Drive"""
    try:
        titulo = tool_input.get('titulo')
        contenido = tool_input.get('contenido')
        categoria = tool_input.get('categoria', 'training')
        tags = tool_input.get('tags', [])
        idea = tool_input.get('idea', '')  # Descripción corta opcional
        
        # Generar código automático (formato: YYYYMMDD-N)
        from datetime import datetime
        fecha_str = datetime.now().strftime('%Y%m%d')
        fecha_display = datetime.now().strftime('%d/%m/%Y')
        hora_display = datetime.now().strftime('%H:%M:%S')
        
        # Obtener posts existentes para calcular el número
        posts = sheets_service.get_posts()
        posts_hoy = [p for p in posts if p['codigo'].startswith(fecha_str)]
        numero = len(posts_hoy) + 1
        codigo = f"{fecha_str}-{numero}"
        
        print(f"📝 Creando post: {codigo} - {titulo}")
        
        # 1. Crear carpeta en Drive
        print(f"📁 Creando carpeta en Drive...")
        folder_metadata = {
            'name': f"{codigo} - {titulo[:50]}",  # Limitar longitud del nombre
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [os.getenv('DRIVE_ROOT_FOLDER_ID')]  # Carpeta raíz de posts
        }
        
        folder = sheets_service.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        drive_folder_id = folder.get('id')
        print(f"✅ Carpeta creada: {drive_folder_id}")
        
        # 2. Crear subcarpetas (textos, imagenes, videos)
        print(f"📁 Creando subcarpetas...")
        subfolders = ['textos', 'imagenes', 'videos']
        for subfolder_name in subfolders:
            sheets_service.get_subfolder_id(drive_folder_id, subfolder_name, create_if_missing=True)
        print(f"✅ Subcarpetas creadas")
        
        # 3. Guardar base.txt en carpeta textos
        print(f"💾 Guardando {codigo}_base.txt...")
        textos_folder_id = sheets_service.get_subfolder_id(drive_folder_id, 'textos')
        sheets_service.save_file_to_drive(textos_folder_id, f"{codigo}_base.txt", contenido)
        print(f"✅ Archivo base guardado")
        
        # 4. Crear fila en Google Sheets
        print(f"📊 Creando fila en Google Sheets...")
        
        # Estructura de columnas:
        # A=Fecha, B=Hora, C=Código, D=Título, E=Idea, F=ESTADO, G=Drive ID, H=URLs
        # I=base.txt, J-N=textos adaptados, O=prompt_imagen, P=imagen_base, Q-T=formatos imagen
        # U=script_video, V=video_base, W-Z=formatos video, AA-AF=publicaciones, AG=fecha_real, AH=notas
        
        new_row = [
            fecha_display,           # A: Fecha
            hora_display,            # B: Hora
            codigo,                  # C: Código
            titulo,                  # D: Título
            idea or titulo[:100],    # E: Idea (descripción corta)
            'BASE_TEXT_AWAITING',    # F: ESTADO
            drive_folder_id,         # G: Drive Folder ID
            '',                      # H: URLs (vacío por ahora)
            'TRUE',                  # I: base.txt ✓
            'FALSE',                 # J: instagram.txt
            'FALSE',                 # K: linkedin.txt
            'FALSE',                 # L: twitter.txt
            'FALSE',                 # M: facebook.txt
            'FALSE',                 # N: tiktok.txt
            'FALSE',                 # O: prompt_imagen
            'FALSE',                 # P: imagen_base
            'FALSE',                 # Q: instagram_1x1
            'FALSE',                 # R: instagram_stories
            'FALSE',                 # S: linkedin
            'FALSE',                 # T: twitter
            'FALSE',                 # U: facebook
            'FALSE',                 # V: script_video
            'FALSE',                 # W: video_base
            'FALSE',                 # X: feed_16x9
            'FALSE',                 # Y: stories_9x16
            'FALSE',                 # Z: shorts
            'FALSE',                 # AA: tiktok
            'FALSE',                 # AB: Blog publicado
            'FALSE',                 # AC: Instagram publicado
            'FALSE',                 # AD: LinkedIn publicado
            'FALSE',                 # AE: Twitter publicado
            'FALSE',                 # AF: Facebook publicado
            'FALSE',                 # AG: TikTok publicado
            '',                      # AH: Fecha publicación
            f"Creado por IA - Categoría: {categoria}",  # AI: Notas
            '',                      # AJ: Feedback
            'FALSE',                 # AK: Instagram activo
            'FALSE',                 # AL: LinkedIn activo
            'FALSE',                 # AM: Twitter activo
            'FALSE',                 # AN: Facebook activo
            'FALSE',                 # AO: TikTok activo
            'TRUE'                   # AP: Blog activo (siempre)
        ]
        
        # Añadir fila al final del sheet
        sheets_service.service.spreadsheets().values().append(
            spreadsheetId=os.getenv('GOOGLE_SHEETS_ID'),
            range='Sheet1!A:AP',
            valueInputOption='RAW',
            body={'values': [new_row]}
        ).execute()
        
        print(f"✅ Fila creada en Google Sheets")
        
        return {
            'success': True,
            'message': f"✅ Post creado exitosamente!\n\n📝 Código: {codigo}\n📄 Título: {titulo}\n📁 Carpeta Drive: {drive_folder_id}\n📊 Estado: BASE_TEXT_AWAITING\n\n✨ El post ya está visible en el panel principal y listo para generar textos adaptados.",
            'codigo': codigo,
            'titulo': titulo,
            'drive_folder_id': drive_folder_id
        }
        
    except Exception as e:
        print(f"❌ Error creando post: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"❌ Error creando post: {str(e)}"
        }

def execute_list_posts():
    """Ejecuta la herramienta list_posts"""
    try:
        posts = sheets_service.get_posts()
        
        # Formatear lista de posts
        posts_text = "\n".join([
            f"• {p['codigo']} - {p['titulo']} (Estado: {p['estado']})"
            for p in posts[:10]  # Limitar a 10 para no saturar
        ])
        
        return {
            'success': True,
            'message': f"📋 Posts actuales:\n\n{posts_text}\n\nTotal: {len(posts)} posts",
            'posts': posts
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f"❌ Error listando posts: {str(e)}"
        }

def execute_update_image_prompt(tool_input):
    """Actualiza el prompt de imagen de un post"""
    try:
        codigo = tool_input.get('codigo')
        nuevo_prompt = tool_input.get('nuevo_prompt')
        
        print(f"🎨 Actualizando prompt de imagen para post {codigo}")
        
        # 1. Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return {
                'success': False,
                'message': f"❌ Post {codigo} no encontrado"
            }
        
        if not post.get('drive_folder_id'):
            return {
                'success': False,
                'message': f"❌ Post {codigo} no tiene carpeta en Drive"
            }
        
        # 2. Obtener carpeta textos
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        
        if not textos_folder_id:
            return {
                'success': False,
                'message': f"❌ No se pudo acceder a la carpeta textos"
            }
        
        # 3. Guardar nuevo prompt
        filename = f"{codigo}_prompt_imagen.txt"
        sheets_service.save_file_to_drive(textos_folder_id, filename, nuevo_prompt)
        print(f"✅ Prompt guardado: {filename}")
        
        # 4. Actualizar checkbox en Sheets
        sheets_service.update_post_field(codigo, 'image_prompt', 'TRUE')
        print(f"✅ Checkbox image_prompt actualizado")
        
        return {
            'success': True,
            'message': f"✅ Prompt de imagen actualizado!\n\n📝 Post: {codigo}\n📁 Archivo: {filename}\n\n💡 El nuevo prompt se usará la próxima vez que generes la imagen.\n\n🔄 Recarga la página de detalles para ver el cambio.",
            'codigo': codigo,
            'filename': filename
        }
        
    except Exception as e:
        print(f"❌ Error actualizando prompt de imagen: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"❌ Error actualizando prompt: {str(e)}"
        }

def execute_update_video_script(tool_input):
    """Actualiza el script de video de un post"""
    try:
        codigo = tool_input.get('codigo')
        nuevo_script = tool_input.get('nuevo_script')
        
        print(f"🎬 Actualizando script de video para post {codigo}")
        
        # 1. Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return {
                'success': False,
                'message': f"❌ Post {codigo} no encontrado"
            }
        
        if not post.get('drive_folder_id'):
            return {
                'success': False,
                'message': f"❌ Post {codigo} no tiene carpeta en Drive"
            }
        
        # 2. Obtener carpeta textos
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        
        if not textos_folder_id:
            return {
                'success': False,
                'message': f"❌ No se pudo acceder a la carpeta textos"
            }
        
        # 3. Guardar nuevo script
        filename = f"{codigo}_script_video.txt"
        sheets_service.save_file_to_drive(textos_folder_id, filename, nuevo_script)
        print(f"✅ Script guardado: {filename}")
        
        # 4. Actualizar checkbox en Sheets
        sheets_service.update_post_field(codigo, 'video_prompt', 'TRUE')
        print(f"✅ Checkbox video_prompt actualizado")
        
        return {
            'success': True,
            'message': f"✅ Script de video actualizado!\n\n📝 Post: {codigo}\n📁 Archivo: {filename}\n\n💡 El nuevo script se usará la próxima vez que generes el video.\n\n🔄 Recarga la página de detalles para ver el cambio.",
            'codigo': codigo,
            'filename': filename
        }
        
    except Exception as e:
        print(f"❌ Error actualizando script de video: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"❌ Error actualizando script: {str(e)}"
        }

def execute_regenerate_image(tool_input):
    """Actualiza el prompt Y marca para regenerar la imagen"""
    try:
        codigo = tool_input.get('codigo')
        nuevo_prompt = tool_input.get('nuevo_prompt')
        
        print(f"🔄 Regenerando imagen para post {codigo}")
        
        # 1. Obtener post
        posts = sheets_service.get_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post:
            return {
                'success': False,
                'message': f"❌ Post {codigo} no encontrado"
            }
        
        if not post.get('drive_folder_id'):
            return {
                'success': False,
                'message': f"❌ Post {codigo} no tiene carpeta en Drive"
            }
        
        # 2. Guardar nuevo prompt
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        
        if not textos_folder_id:
            return {
                'success': False,
                'message': f"❌ No se pudo acceder a la carpeta textos"
            }
        
        filename = f"{codigo}_prompt_imagen.txt"
        sheets_service.save_file_to_drive(textos_folder_id, filename, nuevo_prompt)
        print(f"✅ Nuevo prompt guardado: {filename}")
        
        # 3. Marcar imagen_base = FALSE para forzar regeneración
        sheets_service.update_post_field(codigo, 'image_base', 'FALSE')
        print(f"✅ Checkbox image_base marcado como FALSE")
        
        # 4. Cambiar estado a IMAGE_PROMPT_AWAITING
        sheets_service.update_post_field(codigo, 'estado', 'IMAGE_PROMPT_AWAITING')
        print(f"✅ Estado cambiado a IMAGE_PROMPT_AWAITING")
        
        return {
            'success': True,
            'message': f"✅ Prompt actualizado y listo para regenerar!\n\n📝 Post: {codigo}\n📁 Nuevo prompt guardado\n🔄 Estado: IMAGE_PROMPT_AWAITING\n\n🎯 Ahora ve al panel principal y haz clic en VALIDATE para generar la nueva imagen con el prompt mejorado.",
            'codigo': codigo,
            'filename': filename
        }
        
    except Exception as e:
        print(f"❌ Error regenerando imagen: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"❌ Error regenerando imagen: {str(e)}"
        }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
