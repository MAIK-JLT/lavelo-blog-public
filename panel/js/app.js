// ============================================
// CONFIGURACIÓN
// ============================================
const API_BASE = 'http://localhost:5001/api';
let currentPost = null;
let currentPostIndex = 0;

// ============================================
// INICIALIZACIÓN
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Restaurar índice del post si viene de details
    const savedIndex = localStorage.getItem('currentPostIndex');
    if (savedIndex !== null) {
        currentPostIndex = parseInt(savedIndex);
        localStorage.removeItem('currentPostIndex'); // Limpiar después de usar
    }
    
    updateCurrentDate();
    loadPostData();
    setTimeout(() => addPostSelector(), 1000);
});

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
        renderProgress(data);
        renderPhases(data);
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
        <h2>📄 ${data.titulo || 'Sin título'}</h2>
        <p><strong>Código:</strong> ${data.codigo}</p>
        <p><strong>Idea:</strong> ${data.idea || 'Sin descripción'}</p>
        <span class="status ${statusClass}">${formatStatus(data.estado)}</span>
        ${data.drive_folder_id ? `<p style="margin-top: 10px;"><a href="https://drive.google.com/drive/folders/${data.drive_folder_id}" target="_blank">📁 Ver en Drive</a></p>` : ''}
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
    
    if (status === 'completed') {
        return '<span style="color: #28a745; font-size: 12px; font-weight: bold;">✅ Validado</span>';
    }
    
    if (status === 'active') {
        return `
            <button class="phase-btn secondary" onclick="viewDetails()">📋 Ver Detalles</button>
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
        const response = await fetch(`${API_BASE}/validate-phase`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                codigo: currentPost.codigo,
                current_state: currentPost.estado
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
        <label for="post-selector" style="display: block; margin-bottom: 10px; font-weight: bold;">📋 Seleccionar Post:</label>
        <select id="post-selector" style="padding: 10px; border-radius: 5px; border: 1px solid #ddd; width: 100%; max-width: 400px;">
            ${posts.map((post, index) => `
                <option value="${index}" ${index === currentPostIndex ? 'selected' : ''}>
                    ${post.codigo} - ${post.titulo}
                </option>
            `).join('')}
        </select>
    `;
    header.appendChild(selector);
    
    document.getElementById('post-selector').addEventListener('change', (e) => {
        currentPostIndex = parseInt(e.target.value);
        loadPostData();
    });
}

function getStoredPosts() {
    const stored = localStorage.getItem('posts');
    return stored ? JSON.parse(stored) : [];
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
function viewDetails() {
    const posts = getStoredPosts();
    const post = posts[currentPostIndex];
    if (post) {
        window.location.href = `/details.html?codigo=${post.codigo}`;
    }
}
