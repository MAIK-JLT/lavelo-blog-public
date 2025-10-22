// Configuración
const API_BASE = 'http://localhost:5001/api';
const REFRESH_INTERVAL = 30000; // 30 segundos (reducir frecuencia)
const MOCK_MODE = false; // Desactivar modo mock - usar API real

// Estado actual
let currentPost = null;

// Datos de ejemplo para el mock
const MOCK_POSTS = [
    {
        codigo: '20251021-1',
        titulo: 'Técnicas de Respiración en Natación para Triatlón',
        idea: 'Post sobre cómo mejorar la técnica de respiración en natación para triatletas principiantes',
        estado: 'BASE_TEXT_AWAITING',
        drive_folder_id: '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    },
    {
        codigo: '20251021-2',
        titulo: 'Plan de Entrenamiento Ciclismo - Semana 3',
        idea: 'Rutina semanal de ciclismo con intervalos de alta intensidad',
        estado: 'ADAPTED_TEXTS_AWAITING',
        drive_folder_id: '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    },
    {
        codigo: '20251021-3',
        titulo: 'Nutrición Pre-Competencia en Triatlón',
        idea: 'Guía completa de alimentación 48 horas antes de una competencia',
        estado: 'IMAGE_FORMATS_AWAITING',
        drive_folder_id: '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    },
    {
        codigo: '20251021-4',
        titulo: 'Recuperación Post-Entrenamiento',
        idea: 'Técnicas de recuperación muscular después de entrenamientos intensos',
        estado: 'READY_TO_PUBLISH',
        drive_folder_id: '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    },
    {
        codigo: '20251021-5',
        titulo: 'Equipamiento Esencial para Triatlón',
        idea: 'Guía completa del equipamiento básico y avanzado para triatletas',
        estado: 'PUBLISHED',
        drive_folder_id: '1YA7uCgCL-hFy7Cjyh_SD5Z7XQ-R3EjLo'
    }
];

let currentPostIndex = 0;

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    updateCurrentDate();
    loadPostData();
    
    // Agregar selector de posts (siempre)
    setTimeout(() => {
        addPostSelector();
    }, 1000);
});

// Actualizar fecha actual
function updateCurrentDate() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('es-ES', options);
}

// Cargar datos del post activo
async function loadPostData() {
    if (MOCK_MODE) {
        // Usar datos mock desde localStorage para mantener sincronización
        const posts = getStoredPosts();
        const data = posts[currentPostIndex];
        currentPost = data;
        renderPostInfo(data);
        renderProgress(data);
        renderPhases(data);
        renderActions(data);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/posts`, {
            credentials: 'include' // Enviar cookies de sesión
        });
        const posts = await response.json();
        
        if (posts.error) {
            showError(posts.error);
            return;
        }
        
        // Guardar posts en localStorage para sincronización
        localStorage.setItem('posts', JSON.stringify(posts));
        
        // Usar el post seleccionado o el primero por defecto
        const data = posts[currentPostIndex] || posts[0];
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

// Agregar selector de posts
function addPostSelector() {
    const header = document.querySelector('header');
    
    // Evitar duplicados
    const existing = document.getElementById('post-selector-container');
    if (existing) existing.remove();
    
    const posts = getStoredPosts();
    if (!posts || posts.length === 0) {
        console.log('No hay posts para mostrar en el selector');
        return;
    }
    
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
        { id: 1, name: 'Texto Base', states: ['BASE_TEXT_AWAITING'], step: 'base', file: 'base.txt' },
        { id: 2, name: 'Textos Adaptados', states: ['ADAPTED_TEXTS_AWAITING'], step: 'texts', file: 'textos_adaptados' },
        { id: 3, name: 'Prompt Imagen', states: ['IMAGE_PROMPT_AWAITING'], step: 'image_prompt', file: 'prompt_imagen.txt' },
        { id: 4, name: 'Imagen Base', states: ['IMAGE_BASE_AWAITING'], step: 'image_base', file: 'imagen_base.png' },
        { id: 5, name: 'Formatos Imagen', states: ['IMAGE_FORMATS_AWAITING'], step: 'image_formats', file: 'formatos_imagen' },
        { id: 6, name: 'Script Video', states: ['VIDEO_PROMPT_AWAITING'], step: 'video_prompt', file: 'script_video.txt' },
        { id: 7, name: 'Video Base', states: ['VIDEO_BASE_AWAITING'], step: 'video_base', file: 'video_base.mp4' },
        { id: 8, name: 'Formatos Video', states: ['VIDEO_FORMATS_AWAITING'], step: 'video_formats', file: 'formatos_video' },
        { id: 9, name: 'Publicación', states: ['READY_TO_PUBLISH', 'PUBLISHED'], step: 'publish', file: 'resumen_completo' }
    ];
    
    phases.innerHTML = phasesData.map(phase => {
        const status = getPhaseStatus(phase, data.estado);
        const icon = status === 'completed' ? '✅' : status === 'active' ? '⏸️' : '🔒';
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

// Obtener botones para cada fase
function getPhaseButtons(phase, status, currentState) {
    if (status === 'locked') {
        return '<span style="color: #999; font-size: 12px;">🔒 Pendiente</span>';
    }
    
    if (status === 'completed') {
        return '<span style="color: #28a745; font-size: 12px; font-weight: bold;">✅ Validado</span>';
    }
    
    if (status === 'active') {
        // Botones iguales para todas las fases
        return `
            <button class="phase-btn secondary" id="check-btn-${phase.id}" onclick="checkPhase(${phase.id})">CHECK</button>
            <button class="phase-btn success" onclick="validatePhase()">VALIDATE</button>
        `;
    }
    
    return '';
}

// Obtener nombre del tipo de archivo para el botón
function getFileTypeName(fileName) {
    if (fileName.includes('.txt')) return 'Texto';
    if (fileName.includes('.png') || fileName.includes('.jpg')) return 'Imagen';
    if (fileName.includes('.mp4')) return 'Video';
    if (fileName.includes('textos_adaptados')) return 'Textos';
    if (fileName.includes('formatos_imagen')) return 'Imágenes';
    if (fileName.includes('formatos_video')) return 'Videos';
    return 'Archivo';
}

// Obtener descripción de la fase
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

// Renderizar botones de acción (ya no se usa - botones integrados en fases)
function renderActions(data) {
    const actions = document.getElementById('actions');
    actions.innerHTML = ''; // Limpiar - ahora los botones están en las fases
}

// Obtener acciones disponibles según estado
function getAvailableActions(estado) {
    const actions = {
        'BASE_TEXT_AWAITING': [
            { label: '👁️ Ver Texto Base', class: 'secondary', action: 'viewFile("base.txt")' },
            { label: '✅ Validar Texto Base', class: 'success', action: 'validateAndGenerate("base")' }
        ],
        'ADAPTED_TEXTS_AWAITING': [
            { label: '👁️ Ver Textos Adaptados', class: 'secondary', action: 'viewFile("textos_adaptados")' },
            { label: '✅ Validar Textos', class: 'success', action: 'validateAndGenerate("texts")' }
        ],
        'IMAGE_PROMPT_AWAITING': [
            { label: '👁️ Ver Prompt Imagen', class: 'secondary', action: 'viewFile("prompt_imagen.txt")' },
            { label: '✅ Validar Prompt', class: 'success', action: 'validateAndGenerate("image_prompt")' }
        ],
        'IMAGE_BASE_AWAITING': [
            { label: '👁️ Ver Imagen Base', class: 'secondary', action: 'viewFile("imagen_base.png")' },
            { label: '✅ Validar Imagen', class: 'success', action: 'validateAndGenerate("image_base")' }
        ],
        'IMAGE_FORMATS_AWAITING': [
            { label: '👁️ Ver Formatos Imagen', class: 'secondary', action: 'viewFile("formatos_imagen")' },
            { label: '✅ Validar Formatos', class: 'success', action: 'validateAndGenerate("image_formats")' }
        ],
        'VIDEO_PROMPT_AWAITING': [
            { label: '👁️ Ver Script Video', class: 'secondary', action: 'viewFile("script_video.txt")' },
            { label: '✅ Validar Script', class: 'success', action: 'validateAndGenerate("video_prompt")' }
        ],
        'VIDEO_BASE_AWAITING': [
            { label: '👁️ Ver Video Base', class: 'secondary', action: 'viewFile("video_base.mp4")' },
            { label: '✅ Validar Video', class: 'success', action: 'validateAndGenerate("video_base")' }
        ],
        'VIDEO_FORMATS_AWAITING': [
            { label: '👁️ Ver Formatos Video', class: 'secondary', action: 'viewFile("formatos_video")' },
            { label: '✅ Validar Formatos', class: 'success', action: 'validateAndGenerate("video_formats")' }
        ],
        'READY_TO_PUBLISH': [
            { label: '👁️ Revisar Todo', class: 'secondary', action: 'viewFile("resumen_completo")' },
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
    if (MOCK_MODE) {
        // Simular acción en modo mock
        showLoading();
        
        // Simular delay de procesamiento
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Simular progreso del estado
        const nextState = getNextState(currentPost.estado);
        if (nextState) {
            MOCK_POSTS[currentPostIndex].estado = nextState;
            showSuccess(`✅ Acción completada. Estado: ${formatStatus(nextState)}`);
            setTimeout(loadPostData, 1000);
        } else {
            showSuccess('✅ Acción simulada completada');
        }
        
        hideLoading();
        return;
    }
    
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

// Obtener siguiente estado para simulación
function getNextState(currentState) {
    const stateFlow = {
        'BASE_TEXT_AWAITING': 'ADAPTED_TEXTS_AWAITING',
        'ADAPTED_TEXTS_AWAITING': 'IMAGE_PROMPT_AWAITING',
        'IMAGE_PROMPT_AWAITING': 'IMAGE_BASE_AWAITING',
        'IMAGE_BASE_AWAITING': 'IMAGE_FORMATS_AWAITING',
        'IMAGE_FORMATS_AWAITING': 'VIDEO_PROMPT_AWAITING',
        'VIDEO_PROMPT_AWAITING': 'VIDEO_BASE_AWAITING',
        'VIDEO_BASE_AWAITING': 'VIDEO_FORMATS_AWAITING',
        'VIDEO_FORMATS_AWAITING': 'READY_TO_PUBLISH',
        'READY_TO_PUBLISH': 'PUBLISHED'
    };
    return stateFlow[currentState] || null;
}

// Funciones para ver archivos
function viewFile(fileName) {
    // Siempre usar la pantalla de detalle
    const detailUrl = `detail.html?post=${currentPostIndex}&type=${fileName}`;
    window.location.href = detailUrl;
}

// CHECK: Marcar fase como revisada (cambia botón a OK ✓)
function checkPhase(phaseId) {
    const btn = document.getElementById(`check-btn-${phaseId}`);
    if (btn) {
        btn.innerHTML = 'OK ✓';
        btn.style.background = '#28a745';
        btn.style.color = 'white';
        btn.disabled = true;
    }
}

// VALIDATE: Validar fase actual y avanzar al siguiente estado
async function validatePhase() {
    if (!currentPost) {
        showError('No hay post seleccionado');
        return;
    }
    
    // Obtener información del estado actual
    const stateInfo = getStateInfo(currentPost.estado);
    
    // Mostrar popup con información
    const message = `📋 VALIDACIÓN\n\n` +
                   `Estado actual: ${stateInfo.name}\n` +
                   `Acción: ${stateInfo.action}\n\n` +
                   `Siguiente estado: ${stateInfo.next_name}\n\n` +
                   `¿Continuar?`;
    
    if (!confirm(message)) return;
    
    // Cambiar estado visual del botón
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
            // Solo recargar, sin popup adicional
            loadPostData();
        } else {
            showError(result.error || 'Error desconocido');
            // Restaurar botón si hay error
            if (validateBtn) {
                validateBtn.disabled = false;
                validateBtn.style.opacity = '1';
                validateBtn.innerHTML = 'VALIDATE';
            }
        }
    } catch (error) {
        showError('Error de conexión');
        console.error(error);
        // Restaurar botón si hay error
        if (validateBtn) {
            validateBtn.disabled = false;
            validateBtn.style.opacity = '1';
            validateBtn.innerHTML = 'VALIDATE';
        }
    }
}

// Obtener información del estado
function getStateInfo(estado) {
    const states = {
        'BASE_TEXT_AWAITING': {
            name: 'Texto Base',
            action: 'Generar textos adaptados para redes sociales',
            next_name: 'Textos Adaptados'
        },
        'ADAPTED_TEXTS_AWAITING': {
            name: 'Textos Adaptados',
            action: 'Generar prompt de imagen',
            next_name: 'Prompt de Imagen'
        },
        'IMAGE_PROMPT_AWAITING': {
            name: 'Prompt de Imagen',
            action: 'Generar imagen base',
            next_name: 'Imagen Base'
        },
        'IMAGE_BASE_AWAITING': {
            name: 'Imagen Base',
            action: 'Generar formatos de imagen',
            next_name: 'Formatos de Imagen'
        },
        'IMAGE_FORMATS_AWAITING': {
            name: 'Formatos de Imagen',
            action: 'Generar script de video',
            next_name: 'Script de Video'
        },
        'VIDEO_PROMPT_AWAITING': {
            name: 'Script de Video',
            action: 'Generar video base',
            next_name: 'Video Base'
        },
        'VIDEO_BASE_AWAITING': {
            name: 'Video Base',
            action: 'Generar formatos de video',
            next_name: 'Formatos de Video'
        },
        'VIDEO_FORMATS_AWAITING': {
            name: 'Formatos de Video',
            action: 'Marcar como listo para publicar',
            next_name: 'Listo para Publicar'
        },
        'READY_TO_PUBLISH': {
            name: 'Listo para Publicar',
            action: 'Publicar en todas las plataformas',
            next_name: 'Publicado'
        }
    };
    
    return states[estado] || { name: 'Desconocido', action: 'N/A', next_name: 'N/A' };
}

// Obtener mensaje de confirmación para validación
function getValidationMessage(step) {
    const messages = {
        'base': '¿Validar el texto base y generar textos adaptados para redes sociales?',
        'texts': '¿Validar los textos adaptados y generar prompt de imagen?',
        'image_prompt': '¿Validar el prompt de imagen y generar imagen base?',
        'image_base': '¿Validar la imagen base y generar formatos para redes sociales?',
        'image_formats': '¿Validar los formatos de imagen y generar script de video?',
        'video_prompt': '¿Validar el script de video y generar video base?',
        'video_base': '¿Validar el video base y generar formatos para redes sociales?',
        'video_formats': '¿Validar los formatos de video y marcar como listo para publicar?'
    };
    return messages[step] || '¿Proceder con la validación?';
}

// ELIMINADO: Ya no necesitamos mapear steps a endpoints
// Ahora usamos un único endpoint /validate-phase

// Simular validación y generación
async function simulateValidationAndGeneration(step) {
    showLoading();
    
    // Simular delay de procesamiento
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Avanzar al siguiente estado
    const nextState = getNextState(currentPost.estado);
    if (nextState) {
        // Actualizar en localStorage para mantener sincronización
        const posts = getStoredPosts();
        posts[currentPostIndex].estado = nextState;
        localStorage.setItem('mockPosts', JSON.stringify(posts));
        
        const stepName = getStepName(step);
        showSuccess(`✅ ${stepName} validado y siguiente paso generado automáticamente`);
        setTimeout(loadPostData, 1000);
    }
    
    hideLoading();
}

// Obtener nombre del paso para mensajes
function getStepName(step) {
    const names = {
        'base': 'Texto base',
        'texts': 'Textos adaptados',
        'image_prompt': 'Prompt de imagen',
        'image_base': 'Imagen base',
        'image_formats': 'Formatos de imagen',
        'video_prompt': 'Script de video',
        'video_base': 'Video base',
        'video_formats': 'Formatos de video'
    };
    return names[step] || 'Elemento';
}

// Funciones de acción (legacy - mantener por compatibilidad)
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
        'BASE_TEXT_AWAITING', 'ADAPTED_TEXTS_AWAITING', 'IMAGE_PROMPT_AWAITING',
        'IMAGE_BASE_AWAITING', 'IMAGE_FORMATS_AWAITING', 'VIDEO_PROMPT_AWAITING',
        'VIDEO_BASE_AWAITING', 'VIDEO_FORMATS_AWAITING', 'READY_TO_PUBLISH', 'PUBLISHED'
    ];
    const index = states.indexOf(data.estado);
    return index >= 0 ? Math.round(((index + 1) / states.length) * 100) : 0;
}

function getPhaseStatus(phase, currentState) {
    // Mapeo de estados a fases
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

// Loading visual eliminado - ahora se muestra en el botón VALIDATE

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

// Obtener posts almacenados o usar datos por defecto
function getStoredPosts() {
    // En modo real, usar posts de la API
    if (!MOCK_MODE) {
        const stored = localStorage.getItem('posts');
        if (stored) {
            return JSON.parse(stored);
        }
        return [];
    }
    
    // En modo mock
    const stored = localStorage.getItem('mockPosts');
    if (stored) {
        return JSON.parse(stored);
    }
    
    // Usar datos por defecto y guardarlos
    localStorage.setItem('mockPosts', JSON.stringify(MOCK_POSTS));
    return MOCK_POSTS;
}
