from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('../config/.env')

app = Flask(__name__, static_folder='../panel', static_url_path='')
CORS(app)

# Ruta principal del panel
@app.route('/')
def index():
    return app.send_static_file('index.html')

# API: Obtener estado actual
@app.route('/api/status', methods=['GET'])
def get_status():
    # TODO: Leer desde Google Sheets
    # Por ahora, datos de ejemplo
    return jsonify({
        'codigo': '20251021-1',
        'titulo': 'Test Post',
        'idea': 'Post de prueba del sistema',
        'estado': 'BASE_TEXT_APPROVED',
        'drive_folder_id': '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    })

# API: Generar textos adaptados
@app.route('/api/generate-texts', methods=['POST'])
def generate_texts():
    # TODO: Ejecutar script
    return jsonify({'success': True, 'message': 'Textos generados correctamente'})

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

# API: Publicar
@app.route('/api/publish', methods=['POST'])
def publish():
    return jsonify({'success': True, 'message': 'Publicado correctamente'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
