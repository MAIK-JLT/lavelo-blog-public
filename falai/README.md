# 🎨 Fal.ai SeaDream 4.0 - Test Environment

Entorno de pruebas aislado para validar la generación de imágenes con Fal.ai SeaDream 4.0.

## 📁 Estructura

```
falai/
├── index.html           # Frontend de prueba
├── test_results/        # Imágenes generadas (local)
│   └── test_YYYYMMDD_HHMMSS_N.png
└── README.md           # Este archivo
```

## 🚀 Cómo Usar

### 1. Asegúrate de que el servidor Flask esté corriendo

```bash
cd ~/lavelo-blog/api
python server.py
```

El servidor debe estar en `http://localhost:5001`

### 2. Abre el HTML de prueba

Navega a: `http://localhost:5001/falai/index.html`

### 3. Usa la interfaz

1. **Escribe un prompt** en el campo de texto
2. **Sube hasta 2 imágenes de referencia** (opcional)
3. **Click en "Generar 4 Variaciones"**
4. **Espera 30-60 segundos**
5. **Revisa los resultados** en pantalla y en `test_results/`

## 📝 Nomenclatura de Archivos

**Imágenes generadas:**
- Formato: `test_YYYYMMDD_HHMMSS_N.png`
- Ejemplo: `test_20251027_103045_1.png`
- Ubicación: `falai/test_results/`

Donde:
- `YYYYMMDD`: Fecha de generación
- `HHMMSS`: Hora de generación
- `N`: Número de variación (1-4)

## 🔧 Configuración

El endpoint usa:
- **API Key**: `FAL_KEY` del archivo `.env`
- **Modelo**: `fal-ai/bytedance/seedream/v4/text-to-image`
- **Parámetros fijos**:
  - `image_size`: square_hd (1024x1024)
  - `num_images`: 4
  - `num_inference_steps`: 28
  - `reference_weight`: 1.5 (fijo para pruebas)

## 🎯 Objetivo

Validar que:
1. ✅ Las referencias se envían correctamente
2. ✅ El peso de las referencias funciona
3. ✅ Los resultados son similares a la web de Fal.ai
4. ✅ El prompt genera imágenes esperadas

## 📊 Comparación

Usa este entorno para comparar:
- **Mismo prompt + mismas referencias** → ¿Mismos resultados que la web?
- **Diferentes pesos** → ¿Cómo afecta al resultado?
- **Con/sin referencias** → ¿Diferencia notable?

## 🐛 Debug

Los logs aparecen en:
1. **Consola del navegador** (F12 → Console)
2. **Terminal del servidor Flask**
3. **Panel de logs en el HTML**

## ⚠️ Notas

- Las imágenes se guardan **localmente** en `test_results/`
- **NO se suben a Google Drive**
- **NO afectan** al sistema principal
- Costo: **$0.03 por imagen** (4 imágenes = $0.12)
