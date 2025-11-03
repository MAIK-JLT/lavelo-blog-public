#!/usr/bin/env python3
"""
Script para exportar datos de Google Sheets a JSON
Ejecutar en LOCAL (Mac) donde tienes acceso a Google Sheets
"""
import json
from sheets_service import get_all_posts, get_social_tokens

def export_to_json():
    """Exporta posts y tokens a archivos JSON"""
    print("📊 Exportando datos de Google Sheets...")
    
    # Exportar posts
    posts = get_all_posts()
    with open('posts_export.json', 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"✅ Exportados {len(posts)} posts a posts_export.json")
    
    # Exportar tokens
    try:
        tokens = get_social_tokens()
        with open('tokens_export.json', 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
        print(f"✅ Exportados {len(tokens)} tokens a tokens_export.json")
    except Exception as e:
        print(f"⚠️  No se pudieron exportar tokens: {e}")
    
    print("\n🎉 Exportación completada")
    print("📁 Archivos creados:")
    print("   - posts_export.json")
    print("   - tokens_export.json")
    print("\n📤 Sube estos archivos al servidor para importarlos a MySQL")

if __name__ == "__main__":
    export_to_json()
