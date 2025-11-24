#!/usr/bin/env python3
"""
Script para obtener Page Access Token desde User Access Token
"""
import requests

# User Access Token del Graph API Explorer
user_token = input("Pega el User Access Token del Graph API Explorer: ").strip()

print("\n📡 Consultando páginas de Facebook...")
pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={user_token}"
response = requests.get(pages_url)

if response.status_code != 200:
    print(f"❌ Error: {response.text}")
    exit(1)

data = response.json()

if not data.get('data') or len(data['data']) == 0:
    print("❌ No se encontraron páginas")
    print("\n🔧 Asegúrate de:")
    print("1. Tener una página de Facebook")
    print("2. El token tiene permiso 'pages_show_list'")
    print("3. Eres administrador de la página")
    exit(1)

print(f"\n✅ Se encontraron {len(data['data'])} página(s):\n")

for i, page in enumerate(data['data']):
    print(f"{i+1}. {page['name']} (ID: {page['id']})")

page_index = 0
if len(data['data']) > 1:
    page_index = int(input("\nSelecciona el número de página: ")) - 1

page = data['data'][page_index]
page_id = page['id']
page_token = page.get('access_token')

if not page_token:
    print("❌ No se encontró Page Access Token")
    exit(1)

print(f"\n✅ Page Access Token obtenido para: {page['name']}")
print(f"   Page ID: {page_id}")

# Obtener Instagram Business Account ID
print("\n📡 Consultando Instagram Business Account...")
ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={page_token}"
ig_response = requests.get(ig_url)

instagram_account_id = None
if ig_response.status_code == 200:
    ig_data = ig_response.json()
    instagram_account_id = ig_data.get('instagram_business_account', {}).get('id')
    if instagram_account_id:
        print(f"✅ Instagram Business Account ID: {instagram_account_id}")
    else:
        print("⚠️  No se encontró Instagram Business Account vinculado")
else:
    print(f"❌ Error: {ig_response.text}")

# Actualizar BD
print("\n📝 Actualizando base de datos...")
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

from database import SessionLocal
from db_models import SocialToken

db = SessionLocal()
try:
    token = db.query(SocialToken).filter(SocialToken.platform == 'instagram').first()
    
    if token:
        token.access_token = page_token
        token.page_id = page_id
        if instagram_account_id:
            token.instagram_account_id = instagram_account_id
        db.commit()
        print("✅ Token actualizado en la BD")
    else:
        print("❌ No se encontró token de Instagram en la BD")
finally:
    db.close()

print("\n🎉 ¡Listo! Ahora intenta publicar desde el panel")
