// Estado global
let currentPost = null;

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
            <p style="color: #666; margin-bottom: 20px;">Edita el texto base del post. Este texto será la base para generar las adaptaciones para cada red social.</p>
            <div class="text-item">
                <h3>📄 Texto Base</h3>
                <textarea id="base-text-editor" class="content-editor" data-original="${escapeHtml(baseText || '')}">${baseText || ''}</textarea>
                <div class="save-btn-container">
                    <button class="save-btn" id="save-base" onclick="guardarTextoIndividual('base', 'base-text-editor')">💾 Guardar</button>
                    <span class="save-status" id="status-base">✅ Guardado</span>
                </div>
            </div>
        </div>
    `;
    
    // Detectar cambios
    setupTextEditor('base-text-editor', 'save-base', 'status-base');
}

// FASE 2: ADAPTED_TEXTS_AWAITING
async function renderAdaptedTextsPhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando textos adaptados...</p></div>';
    
    const redes = [
        { id: 'instagram', nombre: 'Instagram', icono: '📸' },
        { id: 'linkedin', nombre: 'LinkedIn', icono: '💼' },
        { id: 'twitter', nombre: 'Twitter/X', icono: '🐦' },
        { id: 'facebook', nombre: 'Facebook', icono: '👥' },
        { id: 'tiktok', nombre: 'TikTok', icono: '🎵' }
    ];
    
    const textos = {};
    for (const red of redes) {
        textos[red.id] = await fetchFileFromDrive('textos', `${codigo}_${red.id}.txt`);
    }
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">📱 Textos Adaptados por Red Social</h2>
            <p style="color: #666; margin-bottom: 20px;">Edita cada texto según la red social. Los cambios se guardan individualmente.</p>
            ${redes.map(red => `
                <div class="text-item">
                    <h3>${red.icono} ${red.nombre}</h3>
                    <textarea id="text-${red.id}" class="content-editor" data-original="${escapeHtml(textos[red.id] || '')}">${textos[red.id] || ''}</textarea>
                    <div class="save-btn-container">
                        <button class="save-btn" id="save-${red.id}" onclick="guardarTextoIndividual('${red.id}', 'text-${red.id}')">💾 Guardar ${red.nombre}</button>
                        <span class="save-status" id="status-${red.id}">✅ Guardado</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Configurar detectores de cambios para cada textarea
    redes.forEach(red => {
        setupTextEditor(`text-${red.id}`, `save-${red.id}`, `status-${red.id}`);
    });
}

// FASE 3: IMAGE_PROMPT_AWAITING
async function renderImagePromptPhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando prompt de imagen...</p></div>';
    
    const promptText = await fetchFileFromDrive('textos', `${codigo}_prompt_imagen.txt`);
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🎨 Prompt de Imagen</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa y edita el prompt que se usará para generar la imagen base. Debe ser descriptivo y en inglés.</p>
            <div class="text-item">
                <h3>📝 Prompt para Generación de Imagen</h3>
                <textarea id="prompt-editor" class="content-editor" data-original="${escapeHtml(promptText || '')}" style="min-height: 150px;">${promptText || ''}</textarea>
                <div class="save-btn-container">
                    <button class="save-btn" id="save-prompt_imagen" onclick="guardarTextoIndividual('prompt_imagen', 'prompt-editor')">💾 Guardar Prompt</button>
                    <span class="save-status" id="status-prompt_imagen">✅ Guardado</span>
                </div>
            </div>
        </div>
    `;
    
    setupTextEditor('prompt-editor', 'save-prompt_imagen', 'status-prompt_imagen');
}

// FASE 4: IMAGE_BASE_AWAITING
async function renderImageBasePhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando imagen base...</p></div>';
    
    // Construir URL de la imagen en Drive
    const imageUrl = `/api/drive/image?codigo=${codigo}&folder=imagenes&filename=${codigo}_imagen_base.png`;
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🖼️ Imagen Base Generada</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa la imagen generada. Si no te gusta, vuelve al panel principal y regenera desde la fase anterior.</p>
            <div class="text-item">
                <h3>📸 Imagen Base (1024x1024)</h3>
                <div style="text-align: center; padding: 20px;">
                    <img src="${imageUrl}" alt="Imagen base" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);" onerror="this.src=''; this.alt='Error cargando imagen';">
                </div>
                <p style="color: #666; font-size: 0.9em; text-align: center; margin-top: 10px;">Si la imagen es correcta, vuelve al panel y haz clic en VALIDATE para generar los formatos.</p>
            </div>
        </div>
    `;
}

