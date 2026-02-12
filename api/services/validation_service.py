"""
Servicio de validación de fases
Usado por: Panel Web, API REST
"""
from typing import Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.content_service import content_service
from services.image_service import image_service
from services.video_service import video_service

class ValidationService:
    """Servicio para validar fases del workflow"""
    
    def __init__(self):
        self.content_service = content_service
        self.image_service = image_service
        self.video_service = video_service
    
    async def validate_phase(self, codigo: str, current_state: str, redes: Dict[str, bool] = None, user_id: int = None) -> Dict:
        """
        Valida una fase y ejecuta la acción correspondiente
        
        Usado por:
        - Panel Web: Botón "VALIDATE"
        - API: POST /api/validate-phase
        """
        if redes is None:
            redes = {}
        
        if user_id:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

        # Guardar configuración de redes en BD
        print(f"📱 Redes seleccionadas: {redes}")
        for network, active in redes.items():
            field_name = f'redes_{network}'
            db_service.update_post(codigo, {field_name: active}, user_id=user_id)
        
        # Máquina de estados: definir transiciones
        state_transitions = {
            'BASE_TEXT_AWAITING': {
                'next': 'ADAPTED_TEXTS_AWAITING',
                'action': 'generate_adapted_texts',
                'description': 'Generar textos adaptados'
            },
            # Permitir re-generar textos si ya estamos en esa fase
            'ADAPTED_TEXTS_AWAITING': {
                'next': 'IMAGE_PROMPT_AWAITING',
                'action': 'generate_image_prompt', # Por defecto avanza
                'description': 'Generar prompt de imagen'
            },
            'IMAGE_PROMPT_AWAITING': {
                'next': 'IMAGE_BASE_AWAITING',
                'action': 'generate_image',
                'description': 'Generar imagen base'
            },
            'IMAGE_BASE_AWAITING': {
                'next': 'IMAGE_FORMATS_AWAITING',
                'action': 'format_images',
                'description': 'Generar formatos de imagen'
            },
            'IMAGE_FORMATS_AWAITING': {
                'next': 'VIDEO_PROMPT_AWAITING',
                'action': 'generate_video_script',
                'description': 'Generar script de video'
            },
            'VIDEO_PROMPT_AWAITING': {
                'next': 'VIDEO_BASE_AWAITING',
                'action': 'generate_video_base',
                'description': 'Generar video base'
            },
            'VIDEO_BASE_AWAITING': {
                'next': 'VIDEO_FORMATS_AWAITING',
                'action': 'format_videos',
                'description': 'Generar formatos de video'
            },
            'VIDEO_FORMATS_AWAITING': {
                'next': 'READY_TO_PUBLISH',
                'action': 'mark_ready',
                'description': 'Marcar como listo para publicar'
            },
            'READY_TO_PUBLISH': {
                'next': 'PUBLISHED',
                'action': 'publish',
                'description': 'Publicar en redes'
            }
        }
        
        if current_state == 'ADAPTED_TEXTS_AWAITING' and redes:
             # Si estamos en ADAPTED y enviamos redes, es que queremos RE-GENERAR
             print(f"🔄 Re-generando textos para: {codigo}")
             transition = {
                'next': 'ADAPTED_TEXTS_AWAITING', # Nos quedamos en el mismo estado
                'action': 'generate_adapted_texts',
                'description': 'Re-generar textos adaptados'
             }
        else:
            transition = state_transitions.get(current_state)
            
        if not transition:
            raise Exception(f'Estado {current_state} no reconocido')
        
        print(f"🔧 Validando fase: {current_state} → {transition['next']}")
        print(f"📝 Acción: {transition['description']}")
        
        # Ejecutar acción correspondiente
        action_result = {}
        
        if transition['action'] == 'generate_adapted_texts':
            action_result = await self.content_service.generate_adapted_texts(codigo, redes, user_id=user_id)
        
        elif transition['action'] == 'generate_image_prompt':
            action_result = await self.content_service.generate_image_prompt(codigo, user_id=user_id)
        
        elif transition['action'] == 'generate_image':
            # Fase 3: Generar 2 variaciones base
            action_result = await self.image_service.generate_image(codigo, num_images=2, user_id=user_id)
        
        elif transition['action'] == 'format_images':
            action_result = await self.image_service.format_images(codigo, user_id=user_id)
        
        elif transition['action'] == 'generate_video_script':
            action_result = await self.content_service.generate_video_script(codigo, user_id=user_id)
        
        elif transition['action'] == 'generate_video_base':
            action_result = await self.video_service.generate_video_base(codigo, user_id=user_id)
        
        elif transition['action'] == 'format_videos':
            action_result = await self.video_service.format_videos(codigo, user_id=user_id)
        
        elif transition['action'] == 'mark_ready':
            # Solo actualizar estado
            action_result = {'success': True, 'message': 'Listo para publicar'}
        
        elif transition['action'] == 'publish':
            # TODO: Implementar publicación
            action_result = {'success': True, 'message': 'Publicación pendiente de implementar'}
        
        # Actualizar estado en BD
        db_service.update_post(codigo, {'estado': transition['next']}, user_id=user_id)
        
        return {
            'success': True,
            'previous_state': current_state,
            'new_state': transition['next'],
            'action': transition['description'],
            'action_result': action_result,
            'message': f"✅ Fase validada: {current_state} → {transition['next']}"
        }
    
    async def reset_dependent_phases(self, codigo: str, edited_phase: int, user_id: int = None) -> Dict:
        """
        Resetea fases dependientes cuando se edita una fase validada
        
        Usado por:
        - Panel Web: Al guardar cambios en fase validada
        """
        # Mapeo de dependencias
        phase_dependencies = {
            1: [2, 3, 4, 5, 6, 7, 8],  # BASE_TEXT resetea todas
            2: [3, 4, 5, 6, 7, 8],      # ADAPTED_TEXTS resetea desde IMAGE_PROMPT
            3: [4, 5, 6, 7, 8],         # IMAGE_PROMPT resetea desde IMAGE_BASE
            4: [5, 6, 7, 8],            # IMAGE_BASE resetea desde IMAGE_FORMATS
            5: [6, 7, 8],               # IMAGE_FORMATS resetea desde VIDEO_PROMPT
            6: [7, 8],                  # VIDEO_PROMPT resetea desde VIDEO_BASE
            7: [8],                     # VIDEO_BASE resetea VIDEO_FORMATS
            8: []                       # VIDEO_FORMATS no resetea nada
        }
        
        if user_id:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

        phases_to_reset = phase_dependencies.get(edited_phase, [])
        
        # TODO: Implementar reseteo de checkboxes según fase
        
        return {
            'success': True,
            'edited_phase': edited_phase,
            'reset_phases': phases_to_reset,
            'message': f'✅ {len(phases_to_reset)} fases reseteadas'
        }

# Instancia global
validation_service = ValidationService()
