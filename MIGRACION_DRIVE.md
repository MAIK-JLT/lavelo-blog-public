# 🔄 Migración: Google Drive + Sheets → BD Local + Storage

## ✅ Ventaja: Usa Tu Conexión Existente

**Ya tienes Google configurado**, el script usa tu `config/token.json` existente.

## 📋 Preparación

### 1️⃣ Verificar Conexión Existente

```bash
# Verifica que existe el token
ls -la /Users/julioizquierdo/lavelo-blog/api/config/token.json
```

**Si existe** → ✅ Listo para migrar
**Si NO existe** → Abre el panel web primero para autenticarte

### 2️⃣ Obtener IDs de Google

#### **Google Sheet ID:**
```
URL: https://docs.google.com/spreadsheets/d/1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug/edit
                                           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           Este es el SPREADSHEET_ID
```

#### **Google Drive Folder ID:**
```
URL: https://drive.google.com/drive/folders/1AbC123XyZ456
                                             ↑↑↑↑↑↑↑↑↑↑↑↑
                                             Este es el FOLDER_ID
```

### 3️⃣ Configurar .env

Agrega en `/Users/julioizquierdo/lavelo-blog/.env`:

```bash
# IDs para migración (ya deberías tener GOOGLE_SHEETS_ID)
GOOGLE_SHEETS_ID=1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug
GOOGLE_DRIVE_FOLDER_ID=tu_folder_id_aqui
```

**Nota:** `GOOGLE_SHEETS_ID` probablemente ya existe en tu `.env`

---

## 🚀 Ejecutar Migración

### Opción 1: Migración Completa (Sheets + Drive)

```bash
cd /Users/julioizquierdo/lavelo-blog/api
python3 migrate_drive_to_local.py
```

**Esto hará:**
1. ✅ Leer posts de Google Sheets → Crear en BD
2. ✅ Descargar archivos de Drive → Guardar en `/storage/posts/`

---

## 📊 Estructura del Google Sheet

**El script espera estas columnas (ajustar en código si es diferente):**

| A (codigo) | B (titulo) | C (categoria) | D (estado) | E (fecha) | F (hora) |
|------------|------------|---------------|------------|-----------|----------|
| 20251105-1 | Post 1     | Entrenamiento | DRAFT      | 2025-11-10| 10:00    |
| 20251105-2 | Post 2     | Nutrición     | PUBLISHED  | 2025-11-11| 14:00    |

**Si tu sheet tiene columnas diferentes:**
1. Abre `migrate_drive_to_local.py`
2. Busca línea ~120: `codigo = row[0]`
3. Ajusta índices según tu sheet

---

## 📁 Estructura de Drive

**El script espera:**

```
📁 Posts (FOLDER_ID)
  ├── 📁 20251105-1/
  │   ├── 📁 textos/
  │   │   ├── 20251105-1_base.txt
  │   │   ├── 20251105-1_instagram.txt
  │   │   └── ...
  │   ├── 📁 imagenes/
  │   │   ├── 20251105-1_imagen_base.png
  │   │   └── ...
  │   └── 📁 videos/
  │       └── ...
  └── 📁 20251105-2/
      └── ...
```

---

## ✅ Verificar Migración

### 1. Verificar BD:

```bash
cd /Users/julioizquierdo/lavelo-blog/api
python3
```

```python
from database import SessionLocal
from db_models import Post

db = SessionLocal()
posts = db.query(Post).all()

print(f"📊 Posts en BD: {len(posts)}")
for p in posts:
    print(f"  - {p.codigo}: {p.titulo} ({p.estado})")
```

### 2. Verificar Storage:

```bash
ls -la /Users/julioizquierdo/lavelo-blog/storage/posts/
```

**Deberías ver:**
```
20251105-1/
20251105-2/
...
```

### 3. Verificar Panel:

```bash
# Abre navegador
http://localhost:5001/panel/
```

**Deberías ver todos los posts migrados** ✅

---

## 🐛 Troubleshooting

### Error: "No such file credentials.json"
```bash
# Verifica que existe
ls -la /Users/julioizquierdo/lavelo-blog/config/credentials.json

# Si no existe, descárgalo de Google Cloud Console
```

### Error: "Permission denied"
```bash
# Comparte Sheet y Drive con el email del service account
# Email está en credentials.json → "client_email"
```

### Error: "No se encontraron datos en el sheet"
```bash
# Verifica el nombre de la pestaña
# Por defecto busca "Posts!A2:Z1000"
# Ajusta en migrate_drive_to_local.py línea ~95
```

### Posts duplicados:
```bash
# El script salta posts que ya existen
# Si quieres re-migrar, borra la BD primero:
cd api
rm lavelo_blog.db
python3 create_tables.py
python3 migrate_drive_to_local.py
```

---

## 📝 Notas

- **Tiempo estimado:** 5-10 min (depende de cantidad de archivos)
- **Archivos grandes:** Videos pueden tardar más
- **Re-ejecución:** Es segura, no duplica posts existentes
- **Backup:** Haz backup de Drive antes de migrar

---

## 🎯 Después de Migrar

1. **Verifica que todo está OK** en el panel
2. **Puedes seguir usando Drive** (el script solo lee, no borra)
3. **O desconectar Drive** y usar solo storage local
4. **Actualiza .env** para producción si es necesario

---

**¡Listo para migrar!** 🚀
