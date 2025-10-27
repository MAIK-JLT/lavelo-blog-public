#!/usr/bin/env python3
import json
from sheets_service import sheets_service

codigo = '20251024-1'

# Obtener post
posts = sheets_service.get_posts()
post = next((p for p in posts if p['codigo'] == codigo), None)

if post:
    folder_id = post['drive_folder_id']
    textos_folder_id = sheets_service.get_subfolder_id(folder_id, 'textos')
    
    # Leer metadata actual
    metadata_text = sheets_service.get_file_from_drive(textos_folder_id, f'{codigo}_referencias_metadata.json')
    metadata = json.loads(metadata_text)
    
    # Actualizar URLs a formato thumbnail
    for ref in metadata['references']:
        file_id = ref['file_id']
        ref['drive_url'] = f'https://drive.google.com/thumbnail?id={file_id}&sz=w400'
        print(f"✅ Actualizada URL para {ref['filename']}: {ref['drive_url']}")
    
    # Guardar metadata actualizado
    sheets_service.save_file_to_drive(textos_folder_id, f'{codigo}_referencias_metadata.json', json.dumps(metadata, indent=2))
    print('✅ Metadata guardado correctamente')
else:
    print('❌ Post no encontrado')
