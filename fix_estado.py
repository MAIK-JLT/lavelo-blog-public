#!/usr/bin/env python3
import sys
sys.path.append('api')
import db_service

# Actualizar estado del post
db_service.update_post('20251104-2', {'estado': 'IMAGE_FORMATS_AWAITING'})
print('✅ Estado actualizado a IMAGE_FORMATS_AWAITING')
