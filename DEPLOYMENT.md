# Guía de Despliegue en Plesk (SSH)

A diferencia de PHP/Laravel, las aplicaciones Python (FastAPI/Flask) funcionan como procesos persistentes. Esto significa que **los cambios en el código NO se reflejan automáticamente**; debes reiniciar el proceso de la aplicación manualmente cada vez que subas cambios.

## 1. Conectarse por SSH

Accede a tu servidor:
```bash
ssh usuario@tu-servidor.com
cd /ruta/a/tu/proyecto
# Ejemplo: cd httpdocs/lavelo-blog
```

## 2. Descargar Cambios (Git)

Si tienes git configurado en el servidor:
```bash
git pull origin main
```

## 3. Instalar Dependencias (Si cambiaron)

Si has modificado `api/requirements.txt`, debes instalar las nuevas librerías.
Es importante usar el `pip` del entorno virtual de la aplicación. En Plesk, suele estar creado automáticamente.

```bash
# Activar entorno virtual (ruta típica en Plesk)
source venv/bin/activate

# Instalar dependencias
pip install -r api/requirements.txt
```

## 4. Reiniciar la Aplicación (IMPORTANTE)

Para que Python cargue el nuevo código, debes decirle a **Passenger** (el gestor de aplicaciones de Plesk) que reinicie.
Esto se hace simplemente "tocando" un archivo especial:

```bash
# Comando para reiniciar la app
touch tmp/restart.txt
```

*Si la carpeta `tmp` no existe, créala primero:* `
mkdir -p tmp
touch tmp/restart.txt
`

## 5. Archivos Estáticos (JS/CSS)

Los cambios en `panel/`, `css/` o `js/` se sirven como archivos.
Si no los ves actualizados en el navegador:
1. Asegúrate de haber reiniciado la app (paso 4).
2. **Limpia la caché de tu navegador**:
   * Windows/Linux: `Ctrl + Shift + R`
   * Mac: `Cmd + Shift + R`

## Resumen Rápido (One-Liner)

Puedes ejecutar todo en una línea después de hacer el git pull:

```bash
mkdir -p tmp && touch tmp/restart.txt
```
