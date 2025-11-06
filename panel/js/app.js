// ============================================
// CONFIGURACIÓN
// ============================================
const API_BASE = 'http://localhost:5001/api';
let currentPost = null;
let currentPostIndex = 0;

// ============================================
// INICIALIZACIÓN
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    // Verificar autenticación primero
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        window.location.href = '/login.html';
        return;
    }
    
    // Restaurar índice del post si viene de details
    const savedIndex = localStorage.getItem('currentPostIndex');
    if (savedIndex !== null) {
        currentPostIndex = parseInt(savedIndex);
        localStorage.removeItem('currentPostIndex'); // Limpiar después de usar
    }
    
    updateCurrentDate();
    initNetworksFilter();
    loadPostData();
    setTimeout(() => addPostSelector(), 1000);
});

// Verificar si el usuario está autenticado
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/social/me`, { 
            credentials: 'include' 
        });
        
        if (response.status === 401) {
            return false;
        }
        
        const user = await response.json();
        console.log('✅ Usuario autenticado:', user);
        return true;
    } catch (error) {
        console.error('Error verificando autenticación:', error);
        return false;
    }
}

// ============================================
// CARGAR DATOS
// ============================================
async function loadPostData() {
    try {
        const response = await fetch(`${API_BASE}/posts`, { credentials: 'include' });
        const result = await response.json();
        
        if (result.error) {
            showError(result.error);
            return;
        }
        
        const posts = result.posts || result;
        
        // Verificar que posts sea un array
        if (!Array.isArray(posts)) {
            console.error('posts no es un array:', posts);
            showError('Formato de datos incorrecto');
            return;
        }
        
        localStorage.setItem('posts', JSON.stringify(posts));
        const data = posts[currentPostIndex] || posts[0];
        currentPost = data;
        
        renderPostInfo(data);
        renderPhases(data);
        renderProgress(data);
        updateNetworksFromPost(data);
        
        // Actualizar selector de posts
        addPostSelector();
    } catch (error) {
        showError('Error al cargar datos del servidor');
        console.error(error);
    }
}

// ============================================
// RENDERIZADO
// ============================================
function renderPostInfo(data) {
    const postInfo = document.getElementById('post-info');
    const statusClass = getStatusClass(data.estado);
    
    postInfo.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h2 style="margin: 0;">📄 ${data.titulo || 'Sin título'}</h2>
            <button class="delete-post-btn" onclick="deletePost()" title="Eliminar este post">
                🗑️ Eliminar Post
            </button>
        </div>
        <p><strong>Código:</strong> ${data.codigo}</p>
        <p><strong>Categoría:</strong> ${data.categoria || 'Sin categoría'}</p>
        <span class="status ${statusClass}">${formatStatus(data.estado)}</span>
    `;
}

function renderProgress(data) {
    const progress = document.getElementById('progress');
    const percentage = calculateProgress(data);
    progress.style.width = `${percentage}%`;
    progress.textContent = `${percentage}%`;
}

