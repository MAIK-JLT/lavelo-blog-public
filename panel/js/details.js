// Configuración
const API_BASE = '/api';

// Estado global
let currentPost = null;
let phaseIsValidated = false;
let userConfirmedEdit = false;

// Obtener parámetros de URL
const urlParams = new URLSearchParams(window.location.search);
const codigo = urlParams.get('codigo');
const estadoOverride = urlParams.get('estado'); // Estado específico a mostrar (para fases validadas)

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
    // Usar estadoOverride si existe (para fases validadas), si no, usar el estado del post
    const estado = estadoOverride || currentPost.estado;
    const phaseContent = document.getElementById('phase-content');
    
    // Detectar si la fase está validada (viene de una fase completada)
    phaseIsValidated = estadoOverride ? isPhaseValidated(estado) : false;
    
    // Si está validada y el usuario no ha confirmado, mostrar advertencia
    if (phaseIsValidated && !userConfirmedEdit) {
        showEditWarning(estado);
        return;
    }
    
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
    
    // Intentar cargar metadata de referencias
    const metadataText = await fetchFileFromDrive('textos', `${codigo}_referencias_metadata.json`);
    let referencesHTML = '';
    
    if (metadataText) {
        try {
            const metadata = JSON.parse(metadataText);
            if (metadata.references && metadata.references.length > 0) {
                referencesHTML = `
                    <div class="text-item" style="background: #f0f9ff; border-left-color: #3b82f6;">
                        <h3>🖼️ Imágenes de Referencia</h3>
                        <p style="color: #666; margin-bottom: 15px;">Estas imágenes se usarán como guía en la generación:</p>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                            ${metadata.references.map((ref, idx) => {
                                // Usar storage local
                                const imageUrl = `${API_BASE}/files/${codigo}/imagenes/${encodeURIComponent(ref.filename)}`;
                                return `
                                <div style="text-align: center;">
                                    <img src="${imageUrl}" 
                                         style="max-width: 100%; border-radius: 8px; border: 2px solid #ddd; margin-bottom: 8px; background: #f5f5f5;"
                                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                                         alt="Referencia ${idx + 1}">
                                    <div style="display:none; padding:20px; background:#fee; border-radius:8px; color:#c00;">
                                        ⚠️ Error cargando imagen
                                    </div>
                                    <p style="font-size: 13px; color: #666; margin: 0;">
                                        <strong>Referencia ${idx + 1}</strong><br>
                                        ${ref.label}<br>
                                        <small style="color:#999;">${ref.filename}</small>
                                    </p>
                                </div>
                            `}).join('')}
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.error('Error parseando metadata de referencias:', e);
        }
    }
    
    phaseContent.innerHTML = `
        <div class="phase-section">
            <h2 class="phase-title">🎨 Prompt de Imagen</h2>
            <p style="color: #666; margin-bottom: 20px;">Revisa y edita el prompt que se usará para generar la imagen base. Debe ser descriptivo y en inglés.</p>
            <div class="text-item">
                <h3>📝 Prompt para Generación de Imagen</h3>
                <textarea id="prompt-editor" class="content-editor" data-original="${escapeHtml(promptText || '')}" style="min-height: 150px;">${promptText || ''}</textarea>
                <div class="save-btn-container">
                    <button class="save-btn" id="save-prompt_imagen" onclick="guardarTextoIndividual('prompt_imagen', 'prompt-editor')">💾 Guardar Prompt</button>
                    <button class="ai-btn" onclick="mejorarConIA('prompt_imagen', 'prompt-editor')">✨ Mejorar con IA</button>
                    <button class="ai-btn" onclick="abrirPromptBuilderFromTextarea()" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">🎨 Mejorar con Imagen</button>
                    <span class="save-status" id="status-prompt_imagen">✅ Guardado</span>
                </div>
            </div>
            
            ${referencesHTML}
        </div>
    `;
    
    setupTextEditor('prompt-editor', 'save-prompt_imagen', 'status-prompt_imagen');
}

// FASE 4: IMAGE_BASE_AWAITING
async function renderImageBasePhase() {
    const phaseContent = document.getElementById('phase-content');
    phaseContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando imagen base...</p></div>';
    
    // Obtener el prompt usado
    const promptText = await fetchFileFromDrive('textos', `${codigo}_prompt_imagen.txt`);
    
    // Verificar si ya existe imagen_base.png
    const imageExists = await checkImageExists('imagenes', `${codigo}_imagen_base.png`);
    
    if (!imageExists) {
        // No hay imagen generada, mostrar botón GENERATE
        phaseContent.innerHTML = `
            <div class="phase-section">
                <h2 class="phase-title">🎨 Generar Imagen Base</h2>
                <p style="color: #666; margin-bottom: 20px;">Genera la imagen base usando IA con el prompt y referencias de la Fase 3.</p>
                
                <div style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-bottom: 10px;">📝 Prompt a usar:</h4>
                    <p style="color: #666; font-size: 0.9em; line-height: 1.6;">${promptText || 'No disponible'}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <button class="ai-btn" onclick="generateImageWithAI()" style="font-size: 1.1em; padding: 15px 40px;">
                        🚀 GENERAR IMAGEN CON IA
                    </button>
                    <p style="color: #999; font-size: 0.85em; margin-top: 10px;">Se generarán 4 variaciones usando SeaDream 4.0</p>
                </div>
                
                <div id="generation-progress" style="display: none; text-align: center; margin: 20px 0;">
                    <div class="spinner"></div>
                    <p style="color: #666; margin-top: 10px;">Generando imágenes... Esto puede tardar 30-60 segundos.</p>
                </div>
                
                <div id="generated-images" style="margin-top: 30px;"></div>
            </div>
        `;
    } else {
        // Imagen ya existe, mostrar preview
        const imageUrl = `/api/files/${codigo}/imagenes/${codigo}_imagen_base.png`;
        
        phaseContent.innerHTML = `
            <div class="phase-section">
                <h2 class="phase-title">🖼️ Imagen Base Generada</h2>
                <p style="color: #666; margin-bottom: 20px;">Revisa la imagen generada. Si no te gusta, puedes regenerarla.</p>
                <div class="text-item">
                    <h3>📸 Imagen Base (1024x1024)</h3>
                    <div style="text-align: center; padding: 20px;">
                        <img src="${imageUrl}" alt="Imagen base" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);" onerror="this.src=''; this.alt='Error cargando imagen';">
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <h4 style="margin-bottom: 10px;">Prompt usado:</h4>
                        <p style="color: #666; font-size: 0.9em; line-height: 1.6;">${promptText || 'No disponible'}</p>
                    </div>
                    <input type="file" id="upload-image-input-fase4" accept="image/png,image/jpeg,image/jpg" style="display: none;" onchange="handleImageUploadFase4(event)">
                    <div style="text-align: center; margin-top: 20px;">
                        <button class="ai-btn" onclick="regenerarImagenConIA()">🔄 Regenerar con IA</button>
                        <button class="ai-btn" onclick="generateVariationsWithFalAI()" style="margin-left: 10px;">🎨 Generar 4 Variaciones (Fal.ai)</button>
                        <button class="ai-btn" onclick="reemplazarImagenManual()" style="margin-left: 10px;">📤 Reemplazar con mi Imagen</button>
                    </div>
                    <div id="fal-variations-container" style="margin-top: 30px; display: none;">
                        <h3 style="text-align: center; margin-bottom: 20px;">🎨 Variaciones Generadas con Fal.ai</h3>
                        <div id="fal-variations-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px;"></div>
                        <p style="text-align: center; color: #666; font-size: 0.9em;">Haz click en una variación para usarla como imagen base</p>
                    </div>
                    <div id="upload-preview-fase4" style="margin-top: 15px; display: none; text-align: center;">
                        <img id="preview-img-fase4" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-top: 10px;">
                        <p id="preview-info-fase4" style="color: #666; font-size: 0.9em; margin-top: 10px;"></p>
                        <button class="ai-btn" onclick="confirmarSubidaImagenFase4()" style="margin-top: 10px;">✅ Confirmar y Reemplazar</button>
                        <button class="btn-secondary" onclick="cancelarSubidaImagenFase4()" style="margin-top: 10px; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer;">❌ Cancelar</button>
                    </div>
                    <p style="color: #666; font-size: 0.9em; text-align: center; margin-top: 15px;">Si la imagen es correcta, vuelve al panel y haz clic en VALIDATE para generar los formatos.</p>
                </div>
            </div>
        `;
    }
}

// Función para verificar si una imagen existe en storage local
async function checkImageExists(folder, filename) {
    try {
        // Verificar en storage local usando el endpoint /api/files/
        const response = await fetch(`${API_BASE}/files/${codigo}/${folder}/${filename}`);
        return response.ok;
    } catch (error) {
        console.error('Error verificando imagen:', error);
        return false;
    }
}

// Función para generar imagen con IA
async function generateImageWithAI() {
    const progressDiv = document.getElementById('generation-progress');
    const generateBtn = document.querySelector('button[onclick="generateImageWithAI()"]');
    const generatedImagesDiv = document.getElementById('generated-images');
    
    if (generateBtn) generateBtn.disabled = true;
    if (progressDiv) progressDiv.style.display = 'block';
    if (generatedImagesDiv) generatedImagesDiv.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/generate-image`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({codigo: codigo})
        });
        
        const result = await response.json();
        
        if (progressDiv) progressDiv.style.display = 'none';
        
        if (result.success) {
            // Mostrar las 4 variaciones generadas
            let imagesHTML = '<h3 style="text-align: center; margin-bottom: 20px;">✅ Imágenes Generadas - Selecciona una</h3>';
            imagesHTML += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">';
            
            result.images.forEach((img, idx) => {
                const imageUrl = `/api/files/${codigo}/imagenes/${img.filename}`;
                imagesHTML += `
                    <div style="text-align: center; padding: 15px; border: 2px solid #ddd; border-radius: 10px; cursor: pointer;" onclick="selectGeneratedImage('${img.filename}', ${idx})">
                        <img src="${imageUrl}" style="width: 100%; border-radius: 8px;" alt="Variación ${idx + 1}">
                        <p style="margin-top: 10px; color: #666;">Variación ${idx + 1}</p>
                    </div>
                `;
            });
            
            imagesHTML += '</div>';
            imagesHTML += '<p style="text-align: center; color: #666; margin-top: 20px;">Haz click en la imagen que prefieras para usarla como base.</p>';
            
            if (generatedImagesDiv) generatedImagesDiv.innerHTML = imagesHTML;
            
            showNotification(`${result.images.length} imágenes generadas correctamente`, 'success');
        } else {
            throw new Error(result.error || 'Error desconocido');
        }
    } catch (error) {
        if (progressDiv) progressDiv.style.display = 'none';
        if (generateBtn) generateBtn.disabled = false;
        showNotification(`Error generando imagen: ${error.message}`, 'error');
    }
}

