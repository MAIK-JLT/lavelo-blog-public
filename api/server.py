import os
import time
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flasgger import Swagger, swag_from
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler('/tmp/lavelo_api.log')  # Archivo
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno ANTES de importar sheets_service
# 1) Usa ENV_FILE o LAVELO_ENV_FILE si están definidos (p. ej. /var/www/vhosts/<dominio>/private/.env)
# 2) Si no, hace fallback al .env del repo (../.env) para desarrollo local
default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

from sheets_service import sheets_service
from services.publish_service import publish_service
from database import init_db
import db_service
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
import fal_client
import base64

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
 
# Permitir CORS y barras finales opcionales
CORS(app)
app.url_map.strict_slashes = False

# Asegurar que las tablas existen
try:
    init_db()
except Exception as _e:
    print(f"⚠️ No se pudo inicializar DB: {_e}")

# Configurar Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/api/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Lavelo Blog API",
        "description": "API para gestión automatizada de contenido del blog de triatlón",
        "version": "1.0.0",
        "contact": {
            "name": "Lavelo Blog",
            "url": "https://blog.lavelo.es"
        }
    },
    "host": "localhost:5001",
    "basePath": "/",
    "schemes": ["http"],
    "tags": [
        {"name": "Posts", "description": "Gestión de posts del blog"},
        {"name": "Content", "description": "Generación de contenido (textos, imágenes, videos)"},
        {"name": "Images", "description": "Generación y procesamiento de imágenes con Fal.ai"},
        {"name": "Videos", "description": "Generación de videos con IA (SeeDance 1.0)"},
        {"name": "OAuth", "description": "Autenticación OAuth para redes sociales"}
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

logger.info("🚀 Lavelo Blog API iniciada")
logger.info(f"📁 Directorio de trabajo: {os.getcwd()}")
logger.info(f"🔑 FAL_KEY configurado: {'✅' if os.getenv('FAL_KEY') else '❌'}")
logger.info(f"🔑 ANTHROPIC_API_KEY configurado: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")

# Middleware para loggear todas las requests
@app.before_request
def log_request():
    logger.info(f"📥 {request.method} {request.path}")

@app.after_request
def log_response(response):
    logger.info(f"📤 {request.method} {request.path} → {response.status_code}")
    return response

# Servir archivos de la carpeta falai
from flask import send_from_directory

@app.route('/falai/<path:filename>')
def serve_falai(filename):
    """Servir archivos estáticos de la carpeta falai"""
    falai_dir = os.path.join(os.path.dirname(__file__), '..', 'falai')
    return send_from_directory(falai_dir, filename)

# Evitar 404 por favicon
@app.route('/favicon.ico')
def favicon():
    return ('', 204)

# Servir el panel web desde el mismo servidor (evita CORS)
@app.route('/panel/')
def serve_panel_index():
    panel_dir = os.path.join(os.path.dirname(__file__), '..', 'panel')
    return send_from_directory(panel_dir, 'index.html')

@app.route('/panel/<path:path>')
def serve_panel_assets(path):
    panel_dir = os.path.join(os.path.dirname(__file__), '..', 'panel')
    return send_from_directory(panel_dir, path)

@app.route('/panel/<path:filename>')
def serve_panel(filename):
    """Servir archivos estáticos de la carpeta panel"""
    panel_dir = os.path.join(os.path.dirname(__file__), '..', 'panel')
    return send_from_directory(panel_dir, filename)

@app.route('/es/<path:filename>')
def serve_es(filename):
    """Servir archivos estáticos de la carpeta es"""
    es_dir = os.path.join(os.path.dirname(__file__), '..', 'es')
    return send_from_directory(es_dir, filename)

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
CACHE_TTL = 10  # 10 segundos (aumentado para mayor resiliencia)

def clear_posts_cache():
    """Limpiar caché de posts"""
    posts_cache['data'] = None
    posts_cache['timestamp'] = 0
    print("🗑️ Caché de posts limpiado")

def get_cached_posts():
    """Obtener posts con cache para evitar múltiples llamadas simultáneas"""
    import time
    current_time = time.time()
    
    if posts_cache['data'] is None or (current_time - posts_cache['timestamp']) > CACHE_TTL:
        try:
            posts_cache['data'] = db_service.get_all_posts()
            posts_cache['timestamp'] = current_time
        except Exception as e:
            print(f"⚠️ Error obteniendo posts (usando caché antiguo si existe): {e}")
            # Si hay caché antiguo, usarlo aunque esté expirado
            if posts_cache['data'] is not None:
                print("📦 Usando caché antiguo")
                return posts_cache['data']
            # Si no hay caché, propagar el error
            raise
    
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
    global sheets_service  # Declarar global PRIMERO
    
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
    
    # Forzar reconstrucción de servicios
    from sheets_service import SheetsService
    sheets_service = SheetsService()
    
    return redirect('/')

# API: Obtener todos los posts
@app.route('/api/posts', methods=['GET'])
def get_posts():
    """
    Obtener todos los posts del blog
    ---
    tags:
      - Posts
    responses:
      200:
        description: Lista de posts obtenida exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            posts:
              type: array
              items:
                type: object
                properties:
                  codigo:
                    type: string
                    example: "20251024-1"
                  titulo:
                    type: string
                    example: "Optimiza tu Posición de Triatlón"
                  estado:
                    type: string
                    example: "IMAGE_PROMPT_AWAITING"
                  drive_folder_id:
                    type: string
                    example: "1abc123def456"
      500:
        description: Error del servidor
    """
    try:
        posts = db_service.get_all_posts()
        return jsonify({'success': True, 'posts': posts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: Obtener un post por código
@app.route('/api/posts/<codigo>', methods=['GET'])
def get_post(codigo):
    """Obtener un post por su código desde SQLite"""
    try:
        post = db_service.get_post_by_codigo(codigo)
        if not post:
            return jsonify({'error': 'Post no encontrado'}), 404
        return jsonify({'success': True, 'post': post})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: Inicializar estructura de carpetas de un post
@app.route('/api/posts/<codigo>/init-folders', methods=['POST'])
def init_post_folders(codigo):
    """
    Inicializar estructura de carpetas en Drive
    ---
    tags:
      - Posts
    parameters:
      - name: codigo
        in: path
        type: string
        required: true
        description: Código del post
        example: "20251024-1"
    responses:
      200:
        description: Carpetas inicializadas exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            folders_created:
              type: array
              items:
                type: string
              example: ["textos", "imagenes", "videos"]
      404:
        description: Post no encontrado
      500:
        description: Error del servidor
    """
    try:
        # Obtener post de MySQL
        post = db_service.get_post_by_codigo(codigo)
        
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

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Limpiar caché de posts manualmente"""
    try:
        clear_posts_cache()
        return jsonify({'success': True, 'message': 'Caché limpiado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/file-exists', methods=['GET'])
def check_file_exists():
    """Verificar si un archivo existe en Drive sin descargarlo (más confiable que proxy)"""
    try:
        codigo = request.args.get('codigo')
        folder = request.args.get('folder')
        filename = request.args.get('filename')
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener post
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'exists': False}), 200
        
        # Obtener subfolder
        folder_id = post['drive_folder_id']
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder)
        
        if not subfolder_id:
            return jsonify({'exists': False}), 200
        
        # Buscar archivo en Drive
        try:
            query = f"name='{filename}' and '{subfolder_id}' in parents and trashed=false"
            results = sheets_service.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            exists = len(files) > 0
            
            return jsonify({'exists': exists, 'filename': filename})
            
        except Exception as e:
            print(f"⚠️ Error buscando archivo: {e}")
            return jsonify({'exists': False}), 200
        
    except Exception as e:
        print(f"❌ Error verificando archivo: {str(e)}")
        return jsonify({'exists': False}), 200

@app.route('/api/drive/file', methods=['GET'])
def get_drive_file():
    try:
        codigo = request.args.get('codigo')
        folder = request.args.get('folder')
        filename = request.args.get('filename')
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post
        post = db_service.get_post_by_codigo(codigo)
        
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
        
        print(f"📸 Solicitando imagen: codigo={codigo}, folder={folder}, filename={filename}")
        
        if not all([codigo, folder, filename]):
            return jsonify({'error': 'Faltan parámetros'}), 400
        
        # Obtener folder_id del post (usando cache)
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            print(f"❌ Post no encontrado: {codigo}")
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener subfolder
        folder_id = post['drive_folder_id']
        print(f"📁 Folder ID del post: {folder_id}")
        subfolder_id = sheets_service.get_subfolder_id(folder_id, folder)
        
        if not subfolder_id:
            print(f"❌ Carpeta {folder} no encontrada en {folder_id}")
            return jsonify({'error': f'Carpeta {folder} no encontrada'}), 404
        
        print(f"📁 Subfolder ID ({folder}): {subfolder_id}")
        
        # Leer imagen con reintentos para errores de SSL
        max_retries = 5
        image_bytes = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Reinicializar conexión en cada intento para evitar SSL stale
                if attempt > 0:
                    sheets_service.ensure_authenticated()
                    time.sleep(0.3 * (attempt + 1))  # Espera incremental
                
                image_bytes = sheets_service.get_image_from_drive(subfolder_id, filename)
                if image_bytes:
                    print(f"✅ Imagen cargada exitosamente en intento {attempt + 1}")
                    break
            except Exception as retry_error:
                last_error = retry_error
                error_msg = str(retry_error)
                if 'SSL' in error_msg or 'ssl' in error_msg.lower():
                    print(f"⚠️ Error SSL en intento {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                else:
                    print(f"❌ Error no-SSL: {error_msg}")
                    if attempt < max_retries - 1:
                        continue
                    raise retry_error
        
        if not image_bytes:
            error_detail = str(last_error) if last_error else 'Imagen no encontrada'
            print(f"❌ No se pudo cargar imagen después de {max_retries} intentos: {error_detail}")
            return jsonify({'error': f'Error cargando imagen: {error_detail}'}), 500
        
        # Servir imagen
        return send_file(
            BytesIO(image_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error sirviendo imagen {filename}: {error_msg}")
        
        # Si es error SSL, limpiar caché y reinicializar servicios
        if 'SSL' in error_msg or 'ssl' in error_msg.lower():
            print("🔄 Error SSL detectado, limpiando caché y reinicializando...")
            clear_posts_cache()
            # Reinicializar servicios de Google
            try:
                sheets_service.ensure_authenticated()
                print("✅ Servicios reinicializados")
            except Exception as reinit_error:
                print(f"⚠️ Error reinicializando: {reinit_error}")
        
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

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
        post = db_service.get_post_by_codigo(codigo)
        
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
    
    posts = db_service.get_all_posts()
    
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
            post = db_service.get_post_by_codigo(codigo)
            if not post:
                return jsonify({'error': f'Post {codigo} no encontrado'}), 400
            
            if not post.get('drive_folder_id'):
                return jsonify({'error': f'El post {codigo} no tiene Drive Folder ID configurado'}), 400
            
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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
            post = db_service.get_post_by_codigo(codigo)
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

# Nota: El endpoint /api/generate-image está implementado más abajo con Fal.ai

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
        post = db_service.get_post_by_codigo(codigo)
        
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

# API: Generar video base (legacy - mantener para compatibilidad)
@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    return jsonify({'success': True, 'message': 'Video generado'})

# ============================================
# ENDPOINTS PARA GENERACIÓN DE VIDEO CON SEEDANCE 1.0
# ============================================

@app.route('/api/generate-video-text', methods=['POST'])
def generate_video_text():
    """
    Generar video desde texto usando SeeDance 1.0 Pro (Text-to-Video)
    
    NOTA: Este endpoint NO soporta imágenes de referencia. Solo genera desde texto.
    ---
    tags:
      - Videos
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - prompt
          properties:
            prompt:
              type: string
              description: Descripción del video a generar
              example: "Ciclista profesional en bicicleta de carretera, paisaje montañoso"
            resolution:
              type: string
              description: Resolución del video
              enum: ["720p", "1024p"]
              default: "720p"
    responses:
      200:
        description: Video generado exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            video_url:
              type: string
              description: URL temporal del video generado
            duration:
              type: number
              description: Tiempo de generación en segundos
            resolution:
              type: string
              example: "1280x720"
      400:
        description: Parámetros inválidos
      500:
        description: Error en la generación
    """
    try:
        data = request.json
        prompt = data.get('prompt')
        resolution = data.get('resolution', '720p')
        
        if not prompt:
            return jsonify({'error': 'Prompt requerido'}), 400
        
        print(f"\n🎬 === GENERANDO TEXT-TO-VIDEO ===")
        print(f"📝 Prompt: {prompt[:100]}...")
        print(f"📐 Resolución: {resolution}")
        
        # Configurar dimensiones según resolución
        if resolution == '1024p':
            width, height = 1024, 1024
        else:  # 720p por defecto
            width, height = 1280, 720
        
        # Llamar a Fal.ai SeeDance Text-to-Video
        import fal_client
        
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedance/v1/pro/text-to-video",
            arguments={
                "prompt": prompt,
                "video_size": {
                    "width": width,
                    "height": height
                }
            },
            with_logs=True,
            on_queue_update=lambda update: print(f"  ⏳ Status: {getattr(update, 'status', 'processing')}")
        )
        
        print(f"✅ Video generado!")
        video_url = result['video']['url']
        print(f"🎥 URL: {video_url}")
        
        # Descargar y guardar video localmente
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'falai', 'test_results')
        os.makedirs(results_dir, exist_ok=True)
        
        print(f"📥 Descargando video...")
        response = requests.get(video_url)
        video_bytes = response.content
        
        filename = f"test_{timestamp}_video.mp4"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(video_bytes)
        
        print(f"💾 Video guardado: {filename} ({len(video_bytes) / 1024 / 1024:.1f} MB)")
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'local_path': filepath,
            'filename': filename,
            'duration': result.get('timings', {}).get('inference', 0),
            'resolution': f"{width}x{height}"
        })
        
    except Exception as e:
        print(f"❌ Error generando text-to-video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-video-image', methods=['POST'])
def generate_video_image():
    """
    Generar video desde imagen usando SeeDance 1.0 Pro (Image-to-Video)
    
    NOTA: Este endpoint NO soporta imágenes de referencia adicionales. 
    Solo anima la imagen base proporcionada.
    ---
    tags:
      - Videos
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - prompt
            - image_url
          properties:
            prompt:
              type: string
              description: Descripción del movimiento/animación
              example: "Ciclista pedaleando en carretera de montaña"
            image_url:
              type: string
              description: URL de la imagen base a animar
              example: "https://fal.media/files/..."
            resolution:
              type: string
              description: Resolución del video
              enum: ["720p", "1024p"]
              default: "720p"
    responses:
      200:
        description: Video generado exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            video_url:
              type: string
              description: URL temporal del video generado
            duration:
              type: number
              description: Tiempo de generación en segundos
            resolution:
              type: string
              example: "1280x720"
      400:
        description: Parámetros inválidos
      500:
        description: Error en la generación
    """
    try:
        data = request.json
        prompt = data.get('prompt')
        image_url = data.get('image_url')
        resolution = data.get('resolution', '720p')
        
        if not prompt or not image_url:
            return jsonify({'error': 'Prompt e image_url requeridos'}), 400
        
        print(f"\n🎬 === GENERANDO IMAGE-TO-VIDEO ===")
        print(f"📝 Prompt: {prompt[:100]}...")
        print(f"🖼️  Imagen: {image_url[:80]}...")
        print(f"📐 Resolución: {resolution}")
        
        # Configurar dimensiones según resolución
        if resolution == '1024p':
            width, height = 1024, 1024
        else:  # 720p por defecto
            width, height = 1280, 720
        
        # Llamar a Fal.ai SeeDance Image-to-Video
        import fal_client
        
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            arguments={
                "prompt": prompt,
                "image_url": image_url,
                "video_size": {
                    "width": width,
                    "height": height
                }
            },
            with_logs=True,
            on_queue_update=lambda update: print(f"  ⏳ Status: {getattr(update, 'status', 'processing')}")
        )
        
        print(f"✅ Video generado!")
        video_url = result['video']['url']
        print(f"🎥 URL: {video_url}")
        
        # Descargar y guardar video localmente
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'falai', 'test_results')
        os.makedirs(results_dir, exist_ok=True)
        
        print(f"📥 Descargando video...")
        response = requests.get(video_url)
        video_bytes = response.content
        
        filename = f"test_{timestamp}_video.mp4"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(video_bytes)
        
        print(f"💾 Video guardado: {filename} ({len(video_bytes) / 1024 / 1024:.1f} MB)")
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'local_path': filepath,
            'filename': filename,
            'duration': result.get('timings', {}).get('inference', 0),
            'resolution': f"{width}x{height}"
        })
        
    except Exception as e:
        print(f"❌ Error generando image-to-video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API: Formatear videos
@app.route('/api/format-videos', methods=['POST'])
def format_videos():
    return jsonify({'success': True, 'message': 'Videos formateados'})

# API: Actualizar campo de post
@app.route('/api/posts/<codigo>/update', methods=['POST'])
def update_post(codigo):
    try:
        data = request.json
        
        # Actualizar en MySQL
        updated_post = db_service.update_post(codigo, data)
        
        return jsonify({'success': True, 'message': 'Post actualizado', 'post': updated_post})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # 1. Obtener post de MySQL
        post = db_service.get_post_by_codigo(codigo)
        
        if not post:
            return jsonify({'error': f'Post {codigo} no encontrado'}), 404
        
        # 2. Eliminar carpeta de Drive si existe
        if post.get('drive_folder_id'):
            try:
                sheets_service.drive_service.files().delete(fileId=post['drive_folder_id']).execute()
                print(f"  ✅ Carpeta de Drive eliminada: {post['drive_folder_id']}")
            except Exception as e:
                print(f"  ⚠️ Error eliminando carpeta de Drive: {e}")
        
        # 3. Eliminar de MySQL
        db_service.delete_post(codigo)
        print(f"  ✅ Post {codigo} eliminado de MySQL")
        
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
        post = db_service.get_post_by_codigo(codigo)
        
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
    """
    Chat con Claude usando herramientas MCP
    ---
    tags:
      - Content
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              description: Mensaje del usuario
              example: "Ayúdame a crear un nuevo post sobre nutrición en triatlón"
            history:
              type: array
              description: Historial de conversación
              items:
                type: object
                properties:
                  role:
                    type: string
                    enum: ["user", "assistant"]
                  content:
                    type: string
    responses:
      200:
        description: Respuesta de Claude
        schema:
          type: object
          properties:
            success:
              type: boolean
            response:
              type: string
              description: Respuesta de Claude
            tool_results:
              type: array
              description: Resultados de herramientas ejecutadas
              items:
                type: object
            history:
              type: array
              description: Historial actualizado
      400:
        description: Mensaje requerido
      500:
        description: Error en el chat
    """
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
            model=os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620'),
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
        posts = db_service.get_all_posts()
        posts_hoy = [p for p in posts if p.get('codigo', '').startswith(fecha_str)]
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
        posts = db_service.get_all_posts()
        
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
        post = db_service.get_post_by_codigo(codigo)
        
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
        post = db_service.get_post_by_codigo(codigo)
        
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
        post = db_service.get_post_by_codigo(codigo)
        
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

# API: Mejorar prompt con selecciones visuales e imágenes de referencia
@app.route('/api/improve-prompt-visual', methods=['POST'])
def improve_prompt_visual():
    """
    Mejorar prompt con selecciones visuales (Prompt Builder)
    
    ✅ SOPORTA hasta 2 imágenes de referencia que se guardan en Drive.
    ---
    tags:
      - Images
    consumes:
      - multipart/form-data
    parameters:
      - name: codigo
        in: formData
        type: string
        required: true
        description: Código del post
        example: "20251024-1"
      - name: prompt_original
        in: formData
        type: string
        required: true
        description: Prompt original del usuario
        example: "Ciclista profesional en bicicleta de carretera"
      - name: selections
        in: formData
        type: string
        required: false
        description: JSON con selecciones visuales (estilo, composición, etc.)
        example: '{"style": "realistic", "composition": "centered"}'
      - name: reference_images
        in: formData
        type: file
        required: false
        description: Imágenes de referencia (hasta 2)
    responses:
      200:
        description: Prompt mejorado exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            improved_prompt:
              type: string
              description: Prompt mejorado con detalles visuales
            metadata:
              type: object
              description: Metadata de referencias guardadas
      400:
        description: Parámetros requeridos faltantes
      404:
        description: Post no encontrado
      500:
        description: Error en el procesamiento
    """
    try:
        # Obtener datos del FormData
        codigo = request.form.get('codigo')
        prompt_original = request.form.get('prompt_original')
        selections_json = request.form.get('selections', '{}')
        selections = json.loads(selections_json)
        
        if not codigo or not prompt_original:
            return jsonify({'error': 'Código y prompt original requeridos'}), 400
        
        print(f"🎨 Mejorando prompt visual para post {codigo}")
        print(f"📝 Prompt original: {prompt_original[:100]}...")
        print(f"🎯 Selecciones: {selections}")
        
        # Obtener post y carpetas
        post = db_service.get_post_by_codigo(codigo)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado o sin carpeta en Drive'}), 404
        
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes', create_if_missing=True)
        
        if not textos_folder_id or not imagenes_folder_id:
            return jsonify({'error': 'No se pudieron acceder a las carpetas'}), 500
        
        # Procesar imágenes de referencia si existen
        reference_info = []
        for ref_num in [1, 2]:
            ref_key = f'ref{ref_num}'
            if ref_key in request.files:
                ref_file = request.files[ref_key]
                ref_influence = request.form.get(f'{ref_key}_influence', '0.6')
                
                # Guardar imagen en Drive
                ref_filename = f"{codigo}_referencia_{ref_num}.png"
                ref_bytes = ref_file.read()
                file_id = sheets_service.save_image_to_drive(imagenes_folder_id, ref_filename, ref_bytes)
                
                influence_labels = {
                    '0.3': 'Inspiración (mood/colores)',
                    '0.6': 'Guía (estructura similar)',
                    '0.9': 'Exacta (replicar elemento)'
                }
                
                # Generar URL usando proxy local (más confiable que Drive directo)
                drive_url = f"/api/drive/image?codigo={codigo}&folder=imagenes&filename={ref_filename}" if file_id else None
                
                reference_info.append({
                    'filename': ref_filename,
                    'file_id': file_id,
                    'drive_url': drive_url,
                    'influence': float(ref_influence),
                    'label': influence_labels.get(ref_influence, 'Guía')
                })
                
                print(f"  📸 Referencia {ref_num}: {ref_filename} (ID: {file_id}, influencia: {ref_influence})")
        
        # Guardar metadata de referencias
        if reference_info:
            from datetime import datetime
            metadata = {
                'references': reference_info,
                'timestamp': datetime.now().isoformat(),
                'codigo': codigo
            }
            metadata_filename = f"{codigo}_referencias_metadata.json"
            sheets_service.save_file_to_drive(textos_folder_id, metadata_filename, json.dumps(metadata, indent=2))
            print(f"  ✅ Metadata guardada: {metadata_filename}")
        
        # Filtrar selecciones no nulas
        active_selections = {k: v for k, v in selections.items() if v is not None}
        
        # Construir prompt para Claude
        selecciones_texto = ""
        if active_selections:
            selecciones_texto = "\n".join([f"- {k.title()}: {v}" for k, v in active_selections.items()])
        
        referencias_texto = ""
        if reference_info:
            referencias_texto = f"\n\nIMÁGENES DE REFERENCIA SUBIDAS:\n"
            for i, ref in enumerate(reference_info, 1):
                referencias_texto += f"- Referencia {i}: {ref['label']}\n"
            referencias_texto += "\nNOTA: El usuario ha subido imágenes de referencia que se usarán en la generación. Menciona en el prompt que debe incorporar elementos de las referencias proporcionadas."
        
        claude_prompt = f"""Mejora este prompt de imagen para generación con IA, incorporando los siguientes elementos:

PROMPT ACTUAL:
{prompt_original}

ELEMENTOS VISUALES A INCORPORAR:
{selecciones_texto if selecciones_texto else "(No hay selecciones visuales)"}
{referencias_texto}

INSTRUCCIONES:
- Integra los elementos visuales de forma natural en el prompt
- Mantén el concepto y contenido original
- Si hay imágenes de referencia, menciona que debe usar "reference images" o "guided by provided images"
- Genera el prompt mejorado en inglés
- Máximo 400 caracteres
- Enfócate en equipamiento deportivo, paisajes y elementos abstractos (evita personas específicas)

Genera SOLO el prompt mejorado, sin explicaciones."""

        # Llamar a Claude
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": claude_prompt}]
        )
        
        nuevo_prompt = message.content[0].text.strip()
        print(f"✅ Nuevo prompt generado: {nuevo_prompt}")
        
        # Guardar nuevo prompt
        filename = f"{codigo}_prompt_imagen.txt"
        sheets_service.save_file_to_drive(textos_folder_id, filename, nuevo_prompt)
        print(f"✅ Prompt guardado en Drive: {filename}")
        
        # Actualizar checkbox
        sheets_service.update_post_field(codigo, 'image_prompt', 'TRUE')
        print(f"✅ Checkbox actualizado")
        
        # Limpiar caché para que index.html vea los cambios inmediatamente
        clear_posts_cache()
        
        return jsonify({
            'success': True,
            'message': 'Prompt mejorado y guardado correctamente',
            'nuevo_prompt': nuevo_prompt,
            'references_count': len(reference_info)
        })
        
    except Exception as e:
        print(f"❌ Error mejorando prompt visual: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINT COMPUESTO PARA IAs (MCP)
# ============================================

@app.route('/api/generate-complete-post', methods=['POST'])
def generate_complete_post():
    """
    🚀 ENDPOINT MAESTRO: Genera post completo de principio a fin
    
    Diseñado para Claude Desktop. Ejecuta todo el flujo automáticamente:
    1. Genera tema (si no se proporciona)
    2. Genera título y contenido con Claude
    3. Crea post en Sheets + Drive (reutiliza execute_create_post)
    4. Genera prompt + 4 imágenes (reutiliza generate_post_images_complete)
    
    ✅ SOPORTA referencias visuales si existen
    ---
    tags:
      - Composite
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            tema:
              type: string
              description: Tema del post (opcional, si no se da, se genera uno)
              example: "Nutrición en Ironman 70.3"
            categoria:
              type: string
              description: Categoría del post
              enum: [training, racing, training-science]
              default: "training"
    responses:
      200:
        description: Post completo generado exitosamente
      500:
        description: Error en la generación
    """
    try:
        tema = request.json.get('tema') if request.json else None
        categoria = request.json.get('categoria', 'training') if request.json else 'training'
        
        print(f"\n🚀 === GENERACIÓN COMPLETA DE POST ===")
        print(f"📝 Tema: {tema or 'Auto-generado'}")
        print(f"📂 Categoría: {categoria}")
        
        if not sheets_service.ensure_authenticated():
            return jsonify({'error': 'Error de autenticación con Google'}), 500
        
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # 1. Generar tema si no se proporciona
        if not tema:
            print(f"🎲 Generando tema automáticamente...")
            tema_generation = client.messages.create(
                model=os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620'),
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""Genera un tema interesante y relevante para un post de blog de triatlón.

Categoría: {categoria}

Requisitos:
- Tema específico y accionable
- Relevante para triatletas de nivel medio-avanzado
- Enfocado en mejorar rendimiento
- Una frase corta (máximo 10 palabras)

Ejemplos: "Técnicas de escalada en bicicleta para triatlón", "Periodización inversa en fase base"

Responde SOLO con el tema, sin explicaciones."""
                }]
            )
            tema = tema_generation.content[0].text.strip()
            print(f"✅ Tema generado: {tema}")
        
        # 2. Generar título y contenido
        print(f"📝 Generando contenido con Claude...")
        content_generation = client.messages.create(
            model=os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620'),
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""Crea un post completo para el blog de Lavelo Triathlon Training sobre: {tema}

Categoría: {categoria}

Estructura:
1. Título atractivo (máximo 80 caracteres)
2. Contenido completo (800-1200 palabras)

Estilo: Profesional pero motivador, basado en ciencia del deporte, consejos prácticos, tono cercano.

Formato de respuesta:
TÍTULO: [tu título aquí]

CONTENIDO:
[tu contenido aquí]

NO incluyas hashtags, emojis ni llamadas a acción de redes sociales."""
            }]
        )
        
        response_text = content_generation.content[0].text.strip()
        
        # Parsear título y contenido
        if "TÍTULO:" in response_text and "CONTENIDO:" in response_text:
            parts = response_text.split("CONTENIDO:")
            titulo = parts[0].replace("TÍTULO:", "").strip()
            contenido = parts[1].strip()
        else:
            lines = response_text.split("\n")
            titulo = lines[0].strip()
            contenido = "\n".join(lines[1:]).strip()
        
        print(f"✅ Título: {titulo[:50]}...")
        print(f"✅ Contenido: {len(contenido)} caracteres")
        
        # 3. Crear post (reutiliza función existente)
        print(f"💾 Creando post en Sheets + Drive...")
        post_result = execute_create_post({
            'titulo': titulo,
            'contenido': contenido,
            'categoria': categoria,
            'idea': tema
        })
        
        if not post_result.get('success'):
            return jsonify(post_result), 500
        
        codigo = post_result['codigo']
        print(f"✅ Post creado: {codigo}")
        
        # 4. Generar prompt + imágenes (llamar internamente)
        print(f"🎨 Generando prompt e imágenes...")
        
        # Hacer request interno al endpoint
        import requests as internal_requests
        images_response = internal_requests.post(
            'http://localhost:5001/api/generate-post-images-complete',
            json={'codigo': codigo},
            timeout=120
        )
        
        images_data = images_response.json()
        
        if not images_data.get('success'):
            return jsonify({
                'success': False,
                'codigo': codigo,
                'message': f'Post creado pero error en imágenes: {images_data.get("error")}'
            }), 500
        
        print(f"✅ GENERACIÓN COMPLETA EXITOSA")
        
        return jsonify({
            'success': True,
            'codigo': codigo,
            'titulo': titulo,
            'contenido_preview': contenido[:200] + "...",
            'prompt': images_data.get('prompt'),
            'images_count': len(images_data.get('images', [])),
            'message': f'✅ Post completo generado: {codigo}\n\n📝 {titulo}\n🖼️  {len(images_data.get("images", []))} imágenes\n📁 Todo guardado en Drive'
        })
        
    except Exception as e:
        print(f"❌ Error en generación completa: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-post-images-complete', methods=['POST'])
def generate_post_images_complete():
    """
    Endpoint compuesto: Genera prompt + 4 imágenes automáticamente
    
    Diseñado para IAs (Claude Desktop). Ejecuta todo el flujo en una llamada:
    1. Lee base.txt del post
    2. Genera prompt optimizado con Claude
    3. Genera 4 variaciones de imagen con Fal.ai
    4. Guarda todo en Drive
    
    ✅ SOPORTA referencias visuales si existen en Drive
    ---
    tags:
      - Images
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - codigo
          properties:
            codigo:
              type: string
              description: Código del post
              example: "20251024-1"
    responses:
      200:
        description: Prompt e imágenes generadas exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            prompt:
              type: string
              description: Prompt generado
            images:
              type: array
              items:
                type: object
                properties:
                  filename:
                    type: string
                  file_id:
                    type: string
                  url:
                    type: string
            message:
              type: string
              example: "✅ Prompt e imágenes generadas correctamente"
      400:
        description: Código requerido
      404:
        description: Post no encontrado
      500:
        description: Error en la generación
    """
    try:
        codigo = request.json.get('codigo')
        
        if not codigo:
            return jsonify({'error': 'Código de post requerido'}), 400
        
        print(f"\n🎨 === GENERACIÓN COMPLETA PARA {codigo} ===")
        
        # 0. Asegurar autenticación
        if not sheets_service.ensure_authenticated():
            return jsonify({'error': 'Error de autenticación con Google'}), 500
        
        # 1. Obtener post y carpetas
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado o sin carpeta en Drive'}), 404
        
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos', create_if_missing=True)
        imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes', create_if_missing=True)
        
        if not textos_folder_id or not imagenes_folder_id:
            return jsonify({'error': 'No se pudieron crear las carpetas'}), 500
        
        # 2. Leer base.txt
        base_filename = f"{codigo}_base.txt"
        base_text = sheets_service.get_file_from_drive(textos_folder_id, base_filename)
        
        if not base_text:
            return jsonify({'error': 'base.txt no encontrado. Crea el post primero.'}), 404
        
        print(f"📝 Base text: {base_text[:100]}...")
        
        # 3. Generar prompt con Claude
        print(f"🤖 Generando prompt con Claude...")
        
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        prompt_generation = client.messages.create(
            model=os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620'),
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Genera un prompt optimizado para SeaDream 4.0 (generador de imágenes) basado en este contenido:

{base_text}

Requisitos:
- Máximo 500 caracteres
- Describe la escena visual principal
- Incluye estilo fotográfico (photorealistic, cinematic, etc.)
- Menciona iluminación y composición
- Enfocado en triatlón/ciclismo/deporte

Responde SOLO con el prompt, sin explicaciones."""
            }]
        )
        
        prompt = prompt_generation.content[0].text.strip()
        print(f"✅ Prompt generado: {prompt[:100]}...")
        
        # 4. Guardar prompt en Drive
        prompt_filename = f"{codigo}_prompt_imagen.txt"
        sheets_service.save_text_to_drive(textos_folder_id, prompt_filename, prompt)
        print(f"💾 Prompt guardado en Drive")
        
        # 5. Actualizar checkbox en Sheet
        sheets_service.update_post_field(codigo, 'prompt_imagen', True)
        
        # 6. Leer referencias si existen
        metadata_filename = f"{codigo}_referencias_metadata.json"
        metadata_text = sheets_service.get_file_from_drive(textos_folder_id, metadata_filename)
        
        reference_images = []
        if metadata_text:
            try:
                metadata = json.loads(metadata_text)
                for ref in metadata.get('references', []):
                    if ref.get('drive_file_id'):
                        ref_content = sheets_service.get_file_content_by_id(ref['drive_file_id'])
                        if ref_content:
                            reference_images.append({
                                "image_url": f"data:image/png;base64,{ref_content}",
                                "weight": ref.get('weight', 0.8)
                            })
                print(f"🖼️  Cargadas {len(reference_images)} referencias desde Drive")
            except:
                pass
        
        # 7. Generar 4 imágenes con Fal.ai
        print(f"🎨 Generando 4 imágenes con Fal.ai SeaDream 4.0...")
        
        fal_key = os.getenv('FAL_KEY')
        if not fal_key:
            return jsonify({'error': 'FAL_KEY no configurada'}), 500
        
        os.environ['FAL_KEY'] = fal_key
        
        arguments = {
            "prompt": prompt,
            "image_size": "square_hd",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 4
        }
        
        if reference_images:
            arguments["reference_images"] = reference_images
            print(f"🖼️  Usando {len(reference_images)} referencias")
        
        import fal_client
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedream/v4/edit" if reference_images else "fal-ai/bytedance/seedream/v4",
            arguments=arguments,
            with_logs=True,
            on_queue_update=lambda update: print(f"  ⏳ Status: {getattr(update, 'status', 'processing')}")
        )
        
        # 8. Guardar imágenes en Drive
        images_saved = []
        for i, img in enumerate(result.get('images', []), 1):
            img_url = img.get('url')
            if img_url:
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    filename = f"{codigo}_imagen_base_{i}.png" if i > 1 else f"{codigo}_imagen_base.png"
                    file_id = sheets_service.save_image_to_drive(
                        imagenes_folder_id,
                        filename,
                        img_response.content
                    )
                    images_saved.append({
                        'filename': filename,
                        'file_id': file_id,
                        'url': img_url
                    })
                    print(f"💾 Guardada: {filename}")
        
        # 9. Actualizar checkbox en Sheet
        sheets_service.update_post_field(codigo, 'imagen_base', True)
        
        # 10. Actualizar estado
        sheets_service.update_post_state(codigo, 'IMAGE_BASE_AWAITING')
        
        print(f"✅ Generación completa exitosa")
        
        return jsonify({
            'success': True,
            'message': f'✅ Prompt e imágenes generadas correctamente',
            'prompt': prompt,
            'images': images_saved,
            'references_used': len(reference_images)
        })
        
    except Exception as e:
        print(f"❌ Error en generación completa: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """
    Generar imagen base usando Fal.ai SeaDream 4.0
    
    ✅ SOPORTA hasta 2 imágenes de referencia con pesos configurables.
    Las referencias se leen automáticamente desde Drive si existen.
    ---
    tags:
      - Images
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - codigo
          properties:
            codigo:
              type: string
              description: Código del post
              example: "20251024-1"
            num_images:
              type: integer
              description: Número de variaciones a generar
              default: 4
              minimum: 1
              maximum: 4
    responses:
      200:
        description: Imágenes generadas exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
              example: "4 imágenes generadas correctamente"
            images:
              type: array
              items:
                type: object
                properties:
                  filename:
                    type: string
                    example: "20251024-1_imagen_base.png"
                  file_id:
                    type: string
                    example: "1xyz789abc"
                  url:
                    type: string
                    example: "https://fal.media/files/..."
            references_used:
              type: integer
              description: Número de imágenes de referencia utilizadas
      400:
        description: Parámetros inválidos
      404:
        description: Post o prompt no encontrado
      500:
        description: Error en la generación
    """
    try:
        codigo = request.json.get('codigo')
        
        if not codigo:
            return jsonify({'error': 'Código de post requerido'}), 400
        
        print(f"\n🎨 === GENERANDO IMAGEN BASE PARA {codigo} ===")
        
        # 0. Asegurar que los servicios estén autenticados
        if not sheets_service.ensure_authenticated():
            return jsonify({'error': 'Error de autenticación con Google'}), 500
        
        # 1. Obtener post y folders
        posts = get_cached_posts()
        post = next((p for p in posts if p['codigo'] == codigo), None)
        
        if not post or not post.get('drive_folder_id'):
            return jsonify({'error': 'Post no encontrado'}), 404
        
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
        imagenes_folder_id = sheets_service.get_subfolder_id(folder_id, 'imagenes')
        
        # 2. Leer prompt de Fase 3
        prompt_filename = f"{codigo}_prompt_imagen.txt"
        prompt = sheets_service.get_file_from_drive(textos_folder_id, prompt_filename)
        
        if not prompt:
            return jsonify({'error': 'Prompt no encontrado. Completa Fase 3 primero.'}), 404
        
        print(f"📝 Prompt: {prompt[:100]}...")
        
        # 3. Leer metadata de referencias
        metadata_filename = f"{codigo}_referencias_metadata.json"
        metadata_text = sheets_service.get_file_from_drive(textos_folder_id, metadata_filename)
        
        reference_images = []
        if metadata_text:
            metadata = json.loads(metadata_text)
            referencias = metadata.get('references', [])
            
            print(f"📸 Referencias encontradas: {len(referencias)}")
            
            # 4. Descargar imágenes de referencia desde Drive y convertir a base64
            for ref in referencias:
                if ref.get('file_id'):
                    try:
                        # Leer imagen desde Drive
                        image_bytes = sheets_service.get_image_from_drive(imagenes_folder_id, ref['filename'])
                        
                        if image_bytes:
                            # Convertir a base64 data URL
                            base64_image = base64.b64encode(image_bytes).decode('utf-8')
                            data_url = f"data:image/png;base64,{base64_image}"
                            
                            reference_images.append({
                                'image_url': data_url,
                                'weight': ref.get('influence', 0.3)
                            })
                            print(f"  ✅ Referencia cargada: {ref['filename']} (peso: {ref.get('influence', 0.3)})")
                    except Exception as e:
                        print(f"  ⚠️ Error cargando referencia {ref['filename']}: {e}")
        
        # 5. Configurar Fal.ai
        fal_key = os.getenv('FAL_KEY')
        if not fal_key:
            return jsonify({'error': 'FAL_KEY no configurada en .env'}), 500
        
        os.environ['FAL_KEY'] = fal_key
        
        # 6. Preparar argumentos para SeaDream 4.0
        arguments = {
            "prompt": prompt,
            "image_size": "square_hd",  # 1024x1024
            "num_inference_steps": 28,
            "num_images": 4,  # Generar 4 variaciones
            "enable_safety_checker": False
        }
        
        # Agregar referencias si existen
        if reference_images:
            arguments["reference_images"] = reference_images
            print(f"🖼️  Usando {len(reference_images)} imágenes de referencia")
        
        print(f"🚀 Llamando a Fal.ai SeaDream 4.0...")
        print(f"   Parámetros: {json.dumps({k: v for k, v in arguments.items() if k != 'reference_images'}, indent=2)}")
        
        # 7. Llamar a Fal.ai
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedream/v4/text-to-image",
            arguments=arguments
        )
        
        print(f"✅ Generación completada!")
        
        # 8. Procesar resultados
        if not result or 'images' not in result or len(result['images']) == 0:
            return jsonify({'error': 'No se generaron imágenes'}), 500
        
        generated_images = []
        
        for idx, image_data in enumerate(result['images'], 1):
            image_url = image_data.get('url')
            
            if image_url:
                # Descargar imagen
                response = requests.get(image_url)
                image_bytes = response.content
                
                # Guardar en Drive
                filename = f"{codigo}_imagen_base_{idx}.png" if idx > 1 else f"{codigo}_imagen_base.png"
                file_id = sheets_service.save_image_to_drive(imagenes_folder_id, filename, image_bytes)
                
                generated_images.append({
                    'filename': filename,
                    'file_id': file_id,
                    'url': image_url,
                    'index': idx
                })
                
                print(f"  💾 Guardada: {filename} (ID: {file_id})")
        
        # 9. Actualizar checkbox en Sheet (solo si se generó al menos una)
        if generated_images:
            sheets_service.update_post_field(codigo, 'imagen_base', 'TRUE')
            print(f"✅ Checkbox imagen_base actualizado")
            
            # Limpiar caché para reflejar cambios
            clear_posts_cache()
        
        return jsonify({
            'success': True,
            'message': f'{len(generated_images)} imágenes generadas correctamente',
            'images': generated_images,
            'references_used': len(reference_images)
        })
        
    except Exception as e:
        print(f"❌ Error generando imagen: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINT PARA GENERAR INSTRUCCIONES DESDE POST
# ============================================
@app.route('/api/generate-instructions-from-post', methods=['POST'])
def generate_instructions_from_post():
    """
    Generar instrucciones de imagen desde contenido del post
    ---
    tags:
      - Content
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - codigo
          properties:
            codigo:
              type: string
              description: Código del post
              example: "20251024-1"
    responses:
      200:
        description: Instrucciones generadas exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            instructions:
              type: string
              description: Instrucciones generadas para la imagen
              example: "Ciclista profesional ajustando posición en bicicleta..."
      400:
        description: Código requerido
      404:
        description: Post no encontrado
      500:
        description: Error en la generación
    """
    try:
        data = request.json
        codigo = data.get('codigo')
        
        if not codigo:
            return jsonify({'error': 'Código de post requerido'}), 400
        
        print(f"\n📋 === GENERANDO INSTRUCCIONES DESDE POST ===")
        print(f"📝 Código: {codigo}")
        
        # Obtener post de MySQL
        post = db_service.get_post_by_codigo(codigo)
        
        if not post:
            return jsonify({'error': f'Post {codigo} no encontrado'}), 404
        
        if not post.get('drive_folder_id'):
            return jsonify({'error': 'Post sin carpeta en Drive'}), 404
        
        # Leer base.txt
        folder_id = post['drive_folder_id']
        textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
        
        if not textos_folder_id:
            return jsonify({'error': 'Carpeta textos no encontrada'}), 404
        
        filename = f"{codigo}_base.txt"
        base_text = sheets_service.get_file_from_drive(textos_folder_id, filename)
        
        if not base_text:
            return jsonify({'error': f'Archivo {filename} no encontrado'}), 404
        
        print(f"📄 Base text: {base_text[:100]}...")
        
        # Generar instrucciones con Claude
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        prompt = f"""Basándote en este contenido de post de blog sobre triatlón, genera instrucciones concisas para crear una imagen representativa.

CONTENIDO DEL POST:
{base_text[:1000]}

INSTRUCCIONES:
- Genera instrucciones en ESPAÑOL
- Describe la escena/objeto principal que debe aparecer
- Menciona estilo visual (fotorrealista, ilustración, etc.)
- Incluye detalles de composición y ambiente
- Máximo 300 caracteres
- Enfócate en elementos visuales concretos (equipamiento, paisajes, escenas)

Genera SOLO las instrucciones, sin explicaciones."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        instructions = response.content[0].text.strip()
        
        print(f"✅ Instrucciones generadas: {instructions}")
        
        return jsonify({
            'success': True,
            'instructions': instructions,
            'post_title': post.get('titulo', ''),
            'codigo': codigo
        })
        
    except Exception as e:
        print(f"❌ Error generando instrucciones: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINT PARA GENERAR PROMPT FINAL CON IA
# ============================================
@app.route('/api/generate-final-prompt', methods=['POST'])
def generate_final_prompt():
    """Genera el prompt final usando Claude basándose en system prompt y user prompt"""
    try:
        data = request.json
        system_prompt = data.get('system_prompt', '')
        user_prompt = data.get('user_prompt', '')
        reference_usage = data.get('reference_usage', [])
        advanced_settings = data.get('advanced_settings', {})
        
        if not user_prompt:
            return jsonify({'error': 'User prompt requerido'}), 400
        
        print(f"\n🤖 === GENERANDO PROMPT FINAL CON IA ===")
        print(f"📋 System Prompt: {len(system_prompt)} caracteres")
        print(f"💬 User Prompt: {user_prompt[:100]}...")
        print(f"🖼️  Referencias: {len(reference_usage)}")
        for ref in reference_usage:
            print(f"  - Ref {ref['ref_num']}: {ref['usage']}")
        if advanced_settings:
            print(f"⚙️  Ajustes avanzados: {list(advanced_settings.keys())}")
        
        # Configurar Claude
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_key:
            return jsonify({'error': 'ANTHROPIC_API_KEY no configurada'}), 500
        
        client = Anthropic(api_key=anthropic_key)
        
        # Construir contexto de referencias
        ref_context = ""
        if reference_usage:
            ref_context = "\n\nREFERENCE USAGE INFO:\n"
            for ref in reference_usage:
                ref_context += f"- Reference {ref['ref_num']}: Use {ref['usage']}\n"
        
        # Construir contexto de ajustes avanzados
        settings_context = ""
        if advanced_settings:
            settings_context = "\n\nADVANCED SETTINGS TO INCORPORATE:\n"
            if advanced_settings.get('perspective'):
                settings_context += f"- Perspectiva: {advanced_settings['perspective']}\n"
            if advanced_settings.get('composition'):
                settings_context += f"- Composición: {advanced_settings['composition']}\n"
            if advanced_settings.get('lighting'):
                settings_context += f"- Iluminación: {advanced_settings['lighting']}\n"
            if advanced_settings.get('style'):
                settings_context += f"- Estilo: {advanced_settings['style']}\n"
            if advanced_settings.get('realism'):
                settings_context += f"- Realismo: {advanced_settings['realism']}\n"
        
        # Construir mensaje para Claude
        messages = [
            {
                "role": "user",
                "content": f"{system_prompt}{ref_context}{settings_context}\n\nUSER REQUEST:\n{user_prompt}\n\nGenera el prompt final para SeeDream 4.0 (máx 500 caracteres) en ESPAÑOL, incorporando los ajustes avanzados de forma natural:"
            }
        ]
        
        print(f"🚀 Llamando a Claude Haiku...")
        
        # Llamar a Claude Haiku (rápido y económico)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=messages
        )
        
        final_prompt = response.content[0].text.strip()
        
        print(f"✅ Prompt generado: {final_prompt[:100]}...")
        print(f"📏 Longitud: {len(final_prompt)} caracteres")
        
        return jsonify({
            'success': True,
            'final_prompt': final_prompt,
            'length': len(final_prompt)
        })
        
    except Exception as e:
        print(f"❌ Error generando prompt: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINT DE PRUEBA FAL.AI
# ============================================
@app.route('/api/test-fal', methods=['POST'])
def test_fal_generate():
    """
    Generar imágenes de prueba con Fal.ai (Prompt Builder)
    
    ✅ SOPORTA hasta 2 imágenes de referencia en base64.
    ---
    tags:
      - Images
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - prompt
          properties:
            prompt:
              type: string
              description: Prompt para generar la imagen
              example: "Professional cyclist on road bike, mountain landscape"
            reference_images:
              type: array
              description: Array de imágenes en base64 (máx 2)
              items:
                type: string
                format: base64
            num_images:
              type: integer
              description: Número de variaciones a generar
              default: 4
              minimum: 1
              maximum: 4
    responses:
      200:
        description: Imágenes generadas exitosamente
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            images:
              type: array
              items:
                type: object
                properties:
                  filename:
                    type: string
                  url:
                    type: string
                  local_path:
                    type: string
            timestamp:
              type: string
      400:
        description: Prompt requerido
      500:
        description: Error en la generación
    """
    try:
        data = request.json
        prompt = data.get('prompt', '')
        reference_images_base64 = data.get('reference_images', [])
        
        if not prompt:
            return jsonify({'error': 'Prompt requerido'}), 400
        
        print(f"\n🎨 === TEST FAL.AI GENERATION ===")
        print(f"📝 Prompt: {prompt[:100]}...")
        print(f"📸 Referencias: {len(reference_images_base64)}")
        
        # Configurar Fal.ai
        fal_key = os.getenv('FAL_KEY')
        if not fal_key:
            return jsonify({'error': 'FAL_KEY no configurada en .env'}), 500
        
        os.environ['FAL_KEY'] = fal_key
        
        # Preparar argumentos
        # Si hay referencias, usar endpoint "edit" (image-to-image)
        # Si no hay referencias, usar endpoint "text-to-image"
        
        if reference_images_base64:
            # Endpoint EDIT (soporta referencias)
            endpoint = "fal-ai/bytedance/seedream/v4/edit"
            
            # Convertir referencias a formato de URLs
            image_urls = []
            for idx, img_data in enumerate(reference_images_base64):
                image_urls.append(img_data)
                print(f"  ✅ Referencia {idx + 1} agregada")
            
            arguments = {
                "prompt": prompt,
                "image_urls": image_urls,  # Array de URLs/base64
                "num_images": 4,
                "enable_safety_checker": False
            }
            
            print(f"🖼️  Usando {len(image_urls)} imágenes de referencia (endpoint: edit)")
        else:
            # Endpoint TEXT-TO-IMAGE (sin referencias)
            endpoint = "fal-ai/bytedance/seedream/v4/text-to-image"
            
            arguments = {
                "prompt": prompt,
                "image_size": "square_hd",
                "num_inference_steps": 28,
                "num_images": 4,
                "enable_safety_checker": False
            }
            
            print(f"🎨 Sin referencias (endpoint: text-to-image)")
        
        print(f"🚀 Llamando a Fal.ai SeaDream 4.0 ({endpoint})...")
        
        # Llamar a Fal.ai
        result = fal_client.subscribe(endpoint, arguments=arguments)
        
        print(f"✅ Generación completada!")
        
        # Procesar resultados
        generated_images = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear carpeta de resultados si no existe
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'falai', 'test_results')
        os.makedirs(results_dir, exist_ok=True)
        
        for idx, image_data in enumerate(result['images'], 1):
            image_url = image_data['url']
            
            # Descargar imagen
            response = requests.get(image_url)
            image_bytes = response.content
            
            # Guardar localmente
            filename = f"test_{timestamp}_{idx}.png"
            filepath = os.path.join(results_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            generated_images.append({
                'filename': filename,
                'url': image_url,
                'local_path': filepath
            })
            
            print(f"  💾 Guardada: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'{len(generated_images)} imágenes generadas',
            'images': generated_images,
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"❌ Error en test Fal.ai: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINTS PARA REDES SOCIALES (OAuth)
# ============================================

@app.route('/api/social/status', methods=['GET'])
def get_social_status():
    """
    Obtener estado de todas las conexiones sociales
    ---
    tags:
      - OAuth
    responses:
      200:
        description: Estado de conexiones
        schema:
          type: object
          properties:
            instagram:
              type: object
            linkedin:
              type: object
            twitter:
              type: object
            facebook:
              type: object
            tiktok:
              type: object
    """
    try:
        # Leer tokens desde SQLite (fuente de verdad actual)
        tokens = db_service.get_social_tokens() or {}

        # Normalizar salida esperada por el panel
        platforms = ['instagram', 'linkedin', 'twitter', 'facebook', 'tiktok']
        status = {}
        for platform in platforms:
            t = tokens.get(platform)
            if t:
                status[platform] = {
                    'connected': True,
                    'username': t.get('username', 'N/A'),
                    'expires_at': t.get('expires_at'),
                    'connected_at': t.get('connected_at'),
                    'last_used': t.get('last_used')
                }
                # Campos extra útiles para Instagram/Facebook
                if platform in ['instagram', 'facebook']:
                    status[platform]['page_id'] = t.get('page_id')
                    status[platform]['instagram_account_id'] = t.get('instagram_account_id')
            else:
                status[platform] = {'connected': False}

        # Si Instagram conectado, marcar Facebook como compartido si no tiene token propio
        if status.get('instagram', {}).get('connected') and not tokens.get('facebook'):
            fb = dict(status.get('facebook', {}))
            fb.update({'connected': True, 'shared_with_instagram': True})
            status['facebook'] = fb

        return jsonify(status)

    except Exception as e:
        print(f"❌ Error obteniendo estado social: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/connect/<platform>', methods=['GET'])
def connect_social_platform(platform):
    """
    Iniciar OAuth para conectar una plataforma
    ---
    tags:
      - OAuth
    parameters:
      - name: platform
        in: path
        type: string
        required: true
        description: Plataforma a conectar (instagram, linkedin, twitter, facebook, tiktok)
    responses:
      302:
        description: Redirect a OAuth
    """
    try:
        # Configuración OAuth por plataforma
        oauth_configs = {
            'instagram': {
                'client_id': os.getenv('INSTAGRAM_CLIENT_ID'),
                'redirect_uri': f"{request.host_url}api/social/callback/instagram",
                'scope': 'instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,pages_manage_posts',
                'auth_url': 'https://www.facebook.com/v21.0/dialog/oauth'
            },
            'linkedin': {
                'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
                'redirect_uri': f"{request.host_url}api/social/callback/linkedin",
                'scope': 'w_member_social,r_basicprofile',
                'auth_url': 'https://www.linkedin.com/oauth/v2/authorization'
            },
            'twitter': {
                'client_id': os.getenv('TWITTER_CLIENT_ID'),
                'redirect_uri': f"{request.host_url}api/social/callback/twitter",
                'scope': 'tweet.read,tweet.write,users.read',
                'auth_url': 'https://twitter.com/i/oauth2/authorize'
            },
            'facebook': {
                'client_id': os.getenv('FACEBOOK_CLIENT_ID'),
                'redirect_uri': f"{request.host_url}api/social/callback/facebook",
                'scope': 'pages_manage_posts,pages_read_engagement',
                'auth_url': 'https://www.facebook.com/v18.0/dialog/oauth'
            },
            'tiktok': {
                'client_id': os.getenv('TIKTOK_CLIENT_ID'),
                'redirect_uri': f"{request.host_url}api/social/callback/tiktok",
                'scope': 'video.upload,user.info.basic',
                'auth_url': 'https://www.tiktok.com/auth/authorize/'
            }
        }
        
        if platform not in oauth_configs:
            return jsonify({'error': 'Plataforma no soportada'}), 400
        
        config = oauth_configs[platform]
        
        # Verificar que exista client_id
        if not config['client_id']:
            return jsonify({
                'error': f'Client ID no configurado para {platform}',
                'message': f'Añade {platform.upper()}_CLIENT_ID al archivo .env'
            }), 500
        
        # Generar state para seguridad
        state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
        session[f'{platform}_oauth_state'] = state
        
        # Construir URL de autorización
        auth_params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'scope': config['scope'],
            'response_type': 'code',
            'state': state
        }
        
        auth_url = f"{config['auth_url']}?"
        auth_url += '&'.join([f"{k}={v}" for k, v in auth_params.items()])
        
        print(f"🔗 Redirigiendo a OAuth de {platform}")
        print(f"   URL: {auth_url}")
        
        return redirect(auth_url)
        
    except Exception as e:
        print(f"❌ Error iniciando OAuth para {platform}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/callback/<platform>', methods=['GET'])
def social_callback(platform):
    """
    Callback OAuth para recibir tokens
    ---
    tags:
      - OAuth
    parameters:
      - name: platform
        in: path
        type: string
        required: true
      - name: code
        in: query
        type: string
        required: true
      - name: state
        in: query
        type: string
        required: true
    responses:
      302:
        description: Redirect a panel con resultado
    """
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verificar state
        stored_state = session.get(f'{platform}_oauth_state')
        if not stored_state or stored_state != state:
            return jsonify({'error': 'Estado OAuth inválido'}), 400
        
        # Intercambiar code por access_token
        print(f"🔁 OAuth callback recibido para {platform}")
        current_user_id = 2
        token_data = exchange_code_for_token(platform, code, current_user_id)

        if not token_data:
            return redirect(f"/panel/social_connect.html?error=token_exchange_failed&platform={platform}")
        
        # Guardar token en SQLite (DB) con campos extra si existen
        # Importante: usar el user_id LOCAL (no el de Meta)
        payload = {
            # SIEMPRE guardar el USER LONG-LIVED TOKEN
            'access_token': token_data.get('user_long_lived_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'username': token_data.get('username'),
            'user_id': current_user_id
        }
        # Extras específicos de Instagram/Facebook
        if platform == 'instagram':
            if token_data.get('page_id'):
                payload['page_id'] = token_data.get('page_id')
            if token_data.get('instagram_account_id'):
                payload['instagram_account_id'] = token_data.get('instagram_account_id')
            if token_data.get('user_long_lived_token'):
                payload['user_long_lived_token'] = token_data.get('user_long_lived_token')

        print("📝 Payload a guardar en DB (recortado):",
              {
                  'platform': platform,
                  'username': payload.get('username'),
                  'user_id': payload.get('user_id'),
                  'page_id': payload.get('page_id'),
                  'instagram_account_id': payload.get('instagram_account_id'),
                  'access_token_preview': (payload.get('access_token') or '')[:15] + '...'
              })
        db_service.save_social_token(platform, payload)
        
        print(f"✅ Token de {platform} guardado correctamente en SQLite")
        try:
            tokens_after = db_service.get_social_tokens()
            ig = tokens_after.get('instagram') if tokens_after else None
            if ig:
                print("🔎 Verificación post-guardado (instagram):",
                      {
                          'page_id': ig.get('page_id'),
                          'instagram_account_id': ig.get('instagram_account_id'),
                          'token_preview': (ig.get('access_token') or '')[:15] + '...'
                      })
        except Exception as ver_e:
            print(f"⚠️ No se pudo verificar post-guardado: {ver_e}")
        
        return redirect(f"/panel/social_connect.html?success=true&platform={platform}")
        
    except Exception as e:
        print(f"❌ Error en callback de {platform}: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(f"/panel/social_connect.html?error={str(e)}&platform={platform}")

def exchange_code_for_token(platform, code, current_user_id):
    """Intercambia el code por un long-lived user token + todas las páginas"""

    try:
        if platform == 'instagram':
            client_id = os.getenv('INSTAGRAM_CLIENT_ID')
            client_secret = os.getenv('INSTAGRAM_CLIENT_SECRET')

            redirect_uri = request.host_url.rstrip('/') + "/api/social/callback/instagram"

            # === 1) CODE → SHORT TOKEN ===
            short_resp = requests.get(
                "https://graph.facebook.com/v21.0/oauth/access_token",
                params={
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "client_secret": client_secret,
                    "code": code
                }
            )
            if short_resp.status_code != 200:
                print("❌ Error short token:", short_resp.text)
                return None

            short_token = short_resp.json().get("access_token")

            # === 2) SHORT → LONG TOKEN ===
            long_resp = requests.get(
                "https://graph.facebook.com/v21.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "fb_exchange_token": short_token
                }
            )

            if long_resp.status_code != 200:
                print("❌ Error long token:", long_resp.text)
                return None

            long_json = long_resp.json()
            user_long_token = long_json["access_token"]

            # === 3) Obtener TODAS LAS PÁGINAS con IG ===
            pages_resp = requests.get(
                "https://graph.facebook.com/v21.0/me/accounts",
                params={
                    "access_token": user_long_token,
                    "fields": "id,name,access_token,instagram_business_account"
                }
            )
            print("📄 /me/accounts =>", pages_resp.text)

            if pages_resp.status_code != 200:
                print("❌ Error /me/accounts:", pages_resp.text)
                return None

            pages_json = pages_resp.json().get("data", [])

            pages_all = []
            pages_with_ig = []

            for p in pages_json:
                pid = p.get("id")
                pname = p.get("name")
                page_token = p.get("access_token")  # Puede ser None
                ig_acc = p.get("instagram_business_account", {})
                ig_id_local = ig_acc.get("id")

                # Guardar en BD
                db_service.upsert_social_page({
                    'user_id': current_user_id,
                    'platform': 'facebook_page',
                    'page_id': pid,
                    'page_name': pname,
                    'instagram_account_id': ig_id_local,
                    'page_access_token': page_token,
                    'expires_at': None
                })

                row = {
                    'id': pid,
                    'name': pname,
                    'access_token': page_token,
                    'instagram_id': ig_id_local
                }

                pages_all.append(row)
                if ig_id_local:
                    pages_with_ig.append(row)

            if not pages_all:
                print("⚠️ Usuario sin páginas")
                return None

            # === 4) Elegir página preferida ===
            if pages_with_ig:
                selected = pages_with_ig[0]   # priorizamos página con IG
            else:
                selected = pages_all[0]       # fallback estable

            # === 5) Información del usuario ===
            me_resp = requests.get(
                "https://graph.facebook.com/v21.0/me",
                params={"fields": "id,name", "access_token": user_long_token}
            )
            if me_resp.status_code == 200:
                me_json = me_resp.json()
                user_meta_id = me_json.get("id")
                username = me_json.get("name")
            else:
                user_meta_id = None
                username = "N/A"

            # === 6) Devolver datos ===
            return {
                "access_token": user_long_token,
                "refresh_token": None,
                "expires_in": long_json.get("expires_in", 5184000),
                "username": username,
                "user_id": user_meta_id,
                "pages": pages_all,
                "page_id": selected["id"],
                "instagram_account_id": selected["instagram_id"],
                "user_long_lived_token": user_long_token
            }

    except Exception as e:
        print("❌ ERROR TOKEN EXCHANGE:", e)
        import traceback
        traceback.print_exc()
        return None


def get_user_info(platform, access_token):
    """Obtener información del usuario"""
    try:
        user_endpoints = {
            'instagram': 'https://graph.instagram.com/me?fields=id,username',
            'linkedin': 'https://api.linkedin.com/v2/me',
            'twitter': 'https://api.twitter.com/2/users/me',
            'facebook': 'https://graph.facebook.com/me?fields=id,name',
            'tiktok': 'https://open-api.tiktok.com/user/info/'
        }
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(user_endpoints[platform], headers=headers)
        
        if response.status_code == 200:
            return response.json()
        
        return {}
        
    except Exception as e:
        print(f"❌ Error obteniendo info de usuario: {str(e)}")
        return {}

@app.route('/api/social/refresh/<platform>', methods=['POST'])
def refresh_social_token(platform):
    """
    Renovar token de una plataforma
    ---
    tags:
      - OAuth
    parameters:
      - name: platform
        in: path
        type: string
        required: true
    responses:
      200:
        description: Token renovado
    """
    try:
        # Obtener refresh token actual
        tokens = sheets_service.get_social_tokens()
        
        if platform not in tokens or not tokens[platform]:
            return jsonify({'error': 'Plataforma no conectada'}), 400
        
        refresh_token = tokens[platform].get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'No hay refresh token disponible'}), 400
        
        # Renovar token
        new_token_data = refresh_access_token(platform, refresh_token)
        
        if not new_token_data:
            return jsonify({'error': 'Error renovando token'}), 500
        
        # Actualizar en Sheets
        sheets_service.save_social_token(platform, new_token_data)
        
        return jsonify({
            'success': True,
            'message': f'Token de {platform} renovado'
        })
        
    except Exception as e:
        print(f"❌ Error renovando token: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def refresh_access_token(platform, refresh_token):
    """Renovar access token usando refresh token"""
    try:
        token_endpoints = {
            'instagram': 'https://graph.instagram.com/refresh_access_token',
            'linkedin': 'https://www.linkedin.com/oauth/v2/accessToken',
            'twitter': 'https://api.twitter.com/2/oauth2/token',
            'facebook': 'https://graph.facebook.com/v18.0/oauth/access_token',
            'tiktok': 'https://open-api.tiktok.com/oauth/refresh_token/'
        }
        
        # Preparar request según plataforma
        if platform == 'instagram':
            params = {
                'grant_type': 'ig_refresh_token',
                'access_token': refresh_token
            }
            response = requests.get(token_endpoints[platform], params=params)
        else:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': os.getenv(f'{platform.upper()}_CLIENT_ID'),
                'client_secret': os.getenv(f'{platform.upper()}_CLIENT_SECRET')
            }
            response = requests.post(token_endpoints[platform], data=data)
        
        if response.status_code != 200:
            print(f"❌ Error renovando token: {response.text}")
            return None
        
        token_response = response.json()
        
        return {
            'access_token': token_response['access_token'],
            'refresh_token': token_response.get('refresh_token', refresh_token),
            'expires_in': token_response.get('expires_in', 3600)
        }
        
    except Exception as e:
        print(f"❌ Error renovando token: {str(e)}")
        return None

@app.route('/api/social/disconnect/<platform>', methods=['POST'])
def disconnect_social_platform(platform):
    """
    Desconectar una plataforma
    ---
    tags:
      - OAuth
    parameters:
      - name: platform
        in: path
        type: string
        required: true
    responses:
      200:
        description: Plataforma desconectada
    """
    try:
        sheets_service.delete_social_token(platform)
        
        return jsonify({
            'success': True,
            'message': f'{platform} desconectado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error desconectando {platform}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/<codigo>/publish', methods=['POST'])
def publish_post(codigo):
    """
    Publicar post en múltiples redes sociales
    ---
    tags:
      - OAuth
    parameters:
      - name: codigo
        in: path
        type: string
        required: true
        description: Código del post (YYYYMMDD-ref)
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            platforms:
              type: array
              items:
                type: string
              description: Lista de plataformas donde publicar
              example: ["instagram", "linkedin", "twitter"]
    responses:
      200:
        description: Publicación completada
        schema:
          type: object
          properties:
            success:
              type: boolean
            results:
              type: object
            errors:
              type: object
    """
    try:
        data = request.json
        platforms = data.get('platforms', [])
        
        if not platforms:
            return jsonify({'error': 'No se especificaron plataformas'}), 400
        
        # Obtener datos del post
        post = sheets_service.get_post_by_codigo(codigo)
        if not post:
            return jsonify({'error': 'Post no encontrado'}), 404
        
        # Obtener tokens
        tokens = sheets_service.get_social_tokens()
        
        results = {}
        errors = {}
        
        for platform in platforms:
            try:
                if platform not in tokens or not tokens[platform]:
                    errors[platform] = 'No conectado'
                    continue
                
                # Publicar en la plataforma
                result = publish_to_platform(platform, codigo, post, tokens[platform])
                
                if result['success']:
                    results[platform] = result
                    # Actualizar checkbox en Sheet
                    sheets_service.update_post_field(codigo, f'published_{platform}', True)
                else:
                    errors[platform] = result.get('error', 'Error desconocido')
                    
            except Exception as e:
                errors[platform] = str(e)
                print(f"❌ Error publicando en {platform}: {str(e)}")
        
        # Si todas las plataformas se publicaron, cambiar estado a PUBLISHED
        if len(results) == len(platforms) and len(errors) == 0:
            sheets_service.update_post_field(codigo, 'estado', 'PUBLISHED')
            sheets_service.update_post_field(codigo, 'fecha_real_publicacion', datetime.now().isoformat())
        
        return jsonify({
            'success': len(errors) == 0,
            'results': results,
            'errors': errors,
            'message': f'Publicado en {len(results)}/{len(platforms)} plataformas'
        })
        
    except Exception as e:
        print(f"❌ Error publicando post: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def publish_to_platform(platform, codigo, post, token_data):
    """Publicar contenido en una plataforma específica vía Zapier"""
    try:
        # Obtener contenido del post desde Drive
        texto = sheets_service.get_file_content(codigo, f'{codigo}_{platform}.txt')
        imagen_url = sheets_service.get_file_url(codigo, f'{codigo}_{platform}_16x9.png')
        
        if not texto or not imagen_url:
            return {'success': False, 'error': 'Contenido o imagen no encontrados'}
        
        # Enviar a Zapier
        zapier_url = os.getenv('ZAPIER_WEBHOOK_URL')
        
        if not zapier_url:
            return {'success': False, 'error': 'ZAPIER_WEBHOOK_URL no configurada'}
        
        # Preparar payload para Zapier
        payload = {
            'platform': platform,
            'user_id': token_data.get('user_id', 'default'),
            'content': texto,
            'image_url': imagen_url,
            'post_codigo': codigo
        }
        
        print(f"📤 Enviando a Zapier: {platform}")
        print(f"   Content: {texto[:50]}...")
        print(f"   Image: {imagen_url}")
        
        # Enviar webhook a Zapier
        response = requests.post(zapier_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Zapier recibió el webhook para {platform}")
            return {
                'success': True,
                'platform': platform,
                'zapier_response': response.json()
            }
        else:
            print(f"❌ Error en Zapier: {response.status_code}")
            return {
                'success': False,
                'error': f'Zapier error: {response.status_code}'
            }
            
    except Exception as e:
        print(f"❌ Error publicando en {platform}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def publish_to_instagram(access_token, caption, image_url, user_id):
    """Publicar en Instagram"""
    try:
        # Instagram requiere 2 pasos: crear container, luego publicar
        
        # Paso 1: Crear media container
        create_url = f'https://graph.instagram.com/v18.0/{user_id}/media'
        create_data = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        
        response = requests.post(create_url, data=create_data)
        if response.status_code != 200:
            return {'success': False, 'error': response.text}
        
        container_id = response.json()['id']
        
        # Paso 2: Publicar
        publish_url = f'https://graph.instagram.com/v18.0/{user_id}/media_publish'
        publish_data = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        response = requests.post(publish_url, data=publish_data)
        if response.status_code != 200:
            return {'success': False, 'error': response.text}
        
        return {'success': True, 'post_id': response.json()['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def publish_to_linkedin(access_token, text, image_url):
    """Publicar en LinkedIn"""
    try:
        # LinkedIn API v2
        url = 'https://api.linkedin.com/v2/ugcPosts'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # TODO: Implementar subida de imagen y creación de post
        # Por ahora solo texto
        
        data = {
            'author': 'urn:li:person:PERSON_ID',  # Obtener del token
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': text
                    },
                    'shareMediaCategory': 'NONE'
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 201:
            return {'success': False, 'error': response.text}
        
        return {'success': True, 'post_id': response.json()['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def publish_to_twitter(access_token, text, image_url):
    """Publicar en Twitter"""
    try:
        # Twitter API v2
        url = 'https://api.twitter.com/2/tweets'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # TODO: Implementar subida de media
        # Por ahora solo texto
        
        data = {
            'text': text
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 201:
            return {'success': False, 'error': response.text}
        
        return {'success': True, 'tweet_id': response.json()['data']['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def publish_to_facebook(access_token, message, image_url, page_id):
    """Publicar en Facebook"""
    try:
        url = f'https://graph.facebook.com/v18.0/{page_id}/photos'
        
        data = {
            'url': image_url,
            'caption': message,
            'access_token': access_token
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code != 200:
            return {'success': False, 'error': response.text}
        
        return {'success': True, 'post_id': response.json()['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def publish_to_tiktok(access_token, description, video_url):
    """Publicar en TikTok"""
    try:
        # TikTok API requiere proceso más complejo
        # TODO: Implementar subida de video
        
        return {'success': False, 'error': 'TikTok publishing not implemented yet'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================
# PUBLICACIÓN EN REDES (endpoint unificado)
# ============================================
@app.route('/api/social/publish', methods=['POST'])
def social_publish():
    """Publicar un post en redes seleccionadas usando tokens de SQLite"""
    try:
        data = request.get_json(silent=True) or {}
        codigo = data.get('codigo')
        networks = data.get('networks')  # lista opcional
        page_id = data.get('page_id')
        instagram_account_id = data.get('instagram_account_id')

        if not codigo:
            return jsonify({'success': False, 'error': 'Falta el código del post'}), 400

        print(f"📤 Publicando post {codigo} en: {', '.join(networks) if networks else 'todas las conectadas'} | page_id={page_id} ig_id={instagram_account_id}")

        result = publish_service.publish_to_all(codigo,
                                               platforms=networks,
                                               page_id=page_id,
                                               instagram_account_id=instagram_account_id)

        response = {
            'success': result.get('success', False),
            'published_count': result.get('published', 0),
            'total': result.get('total', 0),
            'results': result.get('results', {})
        }

        if not response['success']:
            response['config_needed'] = True

    except Exception as e:
        print(f"❌ Error en /api/social/publish: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================
# LISTAR PÁGINAS CONECTADAS
# ============================
@app.route('/api/social/pages', methods=['GET'])
def list_social_pages_api():
    try:
        platform = request.args.get('platform')
        if platform:
            pages = db_service.list_social_pages(platform=platform)
        else:
            pages = db_service.list_social_pages()
        return jsonify({'success': True, 'pages': pages})
    except Exception as e:
        print(f"❌ Error en /api/social/pages: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