// FASE 5: IMAGE_FORMATS_AWAITING
async function renderImageFormatsPhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando formatos de imagen...</p></div>';
    
    const formats = [
        { name: 'Instagram 1:1', filename: `${codigo}_instagram_1x1.png`, size: '1080x1080' },
        { name: 'Instagram Stories 9:16', filename: `${codigo}_instagram_stories_9x16.png`, size: '1080x1920' },
        { name: 'LinkedIn 16:9', filename: `${codigo}_linkedin_16x9.png`, size: '1200x627' },
        { name: 'Twitter 16:9', filename: `${codigo}_twitter_16x9.png`, size: '1200x675' },
        { name: 'Facebook 16:9', filename: `${codigo}_facebook_16x9.png`, size: '1200x630' }
    ];
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">📱 Formatos de Imagen Generados</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa todos los formatos generados para cada red social.</p>
            ${formats.map(format => `
                <div class="text-item">
                    <h3>🖼️ ${format.name} (${format.size})</h3>
                    <div id="img-container-${format.filename}" style="text-align: center; padding: 15px;">
                        <div class="spinner" style="margin: 20px auto;"></div>
                        <p style="color: #999;">Cargando imagen...</p>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Cargar imágenes secuencialmente para evitar problemas de SSL
    for (const format of formats) {
        await loadImageWithRetry(format.filename, `img-container-${format.filename}`, format.name);
        // Pequeña pausa entre cargas
        await new Promise(resolve => setTimeout(resolve, 300));
    }
}

// Función auxiliar para cargar imágenes con reintentos
async function loadImageWithRetry(filename, containerId, altText, maxRetries = 3) {
    const container = document.getElementById(containerId);
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const url = `/api/drive/image?codigo=${codigo}&folder=imagenes&filename=${filename}&t=${Date.now()}`;
            
            // Verificar que la imagen existe antes de mostrarla
            const response = await fetch(url);
            if (response.ok) {
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                container.innerHTML = `
                    <img src="${imageUrl}" 
                         alt="${altText}" 
                         style="max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.15);">
                `;
                return; // Éxito
            }
        } catch (error) {
            console.error(`Intento ${attempt} fallido para ${filename}:`, error);
            if (attempt === maxRetries) {
                container.innerHTML = `
                    <p style="color: #dc3545;">❌ Error cargando imagen</p>
                    <p style="color: #999; font-size: 0.9em;">Intenta recargar la página</p>
                `;
            } else {
                // Esperar antes de reintentar
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }
}

// FASE 6: VIDEO_PROMPT_AWAITING
async function renderVideoPromptPhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando script de video...</p></div>';
    
    const scriptText = await fetchFileFromDrive('textos', `${codigo}_script_video.txt`);
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🎬 Script de Video</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa y edita el script del video (4 escenas, 15 segundos total).</p>
            <div class="text-item">
                <h3>📝 Script para Video Base</h3>
                <textarea id="script-editor" class="content-editor" data-original="${escapeHtml(scriptText || '')}" style="min-height: 250px;">${scriptText || ''}</textarea>
                <div class="save-btn-container">
                    <button class="save-btn" id="save-script_video" onclick="guardarTextoIndividual('script_video', 'script-editor')">💾 Guardar Script</button>
                    <span class="save-status" id="status-script_video">✅ Guardado</span>
                </div>
            </div>
        </div>
    `;
    
    setupTextEditor('script-editor', 'save-script_video', 'status-script_video');
}

// FASE 7: VIDEO_BASE_AWAITING
async function renderVideoBasePhase() {
    const phaseContent = document.getElementById('phase-content');
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🎥 Video Base Generado</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa el video generado (16:9, 15 segundos).</p>
            <div class="text-item">
                <h3>🎬 Video Base</h3>
                <div style="text-align: center; padding: 20px;">
                    <video controls style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                        <source src="/api/drive/video?codigo=${codigo}&folder=videos&filename=${codigo}_video_base.mp4" type="video/mp4">
                        Tu navegador no soporta video.
                    </video>
                </div>
                <p style="color: #666; font-size: 0.9em; text-align: center; margin-top: 10px;">Si el video es correcto, vuelve al panel y haz clic en VALIDATE para generar los formatos.</p>
            </div>
        </div>
    `;
}

// FASE 8: VIDEO_FORMATS_AWAITING
async function renderVideoFormatsPhase() {
    const phaseContent = document.getElementById('phase-content');
    
    const formats = [
        { name: 'Feed 16:9', filename: `${codigo}_feed_16x9.mp4`, size: '1920x1080' },
        { name: 'Stories 9:16', filename: `${codigo}_stories_9x16.mp4`, size: '1080x1920' },
        { name: 'Shorts 9:16', filename: `${codigo}_shorts_9x16.mp4`, size: '1080x1920' },
        { name: 'TikTok 9:16', filename: `${codigo}_tiktok_9x16.mp4`, size: '1080x1920' }
    ];
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">📱 Formatos de Video Generados</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa todos los formatos de video para cada plataforma.</p>
            ${formats.map(format => `
                <div class="text-item">
                    <h3>🎥 ${format.name} (${format.size})</h3>
                    <div id="video-container-${format.filename}" style="text-align: center; padding: 15px;">
                        <div class="spinner" style="margin: 20px auto;"></div>
                        <p style="color: #999;">Cargando video...</p>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Cargar videos secuencialmente para evitar problemas de SSL
    for (const format of formats) {
        await loadVideoWithRetry(format.filename, `video-container-${format.filename}`, format.name);
        // Pausa más larga entre videos (son archivos más grandes)
        await new Promise(resolve => setTimeout(resolve, 500));
    }
}

// Función auxiliar para cargar videos con reintentos
async function loadVideoWithRetry(filename, containerId, altText, maxRetries = 3) {
    const container = document.getElementById(containerId);
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const url = `/api/drive/video?codigo=${codigo}&folder=videos&filename=${filename}&t=${Date.now()}`;
            
            // Verificar que el video existe antes de mostrarlo
            const response = await fetch(url);
            if (response.ok) {
                const blob = await response.blob();
                const videoUrl = URL.createObjectURL(blob);
                
                container.innerHTML = `
                    <video controls style="max-width: 100%; max-height: 500px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.15);">
                        <source src="${videoUrl}" type="video/mp4">
                        Tu navegador no soporta video.
                    </video>
                `;
                return; // Éxito
            }
        } catch (error) {
            console.error(`Intento ${attempt} fallido para ${filename}:`, error);
            if (attempt === maxRetries) {
                container.innerHTML = `
                    <p style="color: #dc3545;">❌ Error cargando video</p>
                    <p style="color: #999; font-size: 0.9em;">Intenta recargar la página</p>
                `;
            } else {
                // Esperar más tiempo antes de reintentar (videos son más pesados)
                await new Promise(resolve => setTimeout(resolve, 1500 * attempt));
            }
        }
    }
}

