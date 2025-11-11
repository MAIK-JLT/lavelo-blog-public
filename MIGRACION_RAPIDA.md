# ⚡ Migración Rápida - 3 Pasos

## ✅ Ventaja: Usa Tu Conexión Existente

**NO necesitas configurar Google de nuevo.** El script usa tu `config/token.json` existente.

---

## 🚀 Pasos:

### 1️⃣ Obtener ID de Carpeta Drive..

1. **Abre:** https://drive.google.com/
2. **Navega** a tu carpeta "Posts" o "Lavelo Blog Content"
3. **Copia el ID** de la URL:
   ```
   https://drive.google.com/drive/folders/1AbC123XyZ456
                                            ↑↑↑↑↑↑↑↑↑↑↑↑
                                            Copia esto
   ```

### 2️⃣ Agregar a .env

Edita `/Users/julioizquierdo/lavelo-blog/.env`:

```bash
# Agregar esta línea (GOOGLE_SHEETS_ID ya debería existir)
GOOGLE_DRIVE_FOLDER_ID=tu_folder_id_aqui
```

### 3️⃣ Ejecutar Migración

```bash
cd /Users/julioizquierdo/lavelo-blog/api
python3 migrate_drive_to_local.py
```

---

## 📊 Qué Hace:

1. **Lee Google Sheets** → Crea posts en BD MySQL/SQLite
2. **Descarga archivos de Drive** → Guarda en `/storage/posts/`
3. **Mantiene estructura** (textos, imagenes, videos)

---

## ✅ Verificar:

```bash
# Ver posts en BD
cd api
python3
```

```python
from database import SessionLocal
from db_models import Post

db = SessionLocal()
posts = db.query(Post).all()
print(f"Posts migrados: {len(posts)}")
```

```bash
# Ver archivos en storage
ls -la ../storage/posts/
```

---

## 🎯 Después:

1. **Abre el panel:** http://localhost:5001/panel/
2. **Deberías ver todos los posts** ✅
3. **Archivos accesibles** desde `/storage/posts/`

---

**¡Listo en 3 pasos!** 🎉
