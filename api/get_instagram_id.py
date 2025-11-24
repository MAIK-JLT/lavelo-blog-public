#!/usr/bin/env python3
"""
Script para obtener Instagram Business Account ID desde el Page ID
"""
import requests

# Tu Page ID
page_id = "61581135985460"

# Token del Graph API Explorer (el que tienes ahora)
access_token = "EAAY2If1YdtgBP26wBQtKhug0SzeXl3ZC7oPvslxPJf2WcwPv97rNdcrZBU76aHC2uj1dOdzYiaj7UakzVjtXgMk6FPyjIxYIE9HP4jnAJDBZBdjT77al0sobv3sTlZCzKyO6JDqkQIFl2ztjjw00CZBVLtZAsYR2ElajCmGy9UFjDn3uVwz35E1rKKuIQ7CEMme4vgDMZCiwfOzVvVDMnyRJh15GwxIQIPRzgjXgypYzfO2FRIxlZCaETtKb6QZDZD"

print(f"🔍 Buscando Instagram Business Account para Page ID: {page_id}")
print()

# Intentar con diferentes versiones de la API
versions = ["v18.0", "v19.0", "v20.0", "v21.0"]

for version in versions:
    print(f"📡 Probando con API {version}...")
    url = f"https://graph.facebook.com/{version}/{page_id}?fields=instagram_business_account&access_token={access_token}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'instagram_business_account' in data:
            ig_id = data['instagram_business_account'].get('id')
            if ig_id:
                print(f"✅ ¡Encontrado!")
                print()
                print("=" * 60)
                print("📝 Añade estas líneas a tu .env:")
                print("=" * 60)
                print(f"FACEBOOK_PAGE_ID={page_id}")
                print(f"INSTAGRAM_BUSINESS_ACCOUNT_ID={ig_id}")
                print("=" * 60)
                exit(0)
            else:
                print(f"⚠️  Respuesta: {data}")
        else:
            print(f"⚠️  No hay instagram_business_account en la respuesta: {data}")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
    
    print()

print("❌ No se pudo obtener el Instagram Business Account ID")
print()
print("🔧 Opciones:")
print("1. Ve a Meta Business Suite: https://business.facebook.com/")
print("2. Selecciona tu página 'Winter Cycling Camp'")
print("3. Ve a Configuración → Cuentas de Instagram")
print("4. Busca el ID numérico de tu cuenta de Instagram")
