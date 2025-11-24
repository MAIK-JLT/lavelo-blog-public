#!/usr/bin/env python3
"""
Script para actualizar tokens existentes con page_id e instagram_account_id
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Cargar .env (producción primero, luego fallback local)
default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

# Importar database
from database import SessionLocal
from db_models import SocialToken

def update_tokens():
    """Actualizar tokens existentes con page_id e instagram_account_id"""
    
    db = SessionLocal()
    try:
        # Obtener todos los tokens de Instagram
        instagram_tokens = db.query(SocialToken).filter(
            SocialToken.platform == 'instagram'
        ).all()
        
        if not instagram_tokens:
            print("⚠️  No hay tokens de Instagram en la BD")
            return
        
        for token in instagram_tokens:
            print(f"\n🔄 Procesando token de usuario {token.user_id}...")
            
            access_token = token.access_token
            
            # Obtener páginas de Facebook
            pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={access_token}"
            print(f"📡 Consultando páginas de Facebook...")
            
            try:
                pages_response = requests.get(pages_url)
                
                if pages_response.status_code != 200:
                    print(f"❌ Error obteniendo páginas: {pages_response.text}")
                    continue
                
                pages_data = pages_response.json()
                
                if not pages_data.get('data') or len(pages_data['data']) == 0:
                    print("⚠️  No se encontraron páginas de Facebook")
                    continue
                
                # Tomar la primera página
                page_id = pages_data['data'][0]['id']
                page_name = pages_data['data'][0].get('name', 'N/A')
                print(f"✅ Facebook Page encontrada: {page_name} (ID: {page_id})")
                
                # Obtener Instagram Business Account ID
                ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={access_token}"
                print(f"📡 Consultando Instagram Business Account...")
                
                ig_response = requests.get(ig_url)
                
                if ig_response.status_code != 200:
                    print(f"❌ Error obteniendo Instagram Account: {ig_response.text}")
                    # Guardar solo page_id
                    token.page_id = page_id
                    db.commit()
                    print(f"✅ page_id actualizado: {page_id}")
                    continue
                
                ig_data = ig_response.json()
                instagram_account_id = ig_data.get('instagram_business_account', {}).get('id')
                
                if instagram_account_id:
                    print(f"✅ Instagram Business Account ID: {instagram_account_id}")
                    
                    # Actualizar token
                    token.page_id = page_id
                    token.instagram_account_id = instagram_account_id
                    db.commit()
                    
                    print(f"🎉 Token actualizado correctamente:")
                    print(f"   - page_id: {page_id}")
                    print(f"   - instagram_account_id: {instagram_account_id}")
                else:
                    print("⚠️  No se encontró Instagram Business Account vinculado a esta página")
                    print("   Asegúrate de que la página de Facebook tiene una cuenta de Instagram Business vinculada")
                    # Guardar solo page_id
                    token.page_id = page_id
                    db.commit()
                    print(f"✅ page_id actualizado: {page_id}")
                
            except Exception as e:
                print(f"❌ Error procesando token: {e}")
                continue
        
        print("\n✅ Proceso completado")
        
    finally:
        db.close()

if __name__ == '__main__':
    update_tokens()
