// Configuración de APIs
// IMPORTANTE: API keys NUNCA van aquí - solo en variables de entorno

const CONFIG = {
    // API keys se obtienen del backend por seguridad
    GEMINI_API_KEY: null, // Se obtiene del servidor
    
    // URLs de las APIs
    GEMINI_API_URL: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent',
    
    // Configuración de generación
    IMAGE_GENERATION: {
        model: 'gemini-2.5-flash-image',
        maxPromptLength: 2000,
        defaultFormat: '16:9',
        quality: 'high'
    }
};

// Exportar configuración
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
} else {
    window.CONFIG = CONFIG;
}
