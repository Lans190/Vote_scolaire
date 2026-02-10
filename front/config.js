// config.js - Configuration multi-environnements
const CONFIG = {
    // Environnements disponibles
    ENVIRONMENTS: {
        PRODUCTION: {
            name: 'production',
            apiBaseUrl: 'https://vote-scolaire.onrender.com',
            debug: false
        },
        DEVELOPMENT: {
            name: 'development',
            apiBaseUrl: 'http://localhost:10000',
            debug: true
        },
        TEST: {
            name: 'test',
            apiBaseUrl: 'http://localhost:10000',
            debug: true
        }
    },
    
    // Détection automatique de l'environnement
    detectEnvironment: function() {
        const hostname = window.location.hostname;
        
        // Render
        if (hostname.includes('render.com') || hostname.includes('onrender.com')) {
            return this.ENVIRONMENTS.PRODUCTION;
        }
        
        // Localhost
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
            return this.ENVIRONMENTS.DEVELOPMENT;
        }
        
        // Par défaut, production
        return this.ENVIRONMENTS.PRODUCTION;
    },
    
    // Configuration courante
    current: null,
    
    // Initialiser
    init: function() {
        this.current = this.detectEnvironment();
        this.logConfig();
        return this.current;
    },
    
    // Logger la configuration
    logConfig: function() {
        console.log('⚙️  CONFIGURATION DU SYSTÈME DE VOTE');
        console.log('========================================');
        console.log(`🎯 Environnement: ${this.current.name.toUpperCase()}`);
        console.log(`🌐 URL: ${window.location.href}`);
        console.log(`🔗 API: ${this.current.apiBaseUrl}`);
        console.log(`🐛 Debug: ${this.current.debug ? 'ACTIVÉ' : 'DÉSACTIVÉ'}`);
        console.log('========================================\n');
    },
    
    // API Endpoints
    getApiEndpoints: function() {
        const base = this.current.apiBaseUrl;
        return {
            election: `${base}/api/election`,
            vote: `${base}/api/vote`,
            verify: `${base}/api/verify-email`,
            status: `${base}/api/status`,
            results: `${base}/api/results`,
            stats: `${base}/api/stats`,
            reset: `${base}/api/reset-votes`
        };
    },
    
    // Tester la connexion API
    testConnection: async function() {
        try {
            const endpoints = this.getApiEndpoints();
            console.log('🔍 Test de connexion API...');
            
            const response = await fetch(endpoints.status, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ API Connectée:', {
                status: data.system?.status,
                ecole: data.system?.ecole,
                version: data.system?.version,
                election: data.election?.status
            });
            
            return {
                success: true,
                data: data,
                endpoint: endpoints.status
            };
            
        } catch (error) {
            console.error('❌ Échec connexion API:', error);
            return {
                success: false,
                error: error.message,
                endpoint: this.getApiEndpoints().status
            };
        }
    }
};

// Initialiser et exporter
CONFIG.init();
window.APP_CONFIG = CONFIG.current;
window.API_ENDPOINTS = CONFIG.getApiEndpoints();
window.CONFIG = CONFIG;

// Exporter pour les tests
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}