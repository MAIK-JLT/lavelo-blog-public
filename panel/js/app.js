// Configuración
const API_BASE = '/api';
const REFRESH_INTERVAL = 5000; // 5 segundos

// Estado actual
let currentPost = null;

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    updateCurrentDate();
    loadPostData();
    setInterval(loadPostData, REFRESH_INTERVAL);
});

// Actualizar fecha actual
function updateCurrentDate() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('es-ES', options);
}

// Cargar datos del post activo
async function loadPostData() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        currentPost = data;
        renderPostInfo(data);
        renderProgress(data);
        renderPhases(data);
        renderActions(data);
        
    } catch (error) {
        showError('Error al cargar datos del servidor');
        console.error(error);
    }
}

// Renderizar información del post
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

// Renderizar barra de progreso
function renderProgress(data) {
    const progress = document.getElementById('progress');
    const percentage = calculateProgress(data);
    progress.style.width = `${percentage}%`;
    progress.textContent = `${percentage}%`;
}

// Renderizar fases
function renderPhases(data) {
    const phases = document.getElementById('phases');
    const phasesData = [
        { id: 1, name: 'Texto Base', states: ['BASE_TEXT_AWAITING', 'BASE_TEXT_APPROVED'] },
        { id: 2, name: 'Textos Adaptados', states: ['ADAPTED_TEXTS_AWAITING', 'TEXTS_APPROVED'] },
        { id: 3, name: 'Prompt Imagen', states: ['IMAGE_PROMPT_AWAITING', 'IMAGE_PROMPT_APPROVED'] },
        { id: 4, name: 'Imagen Base', states: ['IMAGE_BASE_AWAITING', 'IMAGE_BASE_APPROVED'] },
        { id: 5, name: 'Formatos Imagen', states: ['IMAGE_FORMATS_AWAITING', 'IMAGES_APPROVED'] },
        { id: 6, name: 'Prompt Video', states: ['VIDEO_PROMPT_AWAITING', 'VIDEO_PROMPT_APPROVED'] },
        { id: 7, name: 'Video Base', states: ['VIDEO_BASE_AWAITING', 'VIDEO_BASE_APPROVED'] },
        { id: 8, name: 'Formatos Video', states: ['VIDEO_FORMATS_AWAITING', 'READY_TO_PUBLISH'] },
        { id: 9, name: 'Publicación', states: ['PUBLISHING', 'PUBLISHED'] }
    ];
    
    phases.innerHTML = phasesData.map(phase => {
        const status = getPhaseStatus(phase, data.estado);
        const icon = status === 'completed' ? '✅' : status === 'active' ? '⏸️' : '🔒';
        return `
            <div class="phase ${status}">
                <h3>${icon} Fase ${phase.id}: ${phase.name}</h3>
            </div>
        `;
    }).join('');
}

// Renderizar botones de acción
function renderActions(data) {
    const actions = document.getElementById('actions');
    const buttons = getAvailableActions(data.estado);
    
    actions.innerHTML = buttons.map(btn => `
        <button class="${btn.class}" onclick="${btn.action}">
            ${btn.label}
        </button>
    `).join('');
}

// Obtener acciones disponibles según estado
function getAvailableActions(estado) {
    const actions = {
        'BASE_TEXT_APPROVED': [
            { label: '▶️ Generar Textos Adaptados', class: 'primary', action: 'generateAdaptedTexts()' }
        ],
        'TEXTS_APPROVED': [
            { label: '▶️ Generar Prompt Imagen', class: 'primary', action: 'generateImagePrompt()' }
        ],
        'IMAGE_PROMPT_APPROVED': [
            { label: '▶️ Generar Imagen Base', class: 'primary', action: 'generateBaseImage()' }
        ],
        'IMAGE_BASE_APPROVED': [
            { label: '▶️ Formatear Imágenes', class: 'primary', action: 'formatImages()' }
        ],
        'IMAGES_APPROVED': [
            { label: '▶️ Generar Script Video', class: 'primary', action: 'generateVideoScript()' }
        ],
        'VIDEO_PROMPT_APPROVED': [
            { label: '▶️ Generar Video Base', class: 'primary', action: 'generateBaseVideo()' }
        ],
        'VIDEO_BASE_APPROVED': [
            { label: '▶️ Formatear Videos', class: 'primary', action: 'formatVideos()' }
        ],
        'READY_TO_PUBLISH': [
            { label: '🚀 Publicar Ahora', class: 'success', action: 'publishNow()' }
        ],
        'PUBLISHED': [
            { label: '✅ Completado', class: 'success', action: '', disabled: true }
        ]
    };
    
    return actions[estado] || [
        { label: '⏸️ Esperando validación...', class: 'secondary', action: '', disabled: true }
    ];
}

// Acciones del API
async function callAPI(endpoint, method = 'POST') {
    try {
        showLoading();
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo: currentPost.codigo })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showSuccess(result.message);
            setTimeout(loadPostData, 2000);
        } else {
            showError(result.error || 'Error desconocido');
        }
    } catch (error) {
        hideLoading();
        showError('Error de conexión con el servidor');
        console.error(error);
    }
}

// Funciones de acción
function generateAdaptedTexts() { callAPI('/generate-texts'); }
function generateImagePrompt() { callAPI('/generate-image-prompt'); }
function generateBaseImage() { callAPI('/generate-image'); }
function formatImages() { callAPI('/format-images'); }
function generateVideoScript() { callAPI('/generate-video-script'); }
function generateBaseVideo() { callAPI('/generate-video'); }
function formatVideos() { callAPI('/format-videos'); }
function publishNow() { 
    if (confirm('¿Publicar en todas las plataformas ahora?')) {
        callAPI('/publish'); 
    }
}

// Utilidades
function calculateProgress(data) {
    const states = [
        'BASE_TEXT_APPROVED', 'TEXTS_APPROVED', 'IMAGE_PROMPT_APPROVED',
        'IMAGE_BASE_APPROVED', 'IMAGES_APPROVED', 'VIDEO_PROMPT_APPROVED',
        'VIDEO_BASE_APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'
    ];
    const index = states.indexOf(data.estado);
    return index >= 0 ? Math.round(((index + 1) / states.length) * 100) : 0;
}

function getPhaseStatus(phase, currentState) {
    const stateIndex = phase.states.indexOf(currentState);
    if (stateIndex === phase.states.length - 1) return 'completed';
    if (stateIndex >= 0) return 'active';
    return 'locked';
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

function showLoading() {
    document.body.style.cursor = 'wait';
}

function hideLoading() {
    document.body.style.cursor = 'default';
}

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}
