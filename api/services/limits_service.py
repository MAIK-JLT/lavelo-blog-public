"""
Servicio de verificación de límites por tier de usuario
Usado por: Endpoints de creación y publicación
"""
from datetime import datetime, date
from typing import Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import SessionLocal
from db_models import User, AnonymousUsage

class LimitsService:
    """Servicio para verificar límites de uso"""
    
    # Límites por tier
    LIMITS = {
        'anonymous': {
            'create_per_day': 10,
            'publish_total': 0  # No pueden publicar
        },
        'free': {
            'create_per_day': 10,
            'publish_total': 20  # Máximo 20 posts publicados en total
        },
        'premium': {
            'create_per_day': None,  # Ilimitado
            'publish_total': None    # Ilimitado
        }
    }
    
    def check_create_limit(self, user_id: Optional[int] = None, client_ip: Optional[str] = None) -> Dict:
        """
        Verifica si el usuario puede crear un post
        
        Args:
            user_id: ID del usuario (si está logueado)
            client_ip: IP del cliente (si es anónimo)
            
        Returns:
            Dict con 'allowed' (bool) y 'message' (str)
        """
        db = SessionLocal()
        try:
            # Usuario anónimo (por IP)
            if not user_id and client_ip:
                return self._check_anonymous_create(db, client_ip)
            
            # Usuario registrado
            elif user_id:
                return self._check_user_create(db, user_id)
            
            # Sin identificación
            else:
                return {
                    'allowed': False,
                    'message': '❌ No se pudo identificar al usuario'
                }
        finally:
            db.close()
    
    def check_publish_limit(self, user_id: int) -> Dict:
        """
        Verifica si el usuario puede publicar un post
        Solo usuarios registrados pueden publicar
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con 'allowed' (bool) y 'message' (str)
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    'allowed': False,
                    'message': '❌ Usuario no encontrado'
                }
            
            # Premium: ilimitado
            if user.tier == 'premium':
                return {
                    'allowed': True,
                    'message': '✅ Usuario premium - sin límites'
                }
            
            # Free: máximo 20 publicaciones totales
            if user.tier == 'free':
                if user.posts_published_total >= self.LIMITS['free']['publish_total']:
                    return {
                        'allowed': False,
                        'message': f'❌ Límite de {self.LIMITS["free"]["publish_total"]} publicaciones alcanzado. Actualiza a Premium por €19/mes para publicaciones ilimitadas.',
                        'upgrade_required': True
                    }
                
                return {
                    'allowed': True,
                    'message': f'✅ Publicación {user.posts_published_total + 1}/{self.LIMITS["free"]["publish_total"]}'
                }
            
            return {
                'allowed': False,
                'message': '❌ Tier de usuario no reconocido'
            }
            
        finally:
            db.close()
    
    def increment_publish_count(self, user_id: int):
        """Incrementa el contador de publicaciones del usuario"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.posts_published_total += 1
                db.commit()
        finally:
            db.close()
    
    def _check_anonymous_create(self, db, client_ip: str) -> Dict:
        """Verifica límite de creación para usuario anónimo"""
        today = date.today()
        
        # Buscar registro de esta IP
        usage = db.query(AnonymousUsage).filter(
            AnonymousUsage.ip_address == client_ip
        ).first()
        
        if not usage:
            # Primera vez que usa el servicio
            usage = AnonymousUsage(
                ip_address=client_ip,
                posts_created_today=0,
                last_post_date=today
            )
            db.add(usage)
            db.commit()
        
        # Resetear contador si es un nuevo día
        if usage.last_post_date != today:
            usage.posts_created_today = 0
            usage.last_post_date = today
            db.commit()
        
        # Verificar límite
        limit = self.LIMITS['anonymous']['create_per_day']
        
        if usage.posts_created_today >= limit:
            return {
                'allowed': False,
                'message': f'❌ Límite de {limit} posts por día alcanzado. Inicia sesión para crear más: http://localhost:5001/login.html',
                'login_required': True
            }
        
        # Incrementar contador
        usage.posts_created_today += 1
        db.commit()
        
        return {
            'allowed': True,
            'message': f'✅ Post {usage.posts_created_today}/{limit} hoy'
        }
    
    def _check_user_create(self, db, user_id: int) -> Dict:
        """Verifica límite de creación para usuario registrado"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                'allowed': False,
                'message': '❌ Usuario no encontrado'
            }
        
        # Premium: sin límites
        if user.tier == 'premium':
            return {
                'allowed': True,
                'message': '✅ Usuario premium - sin límites de creación'
            }
        
        # Free: mismo límite que anónimo (10/día)
        # Usar tabla AnonymousUsage con user_id como identificador
        today = date.today()
        ip_key = f"user_{user_id}"
        
        usage = db.query(AnonymousUsage).filter(
            AnonymousUsage.ip_address == ip_key
        ).first()
        
        if not usage:
            usage = AnonymousUsage(
                ip_address=ip_key,
                posts_created_today=0,
                last_post_date=today
            )
            db.add(usage)
            db.commit()
        
        # Resetear si es nuevo día
        if usage.last_post_date != today:
            usage.posts_created_today = 0
            usage.last_post_date = today
            db.commit()
        
        # Verificar límite
        limit = self.LIMITS['free']['create_per_day']
        
        if usage.posts_created_today >= limit:
            return {
                'allowed': False,
                'message': f'❌ Límite de {limit} posts por día alcanzado. Actualiza a Premium por €19/mes para creación ilimitada.',
                'upgrade_required': True
            }
        
        # Incrementar contador
        usage.posts_created_today += 1
        db.commit()
        
        return {
            'allowed': True,
            'message': f'✅ Post {usage.posts_created_today}/{limit} hoy'
        }

# Instancia global
limits_service = LimitsService()
