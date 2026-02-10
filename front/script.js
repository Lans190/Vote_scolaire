// ==================== CONFIGURATION ====================
// Utiliser la configuration globale
const API_BASE_URL = window.APP_CONFIG.apiBaseUrl;
const API_ENDPOINTS = window.API_ENDPOINTS;
const IS_DEBUG = window.APP_CONFIG.debug;

console.log('🚀 Script principal chargé');
console.log(`🔗 API Base: ${API_BASE_URL}`);

// ==================== ÉLÉMENTS DOM ====================
const elements = {
    // Sections principales
    emailSection: document.getElementById('emailSection'),
    candidatesSection: document.getElementById('candidatesSection'),
    confirmationSection: document.getElementById('confirmationSection'),
    alreadyVotedSection: document.getElementById('alreadyVotedSection'),
    errorSection: document.getElementById('errorSection'),
    
    // Email
    emailInput: document.getElementById('emailInput'),
    verifyBtn: document.getElementById('verifyBtn'),
    emailError: document.getElementById('emailError'),
    
    // Candidates
    candidatesGrid: document.getElementById('candidatesGrid'),
    selectedCandidatePanel: document.getElementById('selectedCandidate'),
    selectedInfo: document.getElementById('selectedInfo'),
    voteBtn: document.getElementById('voteBtn'),
    loadingCandidates: document.getElementById('loadingCandidates'),
    
    // Confirmation
    confirmationId: document.getElementById('confirmationId'),
    confirmationEmail: document.getElementById('confirmationEmail'),
    confirmationTime: document.getElementById('confirmationTime'),
    voteTimestamp: document.getElementById('voteTimestamp'),
    
    // Modals
    confirmationModal: document.getElementById('confirmationModal'),
    confirmCandidate: document.getElementById('confirmCandidate'),
    confirmVoteBtn: document.getElementById('confirmVoteBtn'),
    
    // Status
    statusMessage: document.getElementById('statusMessage'),
    timeRemaining: document.getElementById('timeRemaining'),
    votesCount: document.getElementById('votesCount'),
    participationRate: document.getElementById('participationRate'),
    
    // Loader
    globalLoader: document.getElementById('globalLoader'),
    loaderMessage: document.getElementById('loaderMessage')
};

// ==================== ÉTAT GLOBAL ====================
let state = {
    userEmail: null,
    selectedCandidateId: null,
    selectedCandidate: null,
    candidates: [],
    hasVoted: false,
    electionStatus: '',
    currentElection: null
};

// ==================== INITIALISATION ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('📱 Page chargée, initialisation...');
    
    // Tester la connexion
    const connection = await window.CONFIG.testConnection();
    
    if (!connection.success) {
        showError('Connexion impossible', 'Le serveur ne répond pas. Réessayez plus tard.');
        return;
    }
    
    // Vérifier vote précédent
    checkPreviousVote();
    
    // Charger statut système
    await loadSystemStatus();
    
    // Configurer événements
    setupEventListeners();
    
    console.log('✅ Système prêt');
    showStatus('✅ Système connecté • Prêt pour le vote', 'success');
});

// ==================== FONCTIONS UTILITAIRES ====================
function showSection(sectionId) {
    // Cacher toutes les sections
    ['emailSection', 'candidatesSection', 'confirmationSection', 'alreadyVotedSection', 'errorSection']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    
    // Afficher la section demandée
    const section = document.getElementById(sectionId);
    if (section) {
        section.style.display = 'block';
        if (IS_DEBUG) console.log(`📱 Affichage section: ${sectionId}`);
    }
}

function showLoader(message = 'Chargement...') {
    if (elements.globalLoader && elements.loaderMessage) {
        elements.loaderMessage.textContent = message;
        elements.globalLoader.style.display = 'flex';
    }
}

function hideLoader() {
    if (elements.globalLoader) {
        elements.globalLoader.style.display = 'none';
    }
}

function showStatus(message, type = 'info') {
    if (elements.statusMessage) {
        elements.statusMessage.textContent = message;
        
        // Couleur selon type
        const colors = {
            info: '#4361ee',
            success: '#2ecc71',
            warning: '#f39c12',
            error: '#e74c3c'
        };
        
        if (elements.statusBanner && colors[type]) {
            elements.statusBanner.style.borderLeftColor = colors[type];
        }
    }
}

