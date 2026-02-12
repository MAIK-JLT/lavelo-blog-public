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
        // Timeout de 120 segundos para respuestas largas
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                message: message,
                history: chatHistory
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (response.status === 401) {
            window.location.href = '/panel/login.html';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Chat response:', data);
        
        // Ocultar loading
        hideChatLoading();
        
        if (data.success) {
            // Añadir respuesta del asistente
            const assistantMessage = data.response || data.message;
            addMessage('assistant', assistantMessage);
            
            // Actualizar historial
            chatHistory.push({
                role: 'user',
                content: message
            });
            chatHistory.push({
                role: 'assistant',
                content: assistantMessage
            });
            
            // Si se usó una herramienta, manejar según el tipo
            if (data.tool_used === 'create_post') {
                if (data.post_url) {
                    addMessage('assistant', `✅ Terminado. [Ir al post](${data.post_url})`);
                } else {
                    addMessage('assistant', '✅ Terminado. Ya puedes ver el post en el panel.');
                }
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
    
    // Renderizar Markdown a HTML
    bubble.innerHTML = formatMarkdown(content);
    
    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll al final
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // Escapar HTML para seguridad
    text = text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');
    
    // Convertir Markdown a HTML
    return text
        // Headers (deben ir antes de otros reemplazos)
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        // Bold y cursiva
        .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Listas
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>')
        // Code blocks
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Links
        .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Saltos de línea (dobles para párrafos, simples para <br>)
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        // Envolver en párrafo
        .replace(/^(.+)$/gim, '<p>$1</p>')
        // Limpiar párrafos vacíos
        .replace(/<p><\/p>/g, '')
        .replace(/<p><br><\/p>/g, '<br>');
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
