#!/usr/bin/env python3
"""
Importar posts desde CSV (exportado de Google Sheets) a SQLite
"""
import csv
import sys
from datetime import datetime
from database import SessionLocal
from db_models import Post

def parse_date(date_str):
    """Parsear fecha en varios formatos"""
    if not date_str:
        return None
    
    formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None

def import_csv(csv_path):
    """Importar CSV a BD"""
    db = SessionLocal()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            imported = 0
            skipped = 0
            
            for row in reader:
                # Obtener código (columna C)
                codigo = row.get('Código Post') or row.get('codigo') or row.get('C')
                
                if not codigo:
                    print(f"⏭️  Fila sin código, saltando...")
                    continue
                
                # Verificar si ya existe
                existing = db.query(Post).filter(Post.codigo == codigo).first()
                if existing:
                    print(f"⏭️  {codigo} ya existe, saltando...")
                    skipped += 1
                    continue
                
                # Parsear fecha
                fecha_str = row.get('Fecha Programada') or row.get('fecha_programada') or row.get('A')
                fecha = parse_date(fecha_str)
                
                # Función helper para convertir checkbox
                def to_bool(val):
                    if not val:
                        return False
                    return str(val).upper() in ['TRUE', '1', 'YES', 'SÍ', 'SI', 'X', '✓', '✔']
                
                # Crear post con TODAS las columnas (con y sin emojis)
                post = Post(
                    codigo=codigo,
                    fecha_programada=fecha,
                    hora_programada=row.get('Hora Programada') or row.get('B') or '',
                    titulo=row.get('Título') or row.get('D') or '',
                    idea=row.get('Idea/Brief') or row.get('E') or '',
                    estado=row.get('ESTADO') or row.get('F') or 'DRAFT',
                    drive_folder_id=row.get('Drive Folder ID') or row.get('G') or '',
                    urls=row.get('URLs') or row.get('H') or '',
                    
                    # TEXTOS (I-O) - Con emoji ☑
                    base_txt=to_bool(row.get('☑ base.txt') or row.get('base.txt') or row.get('I')),
                    instagram_txt=to_bool(row.get('☑ instagram.txt') or row.get('instagram.txt') or row.get('J')),
                    linkedin_txt=to_bool(row.get('☑ linkedin.txt') or row.get('linkedin.txt') or row.get('K')),
                    twitter_txt=to_bool(row.get('☑ twitter.txt') or row.get('twitter.txt') or row.get('L')),
                    facebook_txt=to_bool(row.get('☑ facebook.txt') or row.get('facebook.txt') or row.get('M')),
                    tiktok_txt=to_bool(row.get('☑ tiktok.txt') or row.get('tiktok.txt') or row.get('N')),
                    prompt_imagen_base_txt=to_bool(row.get('☑ prompt_imagen_base.txt') or row.get('prompt_imagen_base.txt') or row.get('O')),
                    
                    # IMÁGENES (P-U) - Con emoji ☑
                    imagen_base_png=to_bool(row.get('☑ imagen_base.png') or row.get('imagen_base.png') or row.get('P')),
                    instagram_1x1_png=to_bool(row.get('☑ instagram_1x1.png') or row.get('instagram_1x1.png') or row.get('Q')),
                    instagram_stories_9x16_png=to_bool(row.get('☑ instagram_stories_9x16.png') or row.get('instagram_stories_9x16.png') or row.get('R')),
                    linkedin_16x9_png=to_bool(row.get('☑ linkedin_16x9.png') or row.get('linkedin_16x9.png') or row.get('S')),
                    twitter_16x9_png=to_bool(row.get('☑ twitter_16x9.png') or row.get('twitter_16x9.png') or row.get('T')),
                    facebook_16x9_png=to_bool(row.get('☑ facebook_16x9.png') or row.get('facebook_16x9.png') or row.get('U')),
                    
                    # VIDEOS (V-AA) - Con emoji ☑
                    script_video_base_txt=to_bool(row.get('☑ script_video_base.txt') or row.get('script_video_base.txt') or row.get('V')),
                    video_base_mp4=to_bool(row.get('☑ video_base.mp4') or row.get('video_base.mp4') or row.get('W')),
                    feed_16x9_mp4=to_bool(row.get('☑ feed_16x9.mp4') or row.get('feed_16x9.mp4') or row.get('X')),
                    stories_9x16_mp4=to_bool(row.get('☑ stories_9x16.mp4') or row.get('stories_9x16.mp4') or row.get('Y')),
                    shorts_9x16_mp4=to_bool(row.get('☑ shorts_9x16.mp4') or row.get('shorts_9x16.mp4') or row.get('Z')),
                    tiktok_9x16_mp4=to_bool(row.get('☑ tiktok_9x16.mp4') or row.get('tiktok_9x16.mp4') or row.get('AA')),
                    
                    # PUBLICACIÓN (AB-AG) - Con emoji ☑
                    blog_published=to_bool(row.get('☑ Blog') or row.get('Blog') or row.get('AB')),
                    instagram_published=to_bool(row.get('☑ Instagram') or row.get('Instagram') or row.get('AC')),
                    linkedin_published=to_bool(row.get('☑ LinkedIn') or row.get('LinkedIn') or row.get('AD')),
                    twitter_published=to_bool(row.get('☑ Twitter') or row.get('Twitter') or row.get('AE')),
                    facebook_published=to_bool(row.get('☑ Facebook') or row.get('Facebook') or row.get('AF')),
                    tiktok_published=to_bool(row.get('☑ TikTok') or row.get('TikTok') or row.get('AG')),
                    
                    # CONTROL (AH-AJ)
                    fecha_real_publicacion=parse_date(row.get('Fecha Real Publicación') or row.get('AH')),
                    notas=row.get('Notas/Errores') or row.get('AI') or '',
                    feedback=row.get('Feedback') or row.get('AJ') or ''
                )
                
                db.add(post)
                print(f"✅ {codigo}: {post.titulo}")
                imported += 1
            
            db.commit()
            
            print(f"\n{'='*60}")
            print(f"✅ Importación completada:")
            print(f"   - Importados: {imported}")
            print(f"   - Saltados: {skipped}")
            print(f"{'='*60}")
            
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {csv_path}")
        print(f"   Descarga el CSV de Google Sheets primero")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 import_csv.py <archivo.csv>")
        print("\nEjemplo:")
        print("  python3 import_csv.py posts.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    import_csv(csv_path)
