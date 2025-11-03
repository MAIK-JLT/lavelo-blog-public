#!/usr/bin/env python3
"""
Script para migrar datos de Google Sheets a MySQL
"""
from sheets_service import get_all_posts, get_social_tokens
from database import SessionLocal
from models import Post, SocialToken
from datetime import datetime

def migrate_posts():
    """Migra posts de Sheets a MySQL"""
    print("🔄 Migrando posts de Google Sheets a MySQL...")
    
    db = SessionLocal()
    
    try:
        # Obtener posts de Sheets
        posts_data = get_all_posts()
        print(f"📊 Encontrados {len(posts_data)} posts en Sheets")
        
        migrated = 0
        skipped = 0
        
        for post_data in posts_data:
            # Verificar si ya existe
            existing = db.query(Post).filter(Post.codigo == post_data['codigo']).first()
            
            if existing:
                print(f"⏭️  Post {post_data['codigo']} ya existe, saltando...")
                skipped += 1
                continue
            
            # Crear nuevo post
            post = Post(
                codigo=post_data['codigo'],
                titulo=post_data.get('titulo', ''),
                contenido=post_data.get('contenido', ''),
                categoria=post_data.get('categoria', 'training'),
                estado=post_data.get('estado', 'DRAFT'),
                drive_folder_id=post_data.get('drive_folder_id'),
                fecha_programada=datetime.strptime(post_data['fecha_programada'], '%Y-%m-%d') if post_data.get('fecha_programada') else None,
                hora_programada=post_data.get('hora_programada')
            )
            
            db.add(post)
            migrated += 1
            print(f"✅ Migrado: {post_data['codigo']} - {post_data.get('titulo', 'Sin título')}")
        
        db.commit()
        
        print(f"\n🎉 Migración completada:")
        print(f"   ✅ Migrados: {migrated}")
        print(f"   ⏭️  Saltados: {skipped}")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def migrate_social_tokens():
    """Migra tokens de redes sociales de Sheets a MySQL"""
    print("\n🔄 Migrando tokens de redes sociales...")
    
    db = SessionLocal()
    
    try:
        # Obtener tokens de Sheets
        tokens_data = get_social_tokens()
        print(f"📊 Encontrados {len(tokens_data)} tokens en Sheets")
        
        migrated = 0
        
        for token_data in tokens_data:
            # Verificar si ya existe
            existing = db.query(SocialToken).filter(
                SocialToken.platform == token_data['platform']
            ).first()
            
            if existing:
                # Actualizar existente
                existing.access_token = token_data['access_token']
                existing.refresh_token = token_data.get('refresh_token')
                existing.expires_at = datetime.fromisoformat(token_data['expires_at']) if token_data.get('expires_at') else None
                existing.username = token_data.get('username')
                print(f"🔄 Actualizado: {token_data['platform']}")
            else:
                # Crear nuevo
                token = SocialToken(
                    platform=token_data['platform'],
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    expires_at=datetime.fromisoformat(token_data['expires_at']) if token_data.get('expires_at') else None,
                    username=token_data.get('username')
                )
                db.add(token)
                print(f"✅ Migrado: {token_data['platform']}")
            
            migrated += 1
        
        db.commit()
        print(f"\n🎉 Tokens migrados: {migrated}")
        
    except Exception as e:
        print(f"❌ Error en migración de tokens: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MIGRACIÓN DE GOOGLE SHEETS A MYSQL")
    print("=" * 60)
    
    migrate_posts()
    migrate_social_tokens()
    
    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 60)
