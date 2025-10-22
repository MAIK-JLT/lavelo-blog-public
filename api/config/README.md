# Configuración de Credenciales

## Archivos Requeridos

Este directorio debe contener los siguientes archivos (NO incluidos en Git por seguridad):

### 1. `credentials.json`
Credenciales de OAuth 2.0 de Google Cloud Console.

**Cómo obtenerlo:**
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita las APIs:
   - Google Sheets API
   - Google Drive API
4. Ve a "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth 2.0"
5. Tipo de aplicación: "Aplicación de escritorio"
6. Descarga el JSON y renómbralo a `credentials.json`

**Copia `credentials.json.example` y reemplaza con tus valores reales.**

### 2. `token.json`
Se genera automáticamente la primera vez que te autentiques.

**No necesitas crearlo manualmente.** El sistema lo generará cuando:
1. Inicies el servidor: `python server.py`
2. Visites: `http://localhost:5001/api/auth/login`
3. Autorices la aplicación con tu cuenta de Google

## Estructura Esperada

```
api/config/
├── credentials.json          # TUS credenciales (NO subir a Git)
├── credentials.json.example  # Plantilla de ejemplo
├── token.json               # Token de acceso (generado automáticamente)
└── README.md                # Este archivo
```

## ⚠️ Seguridad

**NUNCA** subas `credentials.json` o `token.json` a Git. Estos archivos están en `.gitignore`.

Si accidentalmente los subiste:
```bash
git rm --cached api/config/credentials.json api/config/token.json
git commit -m "Remove sensitive files"
```