function showError(title, message) {
    console.error(`❌ ${title}: ${message}`);
    showStatus(`❌ ${title}`, 'error');
    
    if (elements.errorSection) {
        document.getElementById('errorTitle').textContent = title;
        document.getElementById('errorMessage').textContent = message;
        showSection('errorSection');
    }
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function formatDateTime(date) {
    if (!date) return '--';
    return new Date(date).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================== GESTION ÉTAT UTILISATEUR ====================
function checkPreviousVote() {
    const savedEmail = localStorage.getItem('vote_email_2026');
    const savedHasVoted = localStorage.getItem('has_voted_2026');
    
    if (savedEmail && savedHasVoted === 'true') {
        state.userEmail = savedEmail;
        state.hasVoted = true;
        
        if (elements.voteTimestamp) {
            const savedTimestamp = localStorage.getItem('vote_timestamp_2026');
            elements.voteTimestamp.textContent = savedTimestamp 
                ? `Vote enregistré le ${formatDateTime(savedTimestamp)}`
                : 'Vous avez déjà voté';
        }
        
        showSection('alreadyVotedSection');
        showStatus('✅ Vous avez déjà voté', 'info');
        return true;
    }
    
    return false;
}

function saveVoteState(email, timestamp = null) {
    localStorage.setItem('vote_email_2026', email);
    localStorage.setItem('has_voted_2026', 'true');
    localStorage.setItem('vote_timestamp_2026', timestamp || new Date().toISOString());
    state.hasVoted = true;
}

function clearUserSession() {
    state.userEmail = null;
    state.selectedCandidateId = null;
    state.selectedCandidate = null;
    state.hasVoted = false;
    
    localStorage.removeItem('vote_email_2026');
    localStorage.removeItem('has_voted_2026');
    localStorage.removeItem('vote_timestamp_2026');
    localStorage.removeItem('vote_candidate_id_2026');
    
    if (elements.emailInput) {
        elements.emailInput.value = '';
    }
    
    showSection('emailSection');
    showStatus('👋 Session réinitialisée', 'info');
}

// ==================== FONCTIONS API ====================
async function loadSystemStatus() {
    try {
        const response = await fetch(API_ENDPOINTS.status);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        state.currentElection = data.election;
        state.electionStatus = data.election?.status || 'inactive';
        
        // Mettre à jour l'affichage
        if (elements.timeRemaining && data.election?.temps_restant) {
            elements.timeRemaining.textContent = data.election.temps_restant;
        }
        
        if (elements.votesCount && data.statistics?.votes !== undefined) {
            elements.votesCount.textContent = data.statistics.votes;
        }
        
        if (elements.participationRate && data.statistics?.participation_rate !== undefined) {
            elements.participationRate.textContent = `${data.statistics.participation_rate}%`;
        }
        
        return data;
        
    } catch (error) {
        console.error('Erreur chargement statut:', error);
        throw error;
    }
}

// ==================== VÉRIFICATION EMAIL ====================
async function verifyEmail() {
    const email = elements.emailInput?.value.trim().toLowerCase();
    
    if (!email) {
        showEmailError('Veuillez entrer votre email');
        return;
    }
    
    if (!validateEmail(email)) {
        showEmailError('Format d\'email invalide (ex: nom@lasourcedelafontaine.fr)');
        return;
    }
    
    showLoader('Vérification en cours...');
    state.userEmail = email;
    
    try {
        const response = await fetch(API_ENDPOINTS.verify, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Erreur serveur: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showEmailError(data.error);
            return;
        }
        
        state.hasVoted = data.has_voted;
        
        if (state.hasVoted) {
            saveVoteState(email, data.vote_date);
            showSection('alreadyVotedSection');
            showStatus('✅ Vous avez déjà voté', 'info');
        } else {
            if (data.can_vote) {
                await loadCandidates();
                showSection('candidatesSection');
                showStatus('✅ Email validé • Sélectionnez une candidate', 'success');
            } else {
                showEmailError(data.message || 'La période de vote n\'est pas active');
                showStatus('⏸️ Vote non disponible', 'warning');
            }
        }
        
    } catch (error) {
        console.error('Erreur vérification:', error);
        showEmailError('Erreur de connexion: ' + error.message);
        showStatus('❌ Erreur de vérification', 'error');
    } finally {
        hideLoader();
    }
}

function showEmailError(message) {
    if (elements.emailError) {
        elements.emailError.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        elements.emailError.style.display = 'block';
    }
}

// ==================== GESTION CANDIDATES ====================
async function loadCandidates() {
    try {
        showLoader('Chargement des candidates...');
        
        const response = await fetch(API_ENDPOINTS.election);
        if (!response.ok) throw new Error(`Erreur: ${response.status}`);
        
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        
        state.candidates = data.candidates || [];
        state.currentElection = data;
        
        if (state.candidates.length === 0) {
            throw new Error('Aucune candidate disponible');
        }
        
        displayCandidates(state.candidates);
        
    } catch (error) {
        console.error('Erreur chargement candidates:', error);
        showError('Liste non disponible', 'Impossible de charger les candidates');
    } finally {
        hideLoader();
    }
}

function displayCandidates(candidatesList) {
    if (!elements.candidatesGrid) return;
    
    elements.candidatesGrid.innerHTML = '';
    
    if (elements.loadingCandidates) {
        elements.loadingCandidates.style.display = 'none';
    }
    
    // Trier par classe
    const classOrder = ['2nde', '3ème', '4ème', '5ème', '6ème'];
    candidatesList.sort((a, b) => classOrder.indexOf(a.classe) - classOrder.indexOf(b.classe));
    
    candidatesList.forEach(candidate => {
        const card = createCandidateCard(candidate);
        elements.candidatesGrid.appendChild(card);
    });
}

function createCandidateCard(candidate) {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.dataset.id = candidate.id;
    card.dataset.classe = candidate.classe;
    
    // Initiales
    const initials = (candidate.prenom?.charAt(0) || '') + (candidate.nom?.charAt(0) || '');
    
    // Couleur par classe
    const colors = {
        '2nde': 'linear-gradient(135deg, #4361ee, #3a0ca3)',
        '3ème': 'linear-gradient(135deg, #4cc9f0, #3a86ff)',
        '4ème': 'linear-gradient(135deg, #7209b7, #560bad)',
        '5ème': 'linear-gradient(135deg, #f72585, #b5179e)',
        '6ème': 'linear-gradient(135deg, #2ecc71, #27ae60)'
    };
    
    const color = colors[candidate.classe] || 'linear-gradient(135deg, #6c757d, #495057)';
    
    card.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${color}">
                ${initials.toUpperCase()}
            </div>
            <div class="candidate-info">
                <h3>${candidate.prenom} ${candidate.nom}</h3>
                <div class="candidate-class">
                    <i class="fas fa-graduation-cap"></i> ${candidate.classe}
                </div>
            </div>
        </div>
        <div class="candidate-description">
            ${candidate.description || `<em>Candidate pour la classe de ${candidate.classe}</em>`}
        </div>
        <div class="candidate-select">
            <button type="button" class="select-btn" onclick="selectCandidate(${candidate.id})">
                <i class="fas fa-check-circle"></i> Sélectionner
            </button>
        </div>
    `;
    
    // Clic sur la carte
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.select-btn')) {
            selectCandidate(candidate.id);
        }
    });
    
    return card;
}

function selectCandidate(candidateId) {
    if (!state.userEmail) {
        showError('Validation requise', 'Veuillez d\'abord vérifier votre email');
        return;
    }
    
    // Désélectionner précédent
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Sélectionner nouveau
    const selectedCard = document.querySelector(`.candidate-card[data-id="${candidateId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    state.selectedCandidateId = candidateId;
    state.selectedCandidate = state.candidates.find(c => c.id === candidateId);
    
    if (state.selectedCandidate && elements.selectedInfo) {
        const initials = (state.selectedCandidate.prenom?.charAt(0) || '') + (state.selectedCandidate.nom?.charAt(0) || '');
        const colors = {
            '2nde': 'linear-gradient(135deg, #4361ee, #3a0ca3)',
            '3ème': 'linear-gradient(135deg, #4cc9f0, #3a86ff)',
            // ... mêmes couleurs
        };
        const color = colors[state.selectedCandidate.classe] || 'linear-gradient(135deg, #6c757d, #495057)';
        
        elements.selectedInfo.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-photo" style="background: ${color}">
                    ${initials.toUpperCase()}
                </div>
                <div class="candidate-info">
                    <h3>${state.selectedCandidate.prenom} ${state.selectedCandidate.nom}</h3>
                    <div class="candidate-class">
                        <i class="fas fa-graduation-cap"></i> ${state.selectedCandidate.classe}
                    </div>
                </div>
            </div>
            <div class="candidate-description">
                ${state.selectedCandidate.description || `<em>Votre sélection pour la classe de ${state.selectedCandidate.classe}</em>`}
            </div>
            <div class="selection-confirmation">
                <i class="fas fa-check-circle"></i> Prête à voter pour cette candidate
            </div>
        `;
        
        // Afficher panneau
        if (elements.selectedCandidatePanel) {
            elements.selectedCandidatePanel.style.display = 'block';
        }
        
        // Activer bouton vote
        if (elements.voteBtn) {
            elements.voteBtn.disabled = false;
            elements.voteBtn.classList.add('active');
        }
        
        showStatus('✅ Candidate sélectionnée • Prêt à voter', 'success');
    }
}

// ==================== GESTION VOTE ====================
function showConfirmationModal() {
    if (!state.selectedCandidate || !state.userEmail) {
        showError('Sélection incomplète', 'Veuillez sélectionner une candidate');
        return;
    }
    
    if (elements.confirmCandidate) {
        const initials = (state.selectedCandidate.prenom?.charAt(0) || '') + (state.selectedCandidate.nom?.charAt(0) || '');
        const colors = {
            '2nde': 'linear-gradient(135deg, #4361ee, #3a0ca3)',
            // ... mêmes couleurs
        };
        const color = colors[state.selectedCandidate.classe] || 'linear-gradient(135deg, #6c757d, #495057)';
        
        elements.confirmCandidate.innerHTML = `
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 80px; height: 80px; border-radius: 50%; background: ${color}; 
                          display: flex; align-items: center; justify-content: center; 
                          color: white; font-size: 24px; font-weight: bold; margin: 0 auto 15px;">
                    ${initials.toUpperCase()}
                </div>
                <h3 style="margin: 0; color: #333;">${state.selectedCandidate.prenom} ${state.selectedCandidate.nom}</h3>
                <p style="color: #666; margin: 5px 0;">${state.selectedCandidate.classe}</p>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 5px 0;"><strong>Email :</strong> ${state.userEmail}</p>
                <p style="margin: 5px 0;"><strong>Date :</strong> ${formatDateTime(new Date())}</p>
            </div>
        `;
    }
    
    if (elements.confirmationModal) {
        elements.confirmationModal.style.display = 'flex';
    }
}

async function submitVote() {
    if (!state.selectedCandidateId || !state.userEmail) {
        showError('Données manquantes', 'Impossible de voter');
        return;
    }
    
    hideModal();
    showLoader('Enregistrement de votre vote...');
    
    try {
        const response = await fetch(API_ENDPOINTS.vote, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                professeur_email: state.userEmail,
                candidate_id: state.selectedCandidateId
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.error) {
            throw new Error(data.error || `Erreur: ${response.status}`);
        }
        
        // Succès
        saveVoteState(state.userEmail, data.timestamp);
        
        // Afficher confirmation
        if (elements.confirmationId) {
            elements.confirmationId.textContent = data.confirmation_id || `VOTE-${Date.now()}`;
        }
        
        if (elements.confirmationEmail) {
            elements.confirmationEmail.textContent = state.userEmail;
        }
        
        if (elements.confirmationTime) {
            elements.confirmationTime.textContent = formatDateTime(new Date());
        }
        
        showSection('confirmationSection');
        showStatus('✅ Vote enregistré avec succès !', 'success');
        
        // Recharger stats
        setTimeout(() => loadSystemStatus().catch(console.error), 2000);
        
    } catch (error) {
        console.error('Erreur vote:', error);
        
        let errorMessage = 'Erreur d\'enregistrement';
        if (error.message.includes('déjà voté')) {
            errorMessage = 'Vous avez déjà voté pour cette élection';
            state.hasVoted = true;
            saveVoteState(state.userEmail);
            showSection('alreadyVotedSection');
        } else if (error.message.includes('terminée')) {
            errorMessage = 'La période de vote est terminée';
            state.electionStatus = 'finished';
        } else if (error.message.includes('pas encore commencé')) {
            errorMessage = 'L\'élection n\'a pas encore commencé';
            state.electionStatus = 'pending';
        }
        
        showError('Vote impossible', errorMessage);
    } finally {
        hideLoader();
    }
}

function hideModal() {
    if (elements.confirmationModal) {
        elements.confirmationModal.style.display = 'none';
    }
}

// ==================== ÉVÉNEMENTS ====================
function setupEventListeners() {
    // Email input
    if (elements.emailInput) {
        elements.emailInput.addEventListener('input', () => {
            if (elements.emailError) {
                elements.emailError.style.display = 'none';
            }
        });
        
        elements.emailInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                verifyEmail();
            }
        });
        
        // Auto-focus
        setTimeout(() => {
            if (elements.emailInput && elements.emailSection.style.display !== 'none') {
                elements.emailInput.focus();
            }
        }, 100);
    }
    
    // Verify button
    if (elements.verifyBtn) {
        elements.verifyBtn.addEventListener('click', verifyEmail);
    }
    
    // Confirm vote button
    if (elements.confirmVoteBtn) {
        elements.confirmVoteBtn.addEventListener('click', submitVote);
    }
    
    // Fermer modales
    document.addEventListener('click', (e) => {
        if (elements.confirmationModal && e.target === elements.confirmationModal) {
            hideModal();
        }
    });
    
    // Échap pour fermer modales
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal();
        }
    });
    
    // Détection connexion
    window.addEventListener('online', () => {
        showStatus('✅ Connexion rétablie', 'success');
    });
    
    window.addEventListener('offline', () => {
        showStatus('❌ Hors ligne', 'error');
    });
}

// ==================== EXPORT GLOBAL ====================
window.verifyEmail = verifyEmail;
window.selectCandidate = selectCandidate;
window.showConfirmationModal = showConfirmationModal;
window.submitVote = submitVote;
window.hideModal = hideModal;
window.clearSelection = clearSelection;
window.logout = clearUserSession;

// Message final
console.log('✅ Système de vote chargé avec succès');