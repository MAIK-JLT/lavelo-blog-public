// Estado global
let currentPost = null;
let hasChanges = false;

// Obtener parámetros de URL
const urlParams = new URLSearchParams(window.location.search);
const codigo = urlParams.get('codigo');

// Cargar post al iniciar
document.addEventListener('DOMContentLoaded', () => {
    if (!codigo) {
        showError('No se especificó un código de post');
        return;
    }
    cargarPost();
});

// Cargar datos del post
async function cargarPost() {
    try {
        const response = await fetch('/api/posts');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error('Error al cargar posts');
        }
        
        currentPost = data.posts.find(p => p.codigo === codigo);
        
        if (!currentPost) {
            throw new Error('Post no encontrado');
        }
        
        // Actualizar header
        document.getElementById('post-title').textContent = currentPost.titulo;
        document.getElementById('post-codigo').textContent = currentPost.codigo;
        
        const estadoBadge = document.getElementById('post-estado');
        estadoBadge.textContent = currentPost.estado;
        estadoBadge.className = 'status-badge status-awaiting';
        
        // Cargar contenido según fase
        await cargarContenidoFase();
        
    } catch (error) {
        showError(error.message);
    }
}

// Cargar contenido según la fase actual
async function cargarContenidoFase() {
    const estado = currentPost.estado;
    const phaseContent = document.getElementById('phase-content');
    
    try {
        switch (estado) {
            case 'BASE_TEXT_AWAITING':
                await renderBaseTextPhase();
                break;
            case 'ADAPTED_TEXTS_AWAITING':
                await renderAdaptedTextsPhase();
                break;
            case 'IMAGE_PROMPT_AWAITING':
                await renderImagePromptPhase();
                break;
            case 'IMAGE_BASE_AWAITING':
                await renderImageBasePhase();
                break;
            case 'IMAGE_FORMATS_AWAITING':
                await renderImageFormatsPhase();
                break;
            case 'VIDEO_PROMPT_AWAITING':
                await renderVideoPromptPhase();
                break;
            case 'VIDEO_BASE_AWAITING':
                await renderVideoBasePhase();
                break;
            case 'VIDEO_FORMATS_AWAITING':
                await renderVideoFormatsPhase();
                break;
            case 'READY_TO_PUBLISH':
                await renderReadyToPublishPhase();
                break;
            default:
                phaseContent.innerHTML = '<p>Estado no reconocido</p>';
        }
    } catch (error) {
        showError('Error cargando contenido: ' + error.message);
    }
}

// FASE 1: BASE_TEXT_AWAITING
async function renderBaseTextPhase() {
    const phaseContent = document.getElementById('phase-content');
    
    // Leer archivo base.txt de Drive
    const baseText = await fetchFileFromDrive('textos', `${codigo}_base.txt`);
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">📝 Texto Base</h2>
            <p>Edita el texto base del post. Este texto será la base para generar las adaptaciones para cada red social.</p>
            <textarea id="base-text-editor" class="content-editor">${baseText || ''}</textarea>
        </div>
    `;
    
    // Detectar cambios
    document.getElementById('base-text-editor').addEventListener('input', () => {
        hasChanges = true;
        document.getElementById('save-btn').style.display = 'inline-block';
    });
    
    // Mostrar botón validar si hay contenido
    if (baseText) {
        document.getElementById('validate-btn').style.display = 'inline-block';
    }
}

// Obtener archivo de Drive
async function fetchFileFromDrive(folder, filename) {
    try {
        const response = await fetch(`/api/drive/file?codigo=${codigo}&folder=${folder}&filename=${filename}`);
        if (!response.ok) return null;
        const data = await response.json();
        return data.content;
    } catch (error) {
        console.error('Error fetching file:', error);
        return null;
    }
}

// Guardar cambios
async function guardarCambios() {
    const estado = currentPost.estado;
    
    try {
        showLoading('Guardando cambios...');
        
        switch (estado) {
            case 'BASE_TEXT_AWAITING':
                await guardarBaseText();
                break;
            // Agregar más casos según fase
        }
        
        hasChanges = false;
        document.getElementById('save-btn').style.display = 'none';
        showSuccess('Cambios guardados correctamente');
        
    } catch (error) {
        showError('Error guardando cambios: ' + error.message);
    }
}

// Guardar texto base
async function guardarBaseText() {
    const content = document.getElementById('base-text-editor').value;
    
    const response = await fetch('/api/drive/save-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            codigo: codigo,
            folder: 'textos',
            filename: `${codigo}_base.txt`,
            content: content
        })
    });
    
    if (!response.ok) {
        throw new Error('Error guardando archivo');
    }
}

// Validar y continuar
async function validar() {
    if (hasChanges) {
        if (!confirm('Tienes cambios sin guardar. ¿Deseas guardarlos antes de validar?')) {
            return;
        }
        await guardarCambios();
    }
    
    try {
        showLoading('Validando fase...');
        
        const response = await fetch('/api/validate-phase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo: codigo })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Error en validación');
        }
        
        showSuccess('Fase validada correctamente. Redirigiendo...');
        setTimeout(() => {
            window.location.href = '/';
        }, 1500);
        
    } catch (error) {
        showError('Error en validación: ' + error.message);
    }
}

// Cancelar y volver
function cancelar() {
    if (hasChanges) {
        if (!confirm('Tienes cambios sin guardar. ¿Seguro que deseas salir?')) {
            return;
        }
    }
    window.location.href = '/';
}

// Utilidades UI
function showError(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="error">${message}</div>`;
    setTimeout(() => container.innerHTML = '', 5000);
}

function showSuccess(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="success">${message}</div>`;
    setTimeout(() => container.innerHTML = '', 3000);
}

function showLoading(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="loading">${message}</div>`;
}
