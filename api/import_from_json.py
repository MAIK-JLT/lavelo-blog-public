#!/usr/bin/env python3
"""
Script para importar datos desde JSON a MySQL
Ejecutar en el SERVIDOR después de subir los archivos JSON
"""
import json
from database import SessionLocal
from models import Post, SocialToken
from datetime import datetime

def import_posts():
    """Importa posts desde JSON a MySQL"""
    print("🔄 Importando posts desde JSON...")
    
    db = SessionLocal()
    
    try:
        # Leer JSON
        with open('posts_export.json', 'r', encoding='utf-8') as f:
            posts_data = json.load(f)
        
        print(f"📊 Encontrados {len(posts_data)} posts en JSON")
        
        migrated = 0
        skipped = 0
        
        for post_data in posts_data:
            # Verificar si ya existe
            existing = db.query(Post).filter(Post.codigo == post_data['codigo']).first()
            
            if existing:
                print(f"⏭️  Post {post_data['codigo']} ya existe, saltando...")
                skipped += 1
                continue
            
            # Parsear fecha
            fecha_prog = None
            if post_data.get('fecha_programada'):
                try:
                    fecha_prog = datetime.strptime(post_data['fecha_programada'], '%Y-%m-%d').date()
                except:
                    pass
            
            # Crear nuevo post con TODAS las columnas
            post = Post(
                # Principales
                codigo=post_data['codigo'],
                fecha_programada=fecha_prog,
                hora_programada=post_data.get('hora_programada'),
                titulo=post_data.get('titulo', ''),
                idea=post_data.get('idea', ''),
                estado=post_data.get('estado', 'DRAFT'),
                drive_folder_id=post_data.get('drive_folder_id'),
                urls=post_data.get('urls'),
                
                # Textos
                base_txt=post_data.get('base_txt', False),
                instagram_txt=post_data.get('instagram_txt', False),
                linkedin_txt=post_data.get('linkedin_txt', False),
                twitter_txt=post_data.get('twitter_txt', False),
                facebook_txt=post_data.get('facebook_txt', False),
                tiktok_txt=post_data.get('tiktok_txt', False),
                prompt_imagen_base_txt=post_data.get('prompt_imagen_base_txt', False),
                
                # Imágenes
                imagen_base_png=post_data.get('imagen_base_png', False),
                instagram_1x1_png=post_data.get('instagram_1x1_png', False),
                instagram_stories_9x16_png=post_data.get('instagram_stories_9x16_png', False),
                linkedin_16x9_png=post_data.get('linkedin_16x9_png', False),
                twitter_16x9_png=post_data.get('twitter_16x9_png', False),
                facebook_16x9_png=post_data.get('facebook_16x9_png', False),
                
                # Videos
                script_video_base_txt=post_data.get('script_video_base_txt', False),
                video_base_mp4=post_data.get('video_base_mp4', False),
                feed_16x9_mp4=post_data.get('feed_16x9_mp4', False),
                stories_9x16_mp4=post_data.get('stories_9x16_mp4', False),
                shorts_9x16_mp4=post_data.get('shorts_9x16_mp4', False),
                tiktok_9x16_mp4=post_data.get('tiktok_9x16_mp4', False),
                
                # Publicación
                blog_published=post_data.get('blog_published', False),
                instagram_published=post_data.get('instagram_published', False),
                linkedin_published=post_data.get('linkedin_published', False),
                twitter_published=post_data.get('twitter_published', False),
                facebook_published=post_data.get('facebook_published', False),
                tiktok_published=post_data.get('tiktok_published', False),
                
                # Control
                notas=post_data.get('notas'),
                feedback=post_data.get('feedback')
            )
            
            db.add(post)
            migrated += 1
            print(f"✅ Importado: {post_data['codigo']} - {post_data.get('titulo', 'Sin título')}")
        
        db.commit()
        
        print(f"\n🎉 Importación completada:")
        print(f"   ✅ Importados: {migrated}")
        print(f"   ⏭️  Saltados: {skipped}")
        
    except FileNotFoundError:
        print("❌ Error: No se encontró posts_export.json")
        print("   Ejecuta export_sheets_data.py en tu Mac primero")
    except Exception as e:
        print(f"❌ Error en importación: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def import_social_tokens():
    """Importa tokens desde JSON a MySQL"""
    print("\n🔄 Importando tokens de redes sociales...")
    
    db = SessionLocal()
    
    try:
        # Leer JSON
        with open('tokens_export.json', 'r', encoding='utf-8') as f:
            tokens_data = json.load(f)
        
        print(f"📊 Encontrados {len(tokens_data)} tokens en JSON")
        
        migrated = 0
        
        for token_data in tokens_data:
            # Verificar si ya existe
            existing = db.query(SocialToken).filter(
                SocialToken.platform == token_data['platform']
            ).first()
            
            # Parsear fecha
            expires_at = None
            if token_data.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(token_data['expires_at'])
                except:
                    pass
            
            if existing:
                # Actualizar existente
                existing.access_token = token_data['access_token']
                existing.refresh_token = token_data.get('refresh_token')
                existing.expires_at = expires_at
                existing.username = token_data.get('username')
                print(f"🔄 Actualizado: {token_data['platform']}")
            else:
                # Crear nuevo
                token = SocialToken(
                    platform=token_data['platform'],
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    expires_at=expires_at,
                    username=token_data.get('username')
                )
                db.add(token)
                print(f"✅ Importado: {token_data['platform']}")
            
            migrated += 1
        
        db.commit()
        print(f"\n🎉 Tokens importados: {migrated}")
        
    except FileNotFoundError:
        print("⚠️  No se encontró tokens_export.json (opcional)")
    except Exception as e:
        print(f"❌ Error en importación de tokens: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 IMPORTACIÓN DE JSON A MYSQL")
    print("=" * 60)
    
    import_posts()
    import_social_tokens()
    
    print("\n" + "=" * 60)
    print("✅ IMPORTACIÓN COMPLETADA")
    print("=" * 60)
