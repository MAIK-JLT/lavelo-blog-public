// Chat con IA
let chatHistory = [];
let isProcessing = false;
let chatInitialized = false; // Para saber si ya mostramos el mensaje de bienvenida

function toggleChat() {
    const modal = document.getElementById('chat-modal');
    if (modal.style.display === 'none' || !modal.style.display) {
        modal.style.display = 'flex';
        document.getElementById('chat-input').focus();
    } else {
        modal.style.display = 'none';
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message || isProcessing) return;
    
    // Añadir mensaje del usuario
    addMessage('user', message);
    input.value = '';
    isProcessing = true;
    
    // Mostrar loading
    showChatLoading();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: chatHistory
            })
        });
        
        const data = await response.json();
        
        // Ocultar loading
        hideChatLoading();
        
        if (data.success) {
            // Añadir respuesta del asistente
            addMessage('assistant', data.message);
            
            // Actualizar historial
            chatHistory.push({
                role: 'user',
                content: message
            });
            chatHistory.push({
                role: 'assistant',
                content: data.message
            });
            
            // Si se usó una herramienta, recargar según el tipo
            if (data.tool_used === 'create_post') {
                setTimeout(() => {
                    if (typeof loadPostData === 'function') {
                        loadPostData(); // Recargar datos y actualizar selector
                    } else {
                        location.reload(); // Fallback: recargar página completa
                    }
                }, 1000);
            } else if (data.tool_used === 'regenerate_image') {
                // Regenerar imagen: volver al panel principal
                addMessage('assistant', '🎯 Volviendo al panel principal para regenerar...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else if (data.tool_used === 'update_image_prompt' || data.tool_used === 'update_video_script') {
                // Mostrar mensaje de éxito y sugerir recarga
                addMessage('assistant', '💡 Recarga la página para ver los cambios aplicados.');
            }
        } else {
            addMessage('assistant', `❌ Error: ${data.error || 'Error desconocido'}`);
        }
        
    } catch (error) {
        hideChatLoading();
        addMessage('assistant', `❌ Error de conexión: ${error.message}`);
    } finally {
        isProcessing = false;
    }
}

function addMessage(role, content) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;
    
    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll al final
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showChatLoading() {
    const messagesContainer = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'chat-loading';
    loadingDiv.className = 'chat-loading';
    loadingDiv.innerHTML = '<div class="spinner"></div> <span>Pensando...</span>';
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideChatLoading() {
    const loading = document.getElementById('chat-loading');
    if (loading) {
        loading.remove();
    }
}

// Enter para enviar
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('chat-input');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
    
    // Mensaje de bienvenida SOLO la primera vez
    if (!chatInitialized) {
        setTimeout(() => {
            addMessage('assistant', '¡Hola! 👋 Soy tu asistente de IA. Puedo ayudarte a crear posts para tu blog. ¿Sobre qué quieres escribir?');
            chatInitialized = true;
        }, 500);
    }
});