// FASE 9: READY_TO_PUBLISH
async function renderReadyToPublishPhase() {
    const phaseContent = document.getElementById('phase-content');
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🚀 Listo para Publicar</h2>
            <p style="color: #28a745; font-size: 1.2em; text-align: center; padding: 40px;">
                ✅ Todos los assets han sido generados y validados.<br><br>
                Vuelve al panel principal para programar la publicación.
            </p>
        </div>
    `;
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

// Configurar editor de texto con detección de cambios
function setupTextEditor(editorId, saveBtnId, statusId) {
    const editor = document.getElementById(editorId);
    const saveBtn = document.getElementById(saveBtnId);
    const status = document.getElementById(statusId);
    
    if (!editor) return;
    
    const originalValue = editor.dataset.original || '';
    
    editor.addEventListener('input', () => {
        const currentValue = editor.value;
        const hasChanged = currentValue !== originalValue;
        
        if (hasChanged) {
            editor.classList.add('modified');
            saveBtn.classList.add('show');
            status.classList.remove('show');
        } else {
            editor.classList.remove('modified');
            saveBtn.classList.remove('show');
            status.classList.add('show');
        }
    });
}

// Guardar texto individual
async function guardarTextoIndividual(tipo, editorId) {
    const editor = document.getElementById(editorId);
    const saveBtn = document.getElementById(`save-${tipo}`);
    const status = document.getElementById(`status-${tipo}`);
    
    try {
        saveBtn.disabled = true;
        saveBtn.textContent = '⏳ Guardando...';
        
        const content = editor.value;
        
        // Determinar nombre de archivo según tipo
        let filename;
        if (tipo === 'base') {
            filename = `${codigo}_base.txt`;
        } else if (tipo === 'prompt_imagen') {
            filename = `${codigo}_prompt_imagen.txt`;
        } else if (tipo === 'script_video') {
            filename = `${codigo}_script_video.txt`;
        } else {
            filename = `${codigo}_${tipo}.txt`;
        }
        
        const response = await fetch('/api/drive/save-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                codigo: codigo,
                folder: 'textos',
                filename: filename,
                content: content
            })
        });
        
        if (!response.ok) {
            throw new Error('Error al guardar');
        }
        
        // Actualizar valor original
        editor.dataset.original = content;
        editor.classList.remove('modified');
        
        // Mostrar confirmación
        saveBtn.classList.remove('show');
        status.classList.add('show');
        
        // Resetear botón
        saveBtn.disabled = false;
        const tipoNombre = tipo === 'base' ? '' : ` ${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`;
        saveBtn.textContent = `💾 Guardar${tipoNombre}`;
        
        // Ocultar confirmación después de 3 segundos
        setTimeout(() => {
            status.classList.remove('show');
        }, 3000);
        
    } catch (error) {
        console.error('Error guardando:', error);
        saveBtn.disabled = false;
        saveBtn.textContent = '❌ Error';
        showError('Error al guardar: ' + error.message);
        
        setTimeout(() => {
            const tipoNombre = tipo === 'base' ? '' : ` ${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`;
            saveBtn.textContent = `💾 Guardar${tipoNombre}`;
        }, 2000);
    }
}

// Verificar si hay cambios sin guardar
function hayTextosSinGuardar() {
    const editores = document.querySelectorAll('.content-editor');
    for (const editor of editores) {
        const original = editor.dataset.original || '';
        if (editor.value !== original) {
            return true;
        }
    }
    return false;
}

// Cancelar y volver
function cancelar() {
    if (hayTextosSinGuardar()) {
        if (!confirm('⚠️ Tienes cambios sin guardar. ¿Seguro que deseas salir sin guardar?')) {
            return;
        }
    }
    volverAlPanel();
}

// Volver al panel principal
function volverAlPanel() {
    const posts = JSON.parse(localStorage.getItem('posts') || '[]');
    const postIndex = posts.findIndex(p => p.codigo === codigo);
    localStorage.setItem('currentPostIndex', postIndex >= 0 ? postIndex : 0);
    window.location.href = '/';
}

// Utilidades UI
function showError(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="message error">❌ ${message}</div>`;
    setTimeout(() => container.innerHTML = '', 5000);
}

function showSuccess(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="message success">✅ ${message}</div>`;
    setTimeout(() => container.innerHTML = '', 3000);
}

function showLoading(message) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="message loading"><div class="spinner"></div>${message}</div>`;
}

// Escapar HTML para evitar problemas con comillas en data attributes
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/"/g, '&quot;');
}
