# 🔐 Configuración de Hoja social_tokens en Google Sheets

## 📋 Instrucciones

### 1. Abrir Google Sheets
Abre tu hoja de cálculo "Lavelo Blog - Content Calendar":
https://docs.google.com/spreadsheets/d/1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug/edit

### 2. Crear Nueva Hoja
1. Click en el botón **"+"** en la parte inferior (junto a las pestañas)
2. Renombrar la nueva hoja a: **`social_tokens`**

### 3. Añadir Headers (Fila 1)
Copia estos headers en la fila 1:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| platform | access_token | refresh_token | expires_at | username | connected_at | last_used |

**Formato de headers:**
- Fondo: Gris oscuro (#434343)
- Texto: Blanco, negrita
- Alineación: Centrado

### 4. Configurar Columnas

**Anchos recomendados:**
- A (platform): 120px
- B (access_token): 400px
- C (refresh_token): 400px
- D (expires_at): 180px
- E (username): 150px
- F (connected_at): 180px
- G (last_used): 180px

### 5. Proteger la Hoja (Opcional pero Recomendado)

1. Click derecho en la pestaña **social_tokens**
2. Selecciona **"Proteger hoja"**
3. En el panel derecho:
   - Marca: **"Excepto ciertas celdas"**
   - Rango: `A2:G1000` (solo las filas de datos, no los headers)
4. Click **"Establecer permisos"**
5. Selecciona: **"Solo tú"**
6. Click **"Listo"**

Esto evita que se borren accidentalmente los headers.

### 6. Formato Condicional (Opcional)

Para visualizar mejor las fechas de expiración:

1. Selecciona rango: `D2:D100`
2. Menú: **Formato → Formato condicional**
3. Regla 1 (Tokens expirados):
   - Formato de celdas si: **La fecha es anterior a**
   - Valor: `HOY()`
   - Formato: Fondo rojo claro (#f4cccc)
4. Regla 2 (Tokens por expirar):
   - Formato de celdas si: **La fecha está entre**
   - Valores: `HOY()` y `HOY()+7`
   - Formato: Fondo amarillo claro (#fff2cc)
5. Regla 3 (Tokens válidos):
   - Formato de celdas si: **La fecha es posterior a**
   - Valor: `HOY()+7`
   - Formato: Fondo verde claro (#d9ead3)

### 7. Ejemplo de Datos

La hoja se llenará automáticamente cuando conectes las redes sociales, pero así se verá:

| platform | access_token | refresh_token | expires_at | username | connected_at | last_used |
|----------|--------------|---------------|------------|----------|--------------|-----------|
| instagram | gAAAAABm... | gAAAAABm... | 2025-12-31T23:59:59 | @lavelo_triathlon | 2025-10-31T12:00:00 | 2025-11-01T09:30:00 |
| linkedin | gAAAAABm... | gAAAAABm... | 2025-11-30T23:59:59 | Lavelo Blog | 2025-10-31T12:05:00 | |

**Nota:** Los tokens están encriptados con Fernet, por eso se ven como `gAAAAABm...`

---

## 🔑 Configurar Clave de Encriptación

### 1. Generar Clave

Ejecuta este comando en tu terminal:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Esto generará algo como:
```
xJ8vK2mN9pQ3rS6tU7wX0yZ1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV2wX3yZ4=
```

### 2. Añadir al .env

Abre el archivo `.env` y añade:

```bash
# Encriptación de tokens de redes sociales
ENCRYPTION_KEY=xJ8vK2mN9pQ3rS6tU7wX0yZ1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV2wX3yZ4=
```

**⚠️ IMPORTANTE:** 
- NO compartas esta clave con nadie
- NO la subas a Git (el .env ya está en .gitignore)
- Guárdala en un lugar seguro (1Password, LastPass, etc.)

---

## 🌐 Configurar Client IDs y Secrets de Redes Sociales

Para que OAuth funcione, necesitas crear apps en cada plataforma y obtener las credenciales.

### Instagram / Facebook

1. Ve a: https://developers.facebook.com/
2. Crea una nueva app
3. Añade producto: **Instagram Basic Display** o **Instagram Graph API**
4. Configura OAuth redirect URI: `http://localhost:5001/api/social/callback/instagram`
5. Copia Client ID y Client Secret
6. Añade al .env:

```bash
INSTAGRAM_CLIENT_ID=tu_client_id_aqui
INSTAGRAM_CLIENT_SECRET=tu_client_secret_aqui
```

### LinkedIn

1. Ve a: https://www.linkedin.com/developers/
2. Crea una nueva app
3. En **Auth** → **OAuth 2.0 settings**
4. Añade redirect URL: `http://localhost:5001/api/social/callback/linkedin`
5. Solicita permisos: `w_member_social`, `r_basicprofile`
6. Copia Client ID y Client Secret
7. Añade al .env:

```bash
LINKEDIN_CLIENT_ID=tu_client_id_aqui
LINKEDIN_CLIENT_SECRET=tu_client_secret_aqui
```

### Twitter / X

1. Ve a: https://developer.twitter.com/
2. Crea un proyecto y app
3. En **User authentication settings**
4. Tipo: **Web App**
5. Callback URL: `http://localhost:5001/api/social/callback/twitter`
6. Permisos: **Read and write**
7. Copia Client ID y Client Secret
8. Añade al .env:

```bash
TWITTER_CLIENT_ID=tu_client_id_aqui
TWITTER_CLIENT_SECRET=tu_client_secret_aqui
```

### Facebook Pages

1. Misma app que Instagram
2. Añade producto: **Facebook Login**
3. Configura redirect URI: `http://localhost:5001/api/social/callback/facebook`
4. Añade al .env:

```bash
FACEBOOK_CLIENT_ID=tu_client_id_aqui
FACEBOOK_CLIENT_SECRET=tu_client_secret_aqui
```

### TikTok

1. Ve a: https://developers.tiktok.com/
2. Crea una app
3. Solicita permisos: `video.upload`, `user.info.basic`
4. Callback URL: `http://localhost:5001/api/social/callback/tiktok`
5. Añade al .env:

```bash
TIKTOK_CLIENT_ID=tu_client_id_aqui
TIKTOK_CLIENT_SECRET=tu_client_secret_aqui
```

---

## ✅ Verificar Configuración

### 1. Instalar Dependencias

```bash
cd ~/lavelo-blog/api
pip install -r requirements.txt
```

### 2. Iniciar Servidor

```bash
python server.py
```

### 3. Abrir Panel de Conexiones

Navega a: http://localhost:5001/panel/publish.html?codigo=YYYYMMDD-N

Deberías ver las 5 redes sociales con estado "❌ No conectado"

### 4. Probar Conexión

1. Click en **"🔗 Conectar Instagram"**
2. Si todo está bien configurado, te redirigirá a Instagram OAuth
3. Autoriza la app
4. Volverás al panel con estado "✅ Conectado"
5. Verifica en Google Sheets que se creó una fila en `social_tokens`

---

## 🐛 Troubleshooting

### Error: "ENCRYPTION_KEY no configurada"
- Genera una clave nueva y añádela al .env

### Error: "Client ID no configurado"
- Verifica que las credenciales estén en el .env
- Reinicia el servidor Flask

### Error: "Estado OAuth inválido"
- Limpia cookies del navegador
- Intenta de nuevo

### Error: "Token exchange failed"
- Verifica que el Client Secret sea correcto
- Verifica que la redirect URI coincida exactamente

### La hoja social_tokens no existe
- Crea la hoja manualmente siguiendo las instrucciones arriba
- Asegúrate de que se llame exactamente `social_tokens` (minúsculas, con guión bajo)

---

## 📝 Notas de Seguridad

1. **Tokens encriptados:** Los access_token y refresh_token se guardan encriptados con Fernet
2. **HTTPS en producción:** En producción, usa HTTPS para OAuth (no HTTP)
3. **Permisos mínimos:** Solo solicita los permisos necesarios en cada plataforma
4. **Rotación de tokens:** Los tokens se renuevan automáticamente antes de expirar
5. **Backup de .env:** Guarda una copia segura del .env (sin subir a Git)

---

## 🎯 Siguiente Paso

Una vez configurado todo:

1. ✅ Hoja `social_tokens` creada
2. ✅ `ENCRYPTION_KEY` en .env
3. ✅ Client IDs y Secrets configurados
4. ✅ Dependencias instaladas
5. ✅ Servidor corriendo

**Puedes empezar a conectar tus redes sociales!** 🚀

Abre: http://localhost:5001/panel/publish.html?codigo=YYYYMMDD-N
