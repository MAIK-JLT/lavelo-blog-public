#!/usr/bin/env python3
"""
Script para importar datos desde CSV a MySQL
Ejecutar en el SERVIDOR después de subir los CSVs
"""
import csv
from database import SessionLocal
from models import Post, SocialToken
from datetime import datetime

def parse_boolean(value):
    """Convierte TRUE/FALSE del CSV a boolean"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.upper() == 'TRUE'
    return False

def parse_date(date_str):
    """Parsea fecha en formato DD/MM/YYYY"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Formato: 23/10/2025
        return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
    except:
        try:
            # Formato alternativo: 2025-10-23
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except:
            return None

def import_posts_from_csv(csv_path='posts.csv'):
    """Importa posts desde CSV a MySQL"""
    print("🔄 Importando posts desde CSV...")
    
    db = SessionLocal()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            migrated = 0
            skipped = 0
            errors = 0
            
            for row in reader:
                try:
                    codigo = row.get('Código Post', '').strip()
                    
                    if not codigo:
                        continue
                    
                    # Verificar si ya existe
                    existing = db.query(Post).filter(Post.codigo == codigo).first()
                    
                    if existing:
                        print(f"⏭️  Post {codigo} ya existe, saltando...")
                        skipped += 1
                        continue
                    
                    # Crear nuevo post
                    post = Post(
                        # Principales
                        codigo=codigo,
                        fecha_programada=parse_date(row.get('Fecha Programada', '')),
                        hora_programada=row.get('Hora Programada', '').strip() or None,
                        titulo=row.get('Título', '').strip(),
                        idea=row.get('Idea/Brief', '').strip(),
                        estado=row.get('ESTADO', 'DRAFT').strip(),
                        drive_folder_id=row.get('Drive Folder ID', '').strip() or None,
                        urls=row.get('URLs', '').strip() or None,
                        
                        # Textos
                        base_txt=parse_boolean(row.get('☑ base.txt', 'FALSE')),
                        instagram_txt=parse_boolean(row.get('☑ instagram.txt', 'FALSE')),
                        linkedin_txt=parse_boolean(row.get('☑ linkedin.txt', 'FALSE')),
                        twitter_txt=parse_boolean(row.get('☑ twitter.txt', 'FALSE')),
                        facebook_txt=parse_boolean(row.get('☑ facebook.txt', 'FALSE')),
                        tiktok_txt=parse_boolean(row.get('☑ tiktok.txt', 'FALSE')),
                        prompt_imagen_base_txt=parse_boolean(row.get('☑ prompt_imagen_base.txt', 'FALSE')),
                        
                        # Imágenes
                        imagen_base_png=parse_boolean(row.get('☑ imagen_base.png', 'FALSE')),
                        instagram_1x1_png=parse_boolean(row.get('☑ instagram_1x1.png', 'FALSE')),
                        instagram_stories_9x16_png=parse_boolean(row.get('☑ instagram_stories_9x16.png', 'FALSE')),
                        linkedin_16x9_png=parse_boolean(row.get('☑ linkedin_16x9.png', 'FALSE')),
                        twitter_16x9_png=parse_boolean(row.get('☑ twitter_16x9.png', 'FALSE')),
                        facebook_16x9_png=parse_boolean(row.get('☑ facebook_16x9.png', 'FALSE')),
                        
                        # Videos
                        script_video_base_txt=parse_boolean(row.get('☑ script_video_base.txt', 'FALSE')),
                        video_base_mp4=parse_boolean(row.get('☑ video_base.mp4', 'FALSE')),
                        feed_16x9_mp4=parse_boolean(row.get('☑ feed_16x9.mp4', 'FALSE')),
                        stories_9x16_mp4=parse_boolean(row.get('☑ stories_9x16.mp4', 'FALSE')),
                        shorts_9x16_mp4=parse_boolean(row.get('☑ shorts_9x16.mp4', 'FALSE')),
                        tiktok_9x16_mp4=parse_boolean(row.get('☑ tiktok_9x16.mp4', 'FALSE')),
                        
                        # Publicación
                        blog_published=parse_boolean(row.get('☑ Blog', 'FALSE')),
                        instagram_published=parse_boolean(row.get('☑ Instagram', 'FALSE')),
                        linkedin_published=parse_boolean(row.get('☑ LinkedIn', 'FALSE')),
                        twitter_published=parse_boolean(row.get('☑ Twitter', 'FALSE')),
                        facebook_published=parse_boolean(row.get('☑ Facebook', 'FALSE')),
                        tiktok_published=parse_boolean(row.get('☑ TikTok', 'FALSE')),
                        
                        # Control
                        notas=row.get('Notas/Errores', '').strip() or None,
                        feedback=row.get('Feedback', '').strip() or None
                    )
                    
                    db.add(post)
                    migrated += 1
                    print(f"✅ Importado: {codigo} - {post.titulo[:50]}...")
                    
                except Exception as e:
                    print(f"❌ Error en fila {codigo}: {e}")
                    errors += 1
                    continue
            
            db.commit()
            
            print(f"\n🎉 Importación completada:")
            print(f"   ✅ Importados: {migrated}")
            print(f"   ⏭️  Saltados: {skipped}")
            print(f"   ❌ Errores: {errors}")
            
    except FileNotFoundError:
        print(f"❌ Error: No se encontró {csv_path}")
        print("   Sube el CSV al servidor primero")
    except Exception as e:
        print(f"❌ Error en importación: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def import_social_tokens_from_csv(csv_path='social_tokens.csv'):
    """Importa tokens desde CSV a MySQL"""
    print("\n🔄 Importando tokens de redes sociales...")
    
    db = SessionLocal()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            migrated = 0
            
            for row in reader:
                platform = row.get('platform', '').strip()
                
                if not platform:
                    continue
                
                # Parsear fecha
                expires_at = None
                if row.get('expires_at'):
                    try:
                        expires_at = datetime.fromisoformat(row['expires_at'])
                    except:
                        pass
                
                # Verificar si ya existe
                existing = db.query(SocialToken).filter(
                    SocialToken.platform == platform
                ).first()
                
                if existing:
                    # Actualizar existente
                    existing.access_token = row.get('access_token', '')
                    existing.refresh_token = row.get('refresh_token', '') or None
                    existing.expires_at = expires_at
                    existing.username = row.get('username', '') or None
                    print(f"🔄 Actualizado: {platform}")
                else:
                    # Crear nuevo
                    token = SocialToken(
                        platform=platform,
                        access_token=row.get('access_token', ''),
                        refresh_token=row.get('refresh_token', '') or None,
                        expires_at=expires_at,
                        username=row.get('username', '') or None
                    )
                    db.add(token)
                    print(f"✅ Importado: {platform}")
                
                migrated += 1
            
            db.commit()
            print(f"\n🎉 Tokens importados: {migrated}")
            
    except FileNotFoundError:
        print(f"⚠️  No se encontró {csv_path} (opcional)")
    except Exception as e:
        print(f"❌ Error en importación de tokens: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 IMPORTACIÓN DE CSV A MYSQL")
    print("=" * 60)
    
    import_posts_from_csv('posts.csv')
    import_social_tokens_from_csv('social_tokens.csv')
    
    print("\n" + "=" * 60)
    print("✅ IMPORTACIÓN COMPLETADA")
    print("=" * 60)