function renderPhases(data) {
    const phases = document.getElementById('phases');
    const phasesData = [
        { id: 1, name: 'Texto Base', states: ['BASE_TEXT_AWAITING'], step: 'base' },
        { id: 2, name: 'Textos Adaptados', states: ['ADAPTED_TEXTS_AWAITING'], step: 'texts' },
        { id: 3, name: 'Prompt Imagen', states: ['IMAGE_PROMPT_AWAITING'], step: 'image_prompt' },
        { id: 4, name: 'Imagen Base', states: ['IMAGE_BASE_AWAITING'], step: 'image_base' },
        { id: 5, name: 'Formatos Imagen', states: ['IMAGE_FORMATS_AWAITING'], step: 'image_formats' },
        { id: 6, name: 'Script Video', states: ['VIDEO_PROMPT_AWAITING'], step: 'video_prompt' },
        { id: 7, name: 'Video Base', states: ['VIDEO_BASE_AWAITING'], step: 'video_base' },
        { id: 8, name: 'Formatos Video', states: ['VIDEO_FORMATS_AWAITING'], step: 'video_formats' },
        { id: 9, name: 'Publicación', states: ['READY_TO_PUBLISH', 'PUBLISHED'], step: 'publish' }
    ];
    
    phases.innerHTML = phasesData.map(phase => {
        const status = getPhaseStatus(phase, data.estado);
        const icon = status === 'completed' ? '✅' : status === 'active' ? '📋' : '⏸️';
        const description = getPhaseDescription(phase.id, status);
        const buttons = getPhaseButtons(phase, status, data.estado);
        
        return `
            <div class="phase ${status}">
                <div class="phase-header">
                    <div class="phase-info">
                        <h3>${icon} Fase ${phase.id}: ${phase.name}</h3>
                        <p style="margin-top: 5px; font-size: 14px; color: #666;">${description}</p>
                    </div>
                    <div class="phase-actions">
                        ${buttons}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// LÓGICA DE FASES
// ============================================
function getPhaseStatus(phase, currentState) {
    const stateToPhase = {
        'BASE_TEXT_AWAITING': 1,
        'ADAPTED_TEXTS_AWAITING': 2,
        'IMAGE_PROMPT_AWAITING': 3,
        'IMAGE_BASE_AWAITING': 4,
        'IMAGE_FORMATS_AWAITING': 5,
        'VIDEO_PROMPT_AWAITING': 6,
        'VIDEO_BASE_AWAITING': 7,
        'VIDEO_FORMATS_AWAITING': 8,
        'READY_TO_PUBLISH': 9,
        'PUBLISHED': 9
    };
    
    const currentPhase = stateToPhase[currentState] || 0;
    
    if (phase.id < currentPhase) return 'completed';
    if (phase.id === currentPhase) return 'active';
    return 'locked';
}

function getPhaseButtons(phase, status, currentState) {
    if (status === 'locked') {
        return '<span style="color: #999; font-size: 12px;">🔒 Pendiente</span>';
    }
    
    // Obtener el estado correspondiente a esta fase
    const phaseState = phase.states[0]; // Usar el primer estado de la fase
    
    if (status === 'completed') {
        // Fases completadas TAMBIÉN tienen botón "Ver Detalles"
        return `
            <button class="phase-btn secondary" onclick="viewDetails('${phaseState}')">📋 Ver Detalles</button>
            <span style="color: #28a745; font-size: 12px; font-weight: bold; margin-left: 10px;">✅ Validado</span>
        `;
    }
    
    if (status === 'active') {
        return `
            <button class="phase-btn secondary" onclick="viewDetails('${phaseState}')">📋 Ver Detalles</button>
            <button class="phase-btn success" onclick="validatePhase()">✅ VALIDATE</button>
        `;
    }
    
    return '';
}

function getPhaseDescription(phaseId, status) {
    const descriptions = {
        1: status === 'active' ? 'Revisar y validar el texto base creado manualmente' : 
            status === 'completed' ? 'Texto base validado ✓' : 'Pendiente de creación manual',
        2: status === 'active' ? 'Revisar textos adaptados para cada red social' : 
            status === 'completed' ? 'Textos adaptados validados ✓' : 'Se generarán automáticamente',
        3: status === 'active' ? 'Revisar prompt para generación de imagen' : 
            status === 'completed' ? 'Prompt de imagen validado ✓' : 'Se generará automáticamente',
        4: status === 'active' ? 'Revisar imagen base generada por IA' : 
            status === 'completed' ? 'Imagen base validada ✓' : 'Se generará automáticamente',
        5: status === 'active' ? 'Revisar formatos de imagen para redes sociales' : 
            status === 'completed' ? 'Formatos de imagen validados ✓' : 'Se generarán automáticamente',
        6: status === 'active' ? 'Revisar script para generación de video' : 
            status === 'completed' ? 'Script de video validado ✓' : 'Se generará automáticamente',
        7: status === 'active' ? 'Revisar video base generado por IA' : 
            status === 'completed' ? 'Video base validado ✓' : 'Se generará automáticamente',
        8: status === 'active' ? 'Revisar formatos de video para redes sociales' : 
            status === 'completed' ? 'Formatos de video validados ✓' : 'Se generarán automáticamente',
        9: status === 'active' ? 'Listo para publicar en todas las plataformas' : 
            status === 'completed' ? 'Publicado en todas las plataformas ✓' : 'Pendiente de completar fases anteriores'
    };
    return descriptions[phaseId] || '';
}

// ============================================
// ACCIONES DE BOTONES
// ============================================
function checkPhase(phaseId) {
    const btn = document.getElementById(`check-btn-${phaseId}`);
    if (btn) {
        btn.innerHTML = 'OK ✓';
        btn.style.background = '#28a745';
        btn.style.color = 'white';
        btn.disabled = true;
    }
}

async function validatePhase() {
    if (!currentPost) {
        showError('No hay post seleccionado');
        return;
    }
    
    const stateInfo = getStateInfo(currentPost.estado);
    const message = `📋 VALIDACIÓN\n\n` +
                   `Estado actual: ${stateInfo.name}\n` +
                   `Acción: ${stateInfo.action}\n\n` +
                   `Siguiente estado: ${stateInfo.next_name}\n\n` +
                   `¿Continuar?`;
    
    if (!confirm(message)) return;
    
    const validateBtn = document.querySelector('.phase-btn.success');
    if (validateBtn) {
        validateBtn.disabled = true;
        validateBtn.style.opacity = '0.6';
        validateBtn.innerHTML = '⏳ Procesando...';
    }
    
    try {
        // Obtener redes seleccionadas
        const selectedNetworks = getSelectedNetworks();
        
        const response = await fetch(`${API_BASE}/validate-phase`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                codigo: currentPost.codigo,
                current_state: currentPost.estado,
                redes: selectedNetworks
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            loadPostData();
        } else {
            showError(result.error || 'Error desconocido');
            if (validateBtn) {
                validateBtn.disabled = false;
                validateBtn.style.opacity = '1';
                validateBtn.innerHTML = 'VALIDATE';
            }
        }
    } catch (error) {
        showError('Error de conexión');
        console.error(error);
        if (validateBtn) {
            validateBtn.disabled = false;
            validateBtn.style.opacity = '1';
            validateBtn.innerHTML = 'VALIDATE';
        }
    }
}

function getStateInfo(estado) {
    const states = {
        'BASE_TEXT_AWAITING': { name: 'Texto Base', action: 'Generar textos adaptados para redes sociales', next_name: 'Textos Adaptados' },
        'ADAPTED_TEXTS_AWAITING': { name: 'Textos Adaptados', action: 'Generar prompt de imagen', next_name: 'Prompt de Imagen' },
        'IMAGE_PROMPT_AWAITING': { name: 'Prompt de Imagen', action: 'Generar imagen base', next_name: 'Imagen Base' },
        'IMAGE_BASE_AWAITING': { name: 'Imagen Base', action: 'Generar formatos de imagen', next_name: 'Formatos de Imagen' },
        'IMAGE_FORMATS_AWAITING': { name: 'Formatos de Imagen', action: 'Generar script de video', next_name: 'Script de Video' },
        'VIDEO_PROMPT_AWAITING': { name: 'Script de Video', action: 'Generar video base', next_name: 'Video Base' },
        'VIDEO_BASE_AWAITING': { name: 'Video Base', action: 'Generar formatos de video', next_name: 'Formatos de Video' },
        'VIDEO_FORMATS_AWAITING': { name: 'Formatos de Video', action: 'Marcar como listo para publicar', next_name: 'Listo para Publicar' },
        'READY_TO_PUBLISH': { name: 'Listo para Publicar', action: 'Publicar en todas las plataformas', next_name: 'Publicado' }
    };
    return states[estado] || { name: 'Desconocido', action: 'N/A', next_name: 'N/A' };
}

// ============================================
// SELECTOR DE POSTS
// ============================================
function addPostSelector() {
    const header = document.querySelector('header');
    const existing = document.getElementById('post-selector-container');
    if (existing) existing.remove();
    
    const posts = getStoredPosts();
    if (!posts || posts.length === 0) return;
    
    const selector = document.createElement('div');
    selector.id = 'post-selector-container';
    selector.style.marginTop = '20px';
    
    selector.innerHTML = `
        <div style="display: flex; gap: 15px; align-items: flex-end;">
            <div style="flex: 1;">
                <label for="post-selector" style="display: block; margin-bottom: 10px; font-weight: bold;">📋 Seleccionar Post:</label>
                <select id="post-selector" style="padding: 10px; border-radius: 5px; border: 1px solid #ddd; width: 100%;">
                    ${posts.map((post, index) => `
                        <option value="${index}" ${index === currentPostIndex ? 'selected' : ''}>
                            ${post.codigo} - ${post.titulo}
                        </option>
                    `).join('')}
                </select>
            </div>
            <button id="create-post-btn" class="create-post-btn" title="Crear nuevo post con IA">
                ➕ Crear Nuevo Post
            </button>
        </div>
    `;
    header.appendChild(selector);
    
    document.getElementById('post-selector').addEventListener('change', (e) => {
        currentPostIndex = parseInt(e.target.value);
        loadPostData();
    });
    
    document.getElementById('create-post-btn').addEventListener('click', createNewPost);
}

function getStoredPosts() {
    const stored = localStorage.getItem('posts');
    return stored ? JSON.parse(stored) : [];
}

function createNewPost() {
    // Abrir el chat
    const modal = document.getElementById('chat-modal');
    modal.style.display = 'flex';
    
    // Esperar un momento para que el chat se abra
    setTimeout(() => {
        // Simular que el usuario escribió el mensaje
        const input = document.getElementById('chat-input');
        input.value = 'Ayúdame a crear un nuevo post';
        
        // Enviar el mensaje automáticamente
        sendChatMessage();
    }, 300);
}

// ============================================
// UTILIDADES
// ============================================
function updateCurrentDate() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('es-ES', options);
}

function calculateProgress(data) {
    const states = [
        'BASE_TEXT_AWAITING', 'ADAPTED_TEXTS_AWAITING', 'IMAGE_PROMPT_AWAITING',
        'IMAGE_BASE_AWAITING', 'IMAGE_FORMATS_AWAITING', 'VIDEO_PROMPT_AWAITING',
        'VIDEO_BASE_AWAITING', 'VIDEO_FORMATS_AWAITING', 'READY_TO_PUBLISH', 'PUBLISHED'
    ];
    const index = states.indexOf(data.estado);
    return index >= 0 ? Math.round(((index + 1) / states.length) * 100) : 0;
}

function getStatusClass(estado) {
    if (estado.includes('AWAITING')) return 'awaiting';
    if (estado.includes('APPROVED') || estado === 'PUBLISHED') return 'approved';
    if (estado.includes('PROCESSING') || estado === 'PUBLISHING') return 'processing';
    if (estado.includes('ERROR')) return 'error';
    return 'awaiting';
}

function formatStatus(estado) {
    return estado.replace(/_/g, ' ');
}

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

// Navegar a página de detalles
function viewDetails(targetState) {
    const posts = getStoredPosts();
    const post = posts[currentPostIndex];
    if (post) {
        // Si se proporciona targetState, usarlo; si no, usar el estado actual del post
        const estado = targetState || post.estado;
        window.location.href = `/details.html?codigo=${post.codigo}&estado=${estado}`;
    }
}

// ============================================
// FILTRO DE REDES SOCIALES
// ============================================

function initNetworksFilter() {
    // Solo añadir listeners, la carga se hace en loadPostData()
    const checkboxes = document.querySelectorAll('.network-checkbox input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', onNetworkChange);
    });
}

function updateNetworksFromPost(post) {
    // Cargar configuración de redes desde el post actual
    if (!post) return;
    
    const networks = {
        instagram: post.redes_instagram === 'TRUE',
        linkedin: post.redes_linkedin === 'TRUE',
        twitter: post.redes_twitter === 'TRUE',
        facebook: post.redes_facebook === 'TRUE',
        tiktok: post.redes_tiktok === 'TRUE',
        blog: post.redes_blog === 'TRUE'
    };
    
    // Aplicar a checkboxes
    Object.keys(networks).forEach(network => {
        const checkbox = document.getElementById(`network-${network}`);
        if (checkbox && network !== 'blog') {  // Blog siempre disabled
            checkbox.checked = networks[network];
        }
    });
    
    // Bloquear checkboxes si ya pasó de Fase 1
    const canEditNetworks = post.estado === 'DRAFT' || post.estado === 'BASE_TEXT_AWAITING';
    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="network-"]:not(#network-blog)');
    const warning = document.getElementById('networks-warning');
    
    checkboxes.forEach(checkbox => {
        checkbox.disabled = !canEditNetworks;
    });
    
    if (warning) {
        if (!canEditNetworks) {
            warning.style.display = 'block';
        } else {
            warning.style.display = 'none';
        }
    }
}

async function onNetworkChange() {
    // Guardar inmediatamente en Sheet cuando cambia un checkbox
    if (!currentPost) return;
    
    const networks = {
        instagram: document.getElementById('network-instagram').checked,
        linkedin: document.getElementById('network-linkedin').checked,
        twitter: document.getElementById('network-twitter').checked,
        facebook: document.getElementById('network-facebook').checked,
        tiktok: document.getElementById('network-tiktok').checked,
        blog: true  // Blog siempre activo
    };
    
    console.log('📱 Guardando configuración de redes:', networks);
    
    try {
        const response = await fetch(`${API_BASE}/posts/${currentPost.codigo}/update-networks`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ redes: networks })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Redes guardadas en Sheet');
        } else {
            console.error('❌ Error guardando redes:', result.error);
            showError('Error guardando configuración de redes');
        }
    } catch (error) {
        console.error('❌ Error:', error);
        showError('Error de conexión al guardar redes');
    }
}

function getSelectedNetworks() {
    // Leer directamente de los checkboxes del DOM (estado actual en el panel)
    const networks = {};
    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="network-"]');
    
    checkboxes.forEach(checkbox => {
        const networkName = checkbox.id.replace('network-', '');
        networks[networkName] = checkbox.checked;
    });
    
    // Si no hay checkboxes (no se han renderizado), usar valores por defecto
    if (Object.keys(networks).length === 0) {
        return {
            instagram: true,
            linkedin: true,
            twitter: true,
            facebook: true,
            tiktok: true,
            blog: true
        };
    }
    
    return networks;
}

// ============================================
// ELIMINAR POST
// ============================================

async function deletePost() {
    if (!currentPost) {
        showError('No hay post seleccionado');
        return;
    }
    
    const confirmMessage = `⚠️ ELIMINAR POST\n\n` +
                          `Post: ${currentPost.codigo}\n` +
                          `Título: ${currentPost.titulo}\n\n` +
                          `Esto eliminará:\n` +
                          `- Fila en Google Sheets\n` +
                          `- Carpeta completa en Google Drive\n` +
                          `- Todos los archivos generados\n\n` +
                          `Esta acción NO se puede deshacer.\n\n` +
                          `¿Estás seguro?`;
    
    if (!confirm(confirmMessage)) return;
    
    // Doble confirmación
    const doubleConfirm = prompt(`Para confirmar, escribe el código del post: ${currentPost.codigo}`);
    if (doubleConfirm !== currentPost.codigo) {
        showError('Código incorrecto. Eliminación cancelada.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/posts/${currentPost.codigo}/delete`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Post eliminado correctamente');
            // Recargar página para mostrar siguiente post
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showError(result.error || 'Error eliminando post');
        }
    } catch (error) {
        showError('Error de conexión');
        console.error(error);
    }
}