// Función para seleccionar una imagen generada
async function selectGeneratedImage(filename, index) {
    if (!confirm(`¿Usar la Variación ${index + 1} como imagen base?`)) return;
    
    try {
        // Si no es la primera (imagen_base.png), renombrarla
        if (filename !== `${codigo}_imagen_base.png`) {
            // Aquí podrías implementar un endpoint para renombrar, o simplemente recargar
            showNotification('Imagen seleccionada. Recargando...', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Imagen base ya seleccionada', 'success');
            setTimeout(() => location.reload(), 1000);
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
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
            const url = `/api/files/${codigo}/imagenes/${filename}?t=${Date.now()}`;
            
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
                    <button class="ai-btn" onclick="mejorarConIA('script_video', 'script-editor')">✨ Mejorar con IA</button>
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
                        <source src="/api/files/${codigo}/videos/${codigo}_video_base.mp4" type="video/mp4">
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
            const url = `/api/files/${codigo}/videos/${filename}?t=${Date.now()}`;
            
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

// Obtener archivo del storage local
async function fetchFileFromDrive(folder, filename) {
    try {
        const response = await fetch(`/api/files/${codigo}/${folder}/${filename}`);
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
        
        const response = await fetch(`/api/files/${codigo}/textos/${filename}`, {
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
        
        // Resetear fases dependientes si es prompt de imagen o script de video
        // (siempre, no solo si está validada)
        const shouldReset = tipo === 'prompt_imagen' || tipo === 'script_video' || tipo === 'base';
        
        if (shouldReset || (phaseIsValidated && userConfirmedEdit)) {
            // Determinar el estado correcto según el tipo de archivo editado
            let estadoParaReset = currentPost.estado;
            if (tipo === 'base') {
                estadoParaReset = 'BASE_TEXT_AWAITING';
            } else if (tipo === 'prompt_imagen') {
                estadoParaReset = 'IMAGE_PROMPT_AWAITING';
            } else if (tipo === 'script_video') {
                estadoParaReset = 'VIDEO_PROMPT_AWAITING';
            }
            await resetDependentPhases(estadoParaReset);
        }
        
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
    window.location.href = '/panel/';
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

// Mejorar contenido con IA
function mejorarConIA(tipo, editorId) {
    // 1. Obtener contenido actual
    const textarea = document.getElementById(editorId);
    const contenidoActual = textarea.value;
    
    if (!contenidoActual || contenidoActual.trim() === '') {
        alert('No hay contenido para mejorar. Por favor, genera primero el contenido.');
        return;
    }
    
    // 2. Abrir chat
    if (typeof toggleChat === 'function') {
        toggleChat();
    }
    
    // 3. Preparar mensaje contextual
    const tipoTexto = tipo === 'prompt_imagen' ? 'prompt de imagen' : 'script de video';
    const mensaje = `Quiero mejorar el ${tipoTexto} del post ${codigo}.

Contenido actual:
${contenidoActual}

¿Puedes ayudarme a mejorarlo?`;
    
    // 4. Enviar al chat después de un pequeño delay para que se abra
    setTimeout(() => {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = mensaje;
            // Auto-enviar el mensaje
            if (typeof sendChatMessage === 'function') {
                sendChatMessage();
            }
        }
    }, 300);
}

// Regenerar imagen con IA (desde Fase 4)
async function regenerarImagenConIA() {
    // Obtener el prompt actual
    const promptText = await fetchFileFromDrive('textos', `${codigo}_prompt_imagen.txt`);
    
    if (!promptText) {
        alert('No se pudo cargar el prompt actual.');
        return;
    }
    
    // Abrir chat
    if (typeof toggleChat === 'function') {
        toggleChat();
    }
    
    // Mensaje contextual
    const mensaje = `La imagen generada para el post ${codigo} no me convence.

Prompt actual usado:
${promptText}

¿Puedes ayudarme a mejorarlo para regenerar una imagen mejor?`;
    
    // Enviar al chat
    setTimeout(() => {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = mensaje;
            if (typeof sendChatMessage === 'function') {
                sendChatMessage();
            }
        }
    }, 300);
}

// Generar 4 variaciones con Fal.ai (desde Fase 4)
async function generateVariationsWithFalAI() {
    console.log('🎨 Iniciando generación de variaciones con Fal.ai...');
    
    try {
        const container = document.getElementById('fal-variations-container');
        const grid = document.getElementById('fal-variations-grid');
        const btn = document.querySelector('button[onclick="generateVariationsWithFalAI()"]');
        
        console.log('Container:', container);
        console.log('Grid:', grid);
        console.log('Button:', btn);
        
        const confirmResult = confirm('¿Generar 4 variaciones con Fal.ai? Esto costará ~$0.12 (4 imágenes × $0.03)');
        console.log('Confirm result:', confirmResult);
        
        if (!confirmResult) {
            console.log('Usuario canceló');
            return;
        }
        
        // Deshabilitar botón y mostrar loading
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Generando...';
        }
        
        if (container) container.style.display = 'none';
        if (grid) grid.innerHTML = '';
        
        console.log('Llamando a API...');
        alert('Generando 4 variaciones con Fal.ai... Esto puede tardar 30-60 segundos.');
        
        const response = await fetch(`${API_BASE}/generate-image`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({codigo: codigo})
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Result:', result);
        
        if (result.success && result.images) {
            // Mostrar las 4 variaciones en grid
            let gridHTML = '';
            
            result.images.forEach((img, idx) => {
                const imageUrl = `/api/files/${codigo}/imagenes/${img.filename}`;
                gridHTML += `
                    <div style="text-align: center; padding: 15px; border: 2px solid #ddd; border-radius: 10px; cursor: pointer; transition: all 0.3s;" 
                         onclick="selectFalVariation('${img.filename}', ${idx + 1})"
                         onmouseover="this.style.borderColor='#7c3aed'; this.style.transform='scale(1.02)'"
                         onmouseout="this.style.borderColor='#ddd'; this.style.transform='scale(1)'">
                        <img src="${imageUrl}" style="width: 100%; border-radius: 8px;" alt="Variación ${idx + 1}">
                        <p style="margin-top: 10px; color: #666; font-weight: bold;">Variación ${idx + 1}</p>
                    </div>
                `;
            });
            
            if (grid) grid.innerHTML = gridHTML;
            if (container) container.style.display = 'block';
            
            alert(`✅ ${result.images.length} variaciones generadas. Haz click en una para usarla.`);
        } else {
            throw new Error(result.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('❌ Error generando variaciones:', error);
        alert(`❌ Error: ${error.message}`);
    } finally {
        const btn = document.querySelector('button[onclick="generateVariationsWithFalAI()"]');
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🎨 Generar 4 Variaciones (Fal.ai)';
        }
    }
}

// Seleccionar una variación de Fal.ai para usarla como imagen base
async function selectFalVariation(filename, variationNumber) {
    if (!confirm(`¿Usar la Variación ${variationNumber} como imagen base?\n\nEsto reemplazará la imagen actual.`)) {
        return;
    }
    
    try {
        showNotification('Aplicando variación...', 'info');
        
        // Si no es la primera (imagen_base.png), necesitamos renombrarla
        if (filename !== `${codigo}_imagen_base.png`) {
            // Crear endpoint para renombrar o simplemente recargar
            // Por ahora, simplemente recargamos para que el usuario vea la seleccionada
            showNotification(`✅ Variación ${variationNumber} seleccionada. Recargando...`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification('✅ Esta ya es la imagen base actual', 'success');
        }
    } catch (error) {
        showNotification(`❌ Error: ${error.message}`, 'error');
    }
}

// ============================================
// SUBIR/REEMPLAZAR IMAGEN MANUAL (FASE 4)
// ============================================
let selectedImageFile = null;

// FASE 4: Reemplazar imagen
function reemplazarImagenManual() {
    document.getElementById('upload-image-input-fase4').click();
}

function handleImageUploadFase4(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validar formato
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        alert('Formato no válido. Usa PNG o JPG.');
        return;
    }
    
    // Validar tamaño (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('Archivo muy grande. Máximo 10MB.');
        return;
    }
    
    selectedImageFile = file;
    
    // Mostrar preview
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-img-fase4').src = e.target.result;
        document.getElementById('preview-info-fase4').textContent = `${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
        document.getElementById('upload-preview-fase4').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function cancelarSubidaImagenFase4() {
    selectedImageFile = null;
    document.getElementById('upload-image-input-fase4').value = '';
    document.getElementById('upload-preview-fase4').style.display = 'none';
}

async function confirmarSubidaImagenFase4() {
    if (!selectedImageFile) {
        alert('No hay imagen seleccionada');
        return;
    }
    
    // Mostrar overlay
    showUploadOverlay('Reemplazando imagen...', 'Guardando imagen, por favor espera...');
    
    try {
        // Convertir imagen a base64
        const reader = new FileReader();
        const imageBase64 = await new Promise((resolve, reject) => {
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(selectedImageFile);
        });
        
        // Enviar como JSON con base64
        const response = await fetch(`${API_BASE}/posts/${codigo}/upload-image`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_data: imageBase64,
                filename: `${codigo}_imagen_base.png`
            })
        });
        
        const result = await response.json();
        
        hideUploadOverlay();
        
        if (result.success) {
            showSuccess(result.message);
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showError(result.error || 'Error reemplazando imagen');
        }
    } catch (error) {
        hideUploadOverlay();
        showError('Error de conexión: ' + error.message);
    }
}

// Funciones para mostrar/ocultar overlay de subida
function showUploadOverlay(title, message) {
    document.getElementById('upload-title').textContent = title;
    document.getElementById('upload-message').textContent = message;
    document.getElementById('upload-overlay').classList.add('show');
}

function hideUploadOverlay() {
    document.getElementById('upload-overlay').classList.remove('show');
}

// ============================================
// ADVERTENCIA PARA EDITAR FASE VALIDADA
// ============================================

// Mapeo de estados a número de fase
const stateToPhase = {
    'BASE_TEXT_AWAITING': 1,
    'ADAPTED_TEXTS_AWAITING': 2,
    'IMAGE_PROMPT_AWAITING': 3,
    'IMAGE_BASE_AWAITING': 4,
    'IMAGE_FORMATS_AWAITING': 5,
    'VIDEO_PROMPT_AWAITING': 6,
    'VIDEO_BASE_AWAITING': 7,
    'VIDEO_FORMATS_AWAITING': 8
};

// Detectar si una fase está validada (viene de fase posterior)
function isPhaseValidated(estado) {
    const currentPhaseNum = stateToPhase[estado];
    if (!currentPhaseNum) return false;
    
    const post = currentPost;
    if (!post) return false;
    
    // Función helper para convertir a booleano
    const toBool = (val) => val === 1 || val === true || val === 'TRUE' || val === '1';
    
    // Verificar si la fase actual ya fue completada (tiene checkboxes marcados)
    switch (estado) {
        case 'BASE_TEXT_AWAITING':
            return toBool(post.base_txt);
        case 'ADAPTED_TEXTS_AWAITING':
            return toBool(post.instagram_txt) || toBool(post.linkedin_txt) || toBool(post.twitter_txt);
        case 'IMAGE_PROMPT_AWAITING':
            return toBool(post.prompt_imagen_base_txt);
        case 'IMAGE_BASE_AWAITING':
            return toBool(post.imagen_base_png);
        case 'IMAGE_FORMATS_AWAITING':
            return toBool(post.instagram_1x1_png) || toBool(post.linkedin_16x9_png);
        case 'VIDEO_PROMPT_AWAITING':
            return toBool(post.script_video_base_txt);
        case 'VIDEO_BASE_AWAITING':
            return toBool(post.video_base_mp4);
        case 'VIDEO_FORMATS_AWAITING':
            return toBool(post.feed_16x9_mp4) || toBool(post.stories_9x16_mp4);
        default:
            return false;
    }
}

// Mapeo de fases que se resetearán
const resetMap = {
    'BASE_TEXT_AWAITING': [
        'Fase 2: Textos Adaptados',
        'Fase 3: Prompt Imagen',
        'Fase 4: Imagen Base',
        'Fase 5: Formatos Imagen',
        'Fase 6: Script Video',
        'Fase 7: Video Base',
        'Fase 8: Formatos Video'
    ],
    'ADAPTED_TEXTS_AWAITING': [], // No resetea nada
    'IMAGE_PROMPT_AWAITING': [
        'Fase 4: Imagen Base',
        'Fase 5: Formatos Imagen'
    ],
    'IMAGE_BASE_AWAITING': [
        'Fase 5: Formatos Imagen'
    ],
    'IMAGE_FORMATS_AWAITING': [],
    'VIDEO_PROMPT_AWAITING': [
        'Fase 7: Video Base',
        'Fase 8: Formatos Video'
    ],
    'VIDEO_BASE_AWAITING': [
        'Fase 8: Formatos Video'
    ],
    'VIDEO_FORMATS_AWAITING': []
};

// Mostrar advertencia antes de editar
function showEditWarning(estado) {
    const resetPhases = resetMap[estado] || [];
    
    if (resetPhases.length === 0) {
        // No hay fases que resetear, permitir edición directamente
        userConfirmedEdit = true;
        cargarContenidoFase();
        return;
    }
    
    // Mostrar modal con lista de fases que se resetearán
    const resetList = document.getElementById('reset-list');
    resetList.innerHTML = resetPhases.map(phase => `<li>${phase}</li>`).join('');
    
    document.getElementById('warning-modal').style.display = 'flex';
}

// Cancelar edición
function cancelWarning() {
    document.getElementById('warning-modal').style.display = 'none';
    // Volver al panel principal
    window.location.href = '/panel/';
}

// Confirmar edición
function confirmEdit() {
    userConfirmedEdit = true;
    document.getElementById('warning-modal').style.display = 'none';
    cargarContenidoFase();
}

// Resetear fases dependientes (llamado después de guardar)
async function resetDependentPhases(estadoParaReset) {
    try {
        // Si no se proporciona estado, usar el del post actual
        const estado = estadoParaReset || currentPost.estado;
        
        console.log(`🔄 Reseteando fases dependientes de: ${estado}`);
        
        const response = await fetch(`${API_BASE}/posts/${codigo}/reset-phases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: estado })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Fases dependientes reseteadas');
            // Mostrar notificación
            showSuccess('Cambios guardados. Fases posteriores han sido reseteadas.');
        } else {
            console.error('❌ Error reseteando fases:', result.error);
        }
        
    } catch (error) {
        console.error('❌ Error en resetDependentPhases:', error);
    }
}

// ============================================
// PROMPT BUILDER VISUAL
// ============================================

function abrirPromptBuilderFromTextarea() {
    try {
        // Leer el prompt actual del textarea
        const textarea = document.getElementById('prompt-editor');
        const promptActual = textarea ? textarea.value : '';
        
        // Construir URL con parámetros
        const params = new URLSearchParams({
            codigo: codigo,
            prompt: promptActual
        });
        
        // Abrir en nueva ventana
        const url = `prompt_builder.html?${params.toString()}`;
        const newWindow = window.open(url, '_blank', 'width=1200,height=800');
        
        // Si el navegador bloqueó el popup, abrir en la misma pestaña
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            window.location.href = url;
        }
    } catch (error) {
        console.error('Error abriendo Prompt Builder:', error);
        alert('Error abriendo el editor visual. Revisa la consola.');
    }
}

function abrirPromptBuilder(promptActual) {
    try {
        // Construir URL con parámetros
        const params = new URLSearchParams({
            codigo: codigo,
            prompt: promptActual || ''
        });
        
        // Abrir en nueva ventana
        const url = `prompt_builder.html?${params.toString()}`;
        const newWindow = window.open(url, '_blank', 'width=1200,height=800');
        
        // Si el navegador bloqueó el popup, abrir en la misma pestaña
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            window.location.href = url;
        }
    } catch (error) {
        console.error('Error abriendo Prompt Builder:', error);
        alert('Error abriendo el editor visual. Revisa la consola.');
    }
}
