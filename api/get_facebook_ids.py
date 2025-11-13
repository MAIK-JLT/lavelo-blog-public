#!/usr/bin/env python3
"""
Script para obtener Facebook Page ID e Instagram Business Account ID
usando el token actual de la BD
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Cargar .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# Importar database
from database import SessionLocal
from db_models import SocialToken

def get_ids():
    """Obtener IDs de Facebook/Instagram"""
    
    db = SessionLocal()
    try:
        # Obtener token de Instagram
        token = db.query(SocialToken).filter(
            SocialToken.platform == 'instagram'
        ).first()
        
        if not token:
            print("❌ No hay token de Instagram en la BD")
            print("   Conecta Instagram primero desde el panel")
            return
        
        access_token = token.access_token
        print(f"✅ Token encontrado para usuario {token.user_id}")
        print(f"   Username: {token.username}")
        print()
        
        # Método 1: Intentar obtener páginas (puede fallar si no hay permisos)
        print("📡 Método 1: Consultando páginas de Facebook...")
        pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={access_token}"
        pages_response = requests.get(pages_url)
        
        if pages_response.status_code == 200:
            pages_data = pages_response.json()
            
            if pages_data.get('data') and len(pages_data['data']) > 0:
                page = pages_data['data'][0]
                page_id = page['id']
                page_name = page.get('name', 'N/A')
                
                print(f"✅ Facebook Page encontrada:")
                print(f"   Nombre: {page_name}")
                print(f"   ID: {page_id}")
                print()
                
                # Obtener Instagram Business Account
                print("📡 Consultando Instagram Business Account...")
                ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={access_token}"
                ig_response = requests.get(ig_url)
                
                if ig_response.status_code == 200:
                    ig_data = ig_response.json()
                    instagram_account_id = ig_data.get('instagram_business_account', {}).get('id')
                    
                    if instagram_account_id:
                        print(f"✅ Instagram Business Account ID: {instagram_account_id}")
                        print()
                        print("=" * 60)
                        print("📝 Añade estas líneas a tu .env:")
                        print("=" * 60)
                        print(f"FACEBOOK_PAGE_ID={page_id}")
                        print(f"INSTAGRAM_BUSINESS_ACCOUNT_ID={instagram_account_id}")
                        print("=" * 60)
                    else:
                        print("⚠️  No se encontró Instagram Business Account vinculado")
                        print(f"   Solo se encontró: FACEBOOK_PAGE_ID={page_id}")
                else:
                    print(f"❌ Error consultando Instagram: {ig_response.text}")
            else:
                print("⚠️  No se encontraron páginas")
                print("   Esto significa que el token no tiene permiso 'pages_show_list'")
                print()
                print("🔧 Soluciones:")
                print("   1. Ve a https://developers.facebook.com/apps/1748369472517848")
                print("   2. Roles de la aplicación → Añade tu cuenta como Administrador")
                print("   3. O solicita aprobación del permiso 'pages_show_list'")
        else:
            print(f"❌ Error: {pages_response.text}")
        
        # Método 2: Obtener info del usuario actual
        print()
        print("📡 Método 2: Info del usuario actual...")
        me_url = f"https://graph.facebook.com/v18.0/me?fields=id,name&access_token={access_token}"
        me_response = requests.get(me_url)
        
        if me_response.status_code == 200:
            me_data = me_response.json()
            print(f"✅ Usuario: {me_data.get('name')} (ID: {me_data.get('id')})")
        
    finally:
        db.close()

if __name__ == '__main__':
    get_ids()
