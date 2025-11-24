import os
import time
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Cargar variables de entorno ANTES de importar sheets_service
default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

from sheets_service import sheets_service
from anthropic import Anthropic
from openai import OpenAI
from google import genai
from google.genai import types
import requests
from io import BytesIO
from PIL import Image
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
        if folder == 'textos':
            if f'{codigo}_base.txt' in filename:
                sheets_service.update_post_field(codigo, 'base_text', 'TRUE')
                checkbox_updated = True
                print(f"✅ Checkbox base_text actualizado a TRUE")
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
                checkbox_updated = True
            elif 'script_video' in filename:
                sheets_service.update_post_field(codigo, 'video_prompt', 'TRUE')
                checkbox_updated = True
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
            'checkbox_updated': checkbox_updated
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
    
    if not codigo or not current_state:
        return jsonify({'error': 'Código y estado requeridos'}), 400
    
    try:
        sheets_service.authenticate(session['credentials'])
        
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
            
            # Llamar a Claude para generar textos adaptados
            print("🤖 Llamando a Claude API...")
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            platforms = {
                'instagram': 'Instagram (2200 caracteres max, tono visual y motivacional)',
                'linkedin': 'LinkedIn (3000 caracteres max, tono profesional)',
                'twitter': 'Twitter/X (280 caracteres max, tono conciso)',
                'facebook': 'Facebook (63206 caracteres max, tono conversacional)',
                'tiktok': 'TikTok (2200 caracteres max, tono juvenil y dinámico)'
            }
            
            for platform, description in platforms.items():
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
        
        # CASO ESPECIAL: IMAGE_BASE_AWAITING → Formatear imágenes
        if current_state == 'IMAGE_BASE_AWAITING':
            # Obtener folder_id del post
            posts = sheets_service.get_posts()
            post = next((p for p in posts if p['codigo'] == codigo), None)
            if not post or not post.get('drive_folder_id'):
                return jsonify({'error': 'Post no encontrado o sin carpeta de Drive'}), 400
            
            folder_id = post['drive_folder_id']
            imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
            
            if not imagenes_folder_id:
                return jsonify({'error': 'No se encontró la carpeta imagenes/'}), 400
            
            # Leer imagen base
            base_image_filename = f"{codigo}_imagen_base.png"
            image_bytes = sheets_service.get_image_from_drive(imagenes_folder_id, base_image_filename)
            if not image_bytes:
                return jsonify({'error': f'No se encontró {base_image_filename}'}), 400
            
            # Abrir imagen con Pillow
            print("🖼️ Formateando imágenes con Pillow...")
            base_image = Image.open(BytesIO(image_bytes))
            
            # Definir formatos
            formats = {
                'instagram_1x1': (1080, 1080),
                'instagram_stories_9x16': (1080, 1920),
                'linkedin_16x9': (1200, 627),
                'twitter_16x9': (1200, 675),
                'facebook_16x9': (1200, 630)
            }
            
            # Generar cada formato
            for format_name, (width, height) in formats.items():
                # Redimensionar manteniendo aspecto (crop al centro)
                img_copy = base_image.copy()
                img_copy.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Crear imagen final con fondo (si es necesario)
                final_img = Image.new('RGB', (width, height), (255, 255, 255))
                offset = ((width - img_copy.width) // 2, (height - img_copy.height) // 2)
                final_img.paste(img_copy, offset)
                
                # Guardar en bytes
                output = BytesIO()
                final_img.save(output, format='PNG')
                output_bytes = output.getvalue()
                
                # Guardar en Drive
                format_filename = f"{codigo}_{format_name}.png"
                sheets_service.save_image_to_drive(imagenes_folder_id, format_filename, output_bytes)
                print(f"  ✅ {format_filename} generado ({width}x{height})")
        
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
            
            # Extraer solo las narraciones del script para el prompt
            # Formato esperado: [ESCENA X - Xseg] Narración | Visual
            narrations = []
            for line in video_script.split('\n'):
                if 'Narración:' in line:
                    narration = line.split('Narración:')[1].strip().strip('"*')
                    narrations.append(narration)
            
            video_prompt = ' '.join(narrations)
            
            # Configurar Google GenAI para Veo 3.1
            print("🎬 Generando video con Veo 3.1...")
            print(f"📝 Prompt: {video_prompt[:100]}...")
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
            
            print("🔍 Verificando archivos generados...")
            
            # Verificar textos
            textos_esperados = [
                f"{codigo}_base.txt",
                f"{codigo}_instagram.txt",
                f"{codigo}_linkedin.txt",
                f"{codigo}_twitter.txt",
                f"{codigo}_facebook.txt",
                f"{codigo}_tiktok.txt",
                f"{codigo}_prompt_imagen.txt",
                f"{codigo}_script_video.txt"
            ]
            
            # Verificar imágenes
            imagenes_esperadas = [
                f"{codigo}_imagen_base.png",
                f"{codigo}_instagram_1x1.png",
                f"{codigo}_instagram_stories_9x16.png",
                f"{codigo}_linkedin_16x9.png",
                f"{codigo}_twitter_16x9.png",
                f"{codigo}_facebook_16x9.png"
            ]
            
            # Verificar videos
            videos_esperados = [
                f"{codigo}_video_base.mp4",
                f"{codigo}_feed_16x9.mp4",
                f"{codigo}_stories_9x16.mp4",
                f"{codigo}_shorts_9x16.mp4",
                f"{codigo}_tiktok_9x16.mp4"
            ]
            
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
    return jsonify({'success': True, 'message': 'Imágenes formateadas'})

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
