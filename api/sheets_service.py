"""
Servicio para interactuar con Google Sheets
Maneja autenticación OAuth2 y operaciones CRUD
"""

import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Configuración - Mismos scopes que MCP (orden importante)
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')

class SheetsService:
    def __init__(self):
        self.creds = None
        self.service = None
        self.drive_service = None
        self.token_path = 'config/token.json'
        
        # Intentar autenticar automáticamente al iniciar
        self.authenticate()
        
    def authenticate(self, credentials_dict=None):
        """Autenticar con Google Sheets usando OAuth2"""
        # Si ya tenemos token guardado, usarlo
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                
                # Si está expirado pero tiene refresh token, refrescar
                if self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    self._save_token()
                    print("✅ Token refrescado automáticamente")
            except Exception as e:
                print(f"⚠️ Error cargando token: {e}")
                self.creds = None
        
        # Si viene credentials_dict (primera vez desde web), usarlo
        elif credentials_dict:
            self.creds = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
            self._save_token()
            print("✅ Token guardado desde OAuth web")
        
        # Construir servicios si tenemos credenciales válidas
        if self.creds and self.creds.valid:
            try:
                self.service = build('sheets', 'v4', credentials=self.creds)
                self.drive_service = build('drive', 'v3', credentials=self.creds)
                print("✅ Servicios de Google autenticados correctamente")
                return True
            except Exception as e:
                print(f"❌ Error construyendo servicios: {e}")
                return False
        
        return False
    
    def _save_token(self):
        """Guardar token para reutilizarlo"""
        try:
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
            print(f"✅ Token guardado en {self.token_path}")
        except Exception as e:
            print(f"❌ Error guardando token: {e}")
    
    def get_oauth_flow(self):
        """Crear flujo OAuth2 para autenticación"""
        flow = Flow.from_client_secrets_file(
            'config/credentials.json',  # ← Usa el archivo directamente
            scopes=SCOPES,
            redirect_uri='http://localhost:5001/oauth2callback'
        )
        
        return flow
    
    def get_posts(self):
        """Obtener todos los posts del Excel"""
        try:
            # Intentar diferentes nombres de hojas
            sheet_names = ['Sheet1', 'Posts', 'Hoja 1', 'Hoja1']
            result = None
            
            for sheet_name in sheet_names:
                try:
                    result = self.service.spreadsheets().values().get(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f'{sheet_name}!A2:AP'  # Leer todas las columnas hasta AP (incluye redes)
                    ).execute()
                    print(f"✅ Hoja encontrada: {sheet_name}")
                    break
                except HttpError:
                    continue
            
            if not result:
                print("❌ No se encontró ninguna hoja válida")
                return []
            
            rows = result.get('values', [])
            posts = []
            
            for row in rows:
                # Mapeo según el orden REAL del Excel
                # A=Fecha, B=Hora, C=Código, D=Título, E=Idea, F=ESTADO, G=Drive ID, H=URLs
                # I=base.txt, J=instagram.txt, K=linkedin.txt, L=twitter.txt, M=facebook.txt, N=tiktok.txt
                # O=prompt_imagen, P=imagen_base, Q-U=formatos imagen, V=script_video, W=video_base, X-AA=formatos video
                # AB-AG=publicaciones, AH=fecha_real, AI=notas, AJ=feedback
                # AK-AP=redes sociales activas (instagram, linkedin, twitter, facebook, tiktok, blog)
                
                post = {
                    'codigo': row[2] if len(row) > 2 else '',  # C
                    'titulo': row[3] if len(row) > 3 else '',  # D
                    'idea': row[4] if len(row) > 4 else '',    # E
                    'estado_excel': row[5] if len(row) > 5 else 'DRAFT',  # F
                    'drive_folder_id': row[6] if len(row) > 6 else '',  # G
                    'base_text': row[8] if len(row) > 8 else 'FALSE',  # I (☑ base.txt)
                    'adapted_texts': 'TRUE' if all([
                        (row[9] if len(row) > 9 else 'FALSE') == 'TRUE',  # instagram
                        (row[10] if len(row) > 10 else 'FALSE') == 'TRUE',  # linkedin
                        (row[11] if len(row) > 11 else 'FALSE') == 'TRUE',  # twitter
                        (row[12] if len(row) > 12 else 'FALSE') == 'TRUE',  # facebook
                        (row[13] if len(row) > 13 else 'FALSE') == 'TRUE'   # tiktok
                    ]) else 'FALSE',
                    'image_prompt': row[14] if len(row) > 14 else 'FALSE',  # O (prompt_imagen)
                    'image_base': row[15] if len(row) > 15 else 'FALSE',    # P (imagen_base)
                    'image_formats': 'TRUE' if all([
                        (row[16] if len(row) > 16 else 'FALSE') == 'TRUE',  # instagram_1x1
                        (row[17] if len(row) > 17 else 'FALSE') == 'TRUE',  # instagram_stories
                        (row[18] if len(row) > 18 else 'FALSE') == 'TRUE',  # linkedin
                        (row[19] if len(row) > 19 else 'FALSE') == 'TRUE',  # twitter
                        (row[20] if len(row) > 20 else 'FALSE') == 'TRUE'   # facebook
                    ]) else 'FALSE',
                    'video_prompt': row[21] if len(row) > 21 else 'FALSE',  # U (script_video)
                    'video_base': row[22] if len(row) > 22 else 'FALSE',    # V (video_base)
                    'video_formats': 'TRUE' if all([
                        (row[23] if len(row) > 23 else 'FALSE') == 'TRUE',  # feed_16x9
                        (row[24] if len(row) > 24 else 'FALSE') == 'TRUE',  # stories_9x16
                        (row[25] if len(row) > 25 else 'FALSE') == 'TRUE',  # shorts
                        (row[26] if len(row) > 26 else 'FALSE') == 'TRUE'   # tiktok
                    ]) else 'FALSE',
                    'published': 'TRUE' if all([
                        (row[27] if len(row) > 27 else 'FALSE') == 'TRUE',  # Blog
                        (row[28] if len(row) > 28 else 'FALSE') == 'TRUE',  # Instagram
                        (row[29] if len(row) > 29 else 'FALSE') == 'TRUE',  # LinkedIn
                        (row[30] if len(row) > 30 else 'FALSE') == 'TRUE',  # Twitter
                        (row[31] if len(row) > 31 else 'FALSE') == 'TRUE',  # Facebook
                        (row[32] if len(row) > 32 else 'FALSE') == 'TRUE'   # TikTok
                    ]) else 'FALSE',
                    'publication_date': row[33] if len(row) > 33 else '',
                    'notes': row[34] if len(row) > 34 else '',
                    # Campos individuales para validación selectiva
                    'instagram_text': row[9] if len(row) > 9 else 'FALSE',
                    'linkedin_text': row[10] if len(row) > 10 else 'FALSE',
                    'twitter_text': row[11] if len(row) > 11 else 'FALSE',
                    'facebook_text': row[12] if len(row) > 12 else 'FALSE',
                    'tiktok_text': row[13] if len(row) > 13 else 'FALSE',
                    'instagram_image': row[16] if len(row) > 16 else 'FALSE',
                    'instagram_stories_image': row[17] if len(row) > 17 else 'FALSE',
                    'linkedin_image': row[18] if len(row) > 18 else 'FALSE',
                    'twitter_image': row[19] if len(row) > 19 else 'FALSE',
                    'facebook_image': row[20] if len(row) > 20 else 'FALSE',
                    # Redes sociales activas (AK-AP = columnas 36-41)
                    'redes_instagram': row[36] if len(row) > 36 else 'TRUE',  # AK
                    'redes_linkedin': row[37] if len(row) > 37 else 'TRUE',   # AL
                    'redes_twitter': row[38] if len(row) > 38 else 'TRUE',    # AM
                    'redes_facebook': row[39] if len(row) > 39 else 'TRUE',   # AN
                    'redes_tiktok': row[40] if len(row) > 40 else 'TRUE',     # AO
                    'redes_blog': row[41] if len(row) > 41 else 'TRUE'        # AP
                }
                
                # Usar el estado directamente de la columna F del Excel
                post['estado'] = post['estado_excel']
                
                print(f"✅ Post: {post['codigo']} - {post['titulo']} - Estado: {post['estado']}")
                posts.append(post)
            
            return posts
        
        except HttpError as error:
            print(f'Error al leer Google Sheets: {error}')
            return []
    
    def update_post_field(self, codigo, field, value):
        """Actualizar un campo específico de un post"""
        try:
            # Primero encontrar la fila del post (buscar en columna C = código)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!C2:C'
            ).execute()
            
            rows = result.get('values', [])
            row_index = None
            
            for i, row in enumerate(rows):
                if row and row[0] == codigo:
                    row_index = i + 2  # +2 porque empezamos en fila 2
                    break
            
            if row_index is None:
                print(f'❌ Post {codigo} no encontrado')
                return False
            
            # Mapear campo a columna según el Excel real
            field_to_column = {
                'estado': 'F',  # ESTADO
                'base_text': 'I',  # ☑ base.txt
                'adapted_texts_instagram': 'J',  # ☑ instagram.txt
                'adapted_texts_linkedin': 'K',   # ☑ linkedin.txt
                'adapted_texts_twitter': 'L',    # ☑ twitter.txt
                'adapted_texts_facebook': 'M',   # ☑ facebook.txt
                'adapted_texts_tiktok': 'N',     # ☑ tiktok.txt
                'image_prompt': 'O',  # ☑ prompt_imagen_base.txt
                'image_base': 'P',    # ☑ imagen_base.png
                'instagram_image': 'Q',  # ☑ instagram_1x1.png
                'instagram_stories_image': 'R',  # ☑ instagram_stories_9x16.png
                'linkedin_image': 'S',  # ☑ linkedin_16x9.png
                'twitter_image': 'T',  # ☑ twitter_16x9.png
                'facebook_image': 'U',  # ☑ facebook_16x9.png
                'video_prompt': 'V',  # ☑ script_video_base.txt
                'video_base': 'W',    # ☑ video_base.mp4
                # Redes sociales activas
                'redes_instagram': 'AK',  # ☑ Instagram activo
                'redes_linkedin': 'AL',   # ☑ LinkedIn activo
                'redes_twitter': 'AM',    # ☑ Twitter activo
                'redes_facebook': 'AN',   # ☑ Facebook activo
                'redes_tiktok': 'AO',     # ☑ TikTok activo
                'redes_blog': 'AP',       # ☑ Blog activo
            }
            
            column = field_to_column.get(field)
            if not column:
                print(f'❌ Campo {field} no reconocido')
                return False
            
            # Actualizar celda
            range_name = f'Sheet1!{column}{row_index}'
            body = {'values': [[value]]}
            
            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f'✅ Actualizado {field} = {value} en fila {row_index}')
            return True
        
        except HttpError as error:
            print(f'❌ Error al actualizar Google Sheets: {error}')
            return False
    
    def batch_update_networks(self, codigo, redes):
        """Actualizar todas las redes sociales en una sola llamada batch"""
        try:
            # Buscar fila del post
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!C2:C'
            ).execute()
            
            rows = result.get('values', [])
            row_index = None
            
            for i, row in enumerate(rows):
                if row and row[0] == codigo:
                    row_index = i + 2
                    break
            
            if row_index is None:
                print(f'❌ Post {codigo} no encontrado')
                return False
            
            # Mapeo de redes a columnas
            network_columns = {
                'instagram': 'AK',
                'linkedin': 'AL',
                'twitter': 'AM',
                'facebook': 'AN',
                'tiktok': 'AO',
                'blog': 'AP'
            }
            
            # Preparar datos para batch update
            data = []
            for network, active in redes.items():
                column = network_columns.get(network)
                if column:
                    value = 'TRUE' if active else 'FALSE'
                    data.append({
                        'range': f'Sheet1!{column}{row_index}',
                        'values': [[value]]
                    })
            
            # Ejecutar batch update (1 sola llamada API)
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            
            print(f'✅ Redes actualizadas en batch para {codigo}')
            return True
            
        except HttpError as error:
            print(f'❌ Error en batch update: {error}')
            return False
    
    def reset_dependent_phases(self, codigo, current_estado):
        """Resetear fases dependientes cuando se edita una fase validada"""
        try:
            print(f"🔄 Reseteando fases dependientes de {current_estado}")
            
            # Mapeo de qué fases resetear según la fase actual
            reset_map = {
                'BASE_TEXT_AWAITING': [
                    'adapted_texts_instagram', 'adapted_texts_linkedin', 
                    'adapted_texts_twitter', 'adapted_texts_facebook', 'adapted_texts_tiktok',
                    'image_prompt', 'image_base',
                    'instagram_image', 'instagram_stories_image', 'linkedin_image', 'twitter_image', 'facebook_image',
                    'video_prompt', 'video_base'
                ],
                'ADAPTED_TEXTS_AWAITING': [],  # No resetea nada
                'IMAGE_PROMPT_AWAITING': [
                    'image_base',
                    'instagram_image', 'instagram_stories_image', 'linkedin_image', 'twitter_image', 'facebook_image'
                ],
                'IMAGE_BASE_AWAITING': [
                    'instagram_image', 'instagram_stories_image', 'linkedin_image', 'twitter_image', 'facebook_image'
                ],
                'IMAGE_FORMATS_AWAITING': [],
                'VIDEO_PROMPT_AWAITING': ['video_base'],
                'VIDEO_BASE_AWAITING': [],
                'VIDEO_FORMATS_AWAITING': []
            }
            
            fields_to_reset = reset_map.get(current_estado, [])
            
            if not fields_to_reset:
                print("✅ No hay fases dependientes que resetear")
                return True
            
            # Resetear cada campo a FALSE
            for field in fields_to_reset:
                self.update_post_field(codigo, field, 'FALSE')
                print(f"  ↳ {field} = FALSE")
            
            # Actualizar estado al actual (para forzar recálculo)
            self.update_post_field(codigo, 'estado', current_estado)
            
            print(f"✅ Fases dependientes reseteadas")
            return True
            
        except Exception as e:
            print(f"❌ Error reseteando fases: {e}")
            return False
    
    def _excel_to_panel_state(self, post):
        """Convertir estados del Excel al estado del panel"""
        # Orden de prioridad de estados
        fields = [
            'base_text',
            'adapted_texts', 
            'image_prompt',
            'image_base',
            'image_formats',
            'video_prompt',
            'video_base',
            'video_formats',
            'published'
        ]
        
        state_mapping = {
            'base_text': 'BASE_TEXT',
            'adapted_texts': 'ADAPTED_TEXTS',
            'image_prompt': 'IMAGE_PROMPT',
            'image_base': 'IMAGE_BASE',
            'image_formats': 'IMAGE_FORMATS',
            'video_prompt': 'VIDEO_PROMPT',
            'video_base': 'VIDEO_BASE',
            'video_formats': 'VIDEO_FORMATS',
            'published': 'PUBLISHED'
        }
        
        # Encontrar el primer campo que no esté en TRUE
        for field in fields:
            value = post.get(field, 'FALSE')
            
            if value == 'FALSE':
                return f'{state_mapping[field]}_AWAITING'
            elif value == 'GENERATING':
                return f'{state_mapping[field]}_GENERATING'
            elif value == 'AWAITING_VALIDATION':
                return f'{state_mapping[field]}_AWAITING'
        
        # Si todos están en TRUE
        return 'PUBLISHED'
    
    def get_subfolder_id(self, parent_folder_id, subfolder_name, create_if_missing=False):
        """Obtener el ID de una subcarpeta dentro de una carpeta, creándola si no existe"""
        try:
            if not hasattr(self, 'drive_service'):
                self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            query = f"name='{subfolder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                print(f"✅ Subcarpeta encontrada: {subfolder_name} (ID: {folders[0]['id']})")
                return folders[0]['id']
            
            # Si no existe y create_if_missing=True, crearla
            if create_if_missing:
                print(f"📁 Creando subcarpeta: {subfolder_name}")
                folder_metadata = {
                    'name': subfolder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_folder_id]
                }
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                folder_id = folder.get('id')
                print(f"✅ Subcarpeta creada: {subfolder_name} (ID: {folder_id})")
                return folder_id
            
            print(f"❌ Subcarpeta no encontrada: {subfolder_name}")
            return None
            
        except Exception as e:
            print(f"❌ Error buscando/creando subcarpeta {subfolder_name}: {str(e)}")
            return None
    
    def get_file_from_drive(self, folder_id, filename):
        """Leer contenido de un archivo de texto desde Google Drive"""
        try:
            # Construir servicio de Drive si no existe
            if not hasattr(self, 'drive_service'):
                self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # DEBUG: Listar todos los archivos en la carpeta
            print(f"🔍 Buscando en carpeta: {folder_id}")
            all_files = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, mimeType)'
            ).execute()
            print(f"📁 Archivos en carpeta:")
            for f in all_files.get('files', []):
                print(f"  - {f['name']} (tipo: {f['mimeType']})")
            
            # Buscar archivo por nombre en la carpeta
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if not files:
                print(f"❌ Archivo no encontrado: {filename}")
                return None
            
            file_id = files[0]['id']
            
            # Descargar contenido
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            print(f"✅ Archivo leído: {filename} ({len(content)} caracteres)")
            return content
            
        except Exception as e:
            print(f"❌ Error leyendo archivo {filename}: {str(e)}")
            return None
    
    def save_file_to_drive(self, folder_id, filename, content):
        """Guardar contenido de texto en Google Drive"""
        try:
            # Construir servicio de Drive si no existe
            if not hasattr(self, 'drive_service'):
                self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Buscar si el archivo ya existe
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            # Preparar contenido
            file_content = io.BytesIO(content.encode('utf-8'))
            media = MediaIoBaseUpload(file_content, mimetype='text/plain', resumable=True)
            
            if files:
                # Actualizar archivo existente
                file_id = files[0]['id']
                self.drive_service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ Archivo actualizado: {filename}")
            else:
                # Crear nuevo archivo
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': 'text/plain'
                }
                self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"✅ Archivo creado: {filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error guardando archivo {filename}: {str(e)}")
            return False
    
    def save_image_to_drive(self, folder_id, filename, image_bytes):
        """Guardar imagen binaria en Google Drive"""
        try:
            if not hasattr(self, 'drive_service'):
                self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Buscar si el archivo ya existe
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            # Preparar contenido
            file_content = io.BytesIO(image_bytes)
            media = MediaIoBaseUpload(file_content, mimetype='image/png', resumable=True)
            
            if files:
                # Actualizar archivo existente
                file_id = files[0]['id']
                self.drive_service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ Imagen actualizada: {filename}")
            else:
                # Crear nuevo archivo
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': 'image/png'
                }
                self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"✅ Imagen creada: {filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error guardando imagen {filename}: {str(e)}")
            return False
    
    def get_image_from_drive(self, folder_id, filename):
        """Leer imagen desde Google Drive y devolver bytes"""
        try:
            if not hasattr(self, 'drive_service'):
                self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Buscar archivo por nombre
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if not files:
                print(f"❌ Imagen no encontrada: {filename}")
                return None
            
            file_id = files[0]['id']
            
            # Descargar contenido
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            image_bytes = file_content.getvalue()
            print(f"✅ Imagen leída: {filename} ({len(image_bytes)} bytes)")
            return image_bytes
            
        except Exception as e:
            print(f"❌ Error leyendo imagen {filename}: {str(e)}")
            return None

# Instancia global
sheets_service = SheetsService()
