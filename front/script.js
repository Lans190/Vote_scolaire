// Configuration de l'API
const API_BASE_URL = window.location.origin;
const API_ENDPOINTS = {
    election: `${API_BASE_URL}/api/election`,
    vote: `${API_BASE_URL}/api/vote`,
    verifyEmail: `${API_BASE_URL}/api/verify-email`,
    status: `${API_BASE_URL}/api/status`
};

// Variables globales
let currentElection = null;
let candidates = [];
let selectedCandidate = null;
let userEmail = null;
let hasVoted = false;
let electionStatus = '';
let selectedCandidateId = null;

// Éléments DOM
const elements = {
    // En-tête et statut
    electionInfo: document.getElementById('electionInfo'),
    statusBanner: document.getElementById('statusBanner'),
    statusMessage: document.getElementById('statusMessage'),
    timeRemaining: document.getElementById('timeRemaining'),
    votesCount: document.getElementById('votesCount'),
    
    // Sections principales
    emailSection: document.getElementById('emailSection'),
    candidatesSection: document.getElementById('candidatesSection'),
    alreadyVotedSection: document.getElementById('alreadyVotedSection'),
    confirmationSection: document.getElementById('confirmationSection'),
    errorSection: document.getElementById('errorSection'),
    
    // Formulaire email
    emailInput: document.getElementById('emailInput'),
    verifyBtn: document.getElementById('verifyBtn'),
    emailError: document.getElementById('emailError'),
    
    // Section candidats
    candidatesGrid: document.getElementById('candidatesGrid'),
    selectedCandidate: document.getElementById('selectedCandidate'),
    selectedInfo: document.getElementById('selectedInfo'),
    voteBtn: document.getElementById('voteBtn'),
    loadingCandidates: document.getElementById('loadingCandidates'),
    
    // Filtres
    filterButtons: document.querySelectorAll('.filter-btn'),
    
    // Sections déjà voté / confirmation
    voteTimestamp: document.getElementById('voteTimestamp'),
    confirmationId: document.getElementById('confirmationId'),
    
    // Modals
    confirmationModal: document.getElementById('confirmationModal'),
    confirmCandidate: document.getElementById('confirmCandidate'),
    confirmVoteBtn: document.getElementById('confirmVoteBtn'),
    systemInfoModal: document.getElementById('systemInfoModal'),
    accessibilityModal: document.getElementById('accessibilityModal'),
    
    // Loader
    globalLoader: document.getElementById('globalLoader'),
    loaderMessage: document.getElementById('loaderMessage'),
    
    // Erreurs
    errorTitle: document.getElementById('errorTitle'),
    errorMessage: document.getElementById('errorMessage'),
    
    // Pied de page
    serverInfo: document.getElementById('serverInfo')
};

// ==================== INITIALISATION ====================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    updateServerInfo();
});

async function initializeApp() {
    try {
        showLoader('Initialisation du système...');
        
        // Vérifier la connexion API
        await checkAPI();
        
        // Charger les données du système
        await loadSystemStatus();
        
        // Vérifier si l'utilisateur a déjà voté
        checkPreviousVote();
        
        // Afficher le statut initial
        showStatus('✅ Système de vote prêt • Cours privés Source de la Fontaine', 'success');
        
    } catch (error) {
        console.error('Erreur d\'initialisation:', error);
        showError('Système temporairement indisponible', 'Veuillez réessayer dans quelques instants');
    } finally {
        hideLoader();
    }
}

// ==================== FONCTIONS API ====================

async function checkAPI() {
    try {
        const response = await fetchWithTimeout(API_ENDPOINTS.status, { timeout: 8000 });
        
        if (!response.ok) {
            throw new Error(`Serveur indisponible (${response.status})`);
        }
        
        const data = await response.json();
        
        if (data.system.status === 'error') {
            throw new Error('Erreur de configuration du serveur');
        }
        
        return true;
        
    } catch (error) {
        console.error('Erreur connexion API:', error);
        throw new Error('Impossible de se connecter au serveur de vote');
    }
}

async function loadSystemStatus() {
    try {
        const response = await fetch(API_ENDPOINTS.status);
        const data = await response.json();
        
        if (data.system.status === 'error') {
            throw new Error(data.system.error || 'Erreur serveur');
        }
        
        currentElection = data.election;
        electionStatus = data.election.status;
        
        updateSystemDisplay(data);
        return data;
        
    } catch (error) {
        console.error('Erreur chargement statut:', error);
        throw error;
    }
}

function updateSystemDisplay(data) {
    // Mettre à jour le temps restant
    if (elements.timeRemaining && data.election.temps_restant) {
        elements.timeRemaining.textContent = data.election.temps_restant;
    }
    
    // Mettre à jour le nombre de votes
    if (elements.votesCount && data.statistics.votes !== undefined) {
        elements.votesCount.textContent = data.statistics.votes;
    }
    
    // Mettre à jour le message de statut
    updateStatusMessage(data.election);
}

function updateStatusMessage(election) {
    if (!elements.statusMessage) return;
    
    let statusText = '';
    
    switch (election.status) {
        case 'active':
            statusText = `🗳️ Vote en cours • ${election.temps_restant} restant`;
            break;
        case 'pending':
            statusText = '⏳ L\'élection débutera prochainement';
            break;
        case 'finished':
            statusText = '✅ Élection terminée';
            break;
        default:
            statusText = '📡 Connexion établie';
    }
    
    elements.statusMessage.textContent = statusText;
}

// ==================== GESTION DES ÉTATS UTILISATEUR ====================

function checkPreviousVote() {
    const savedEmail = localStorage.getItem('vote_email_2026');
    const savedHasVoted = localStorage.getItem('has_voted_2026');
    const savedTimestamp = localStorage.getItem('vote_timestamp_2026');
    
    if (savedEmail && savedHasVoted === 'true') {
        userEmail = savedEmail;
        hasVoted = true;
        
        // Afficher la section "déjà voté" si l'élection est active
        if (electionStatus === 'active' && elements.alreadyVotedSection) {
            setTimeout(() => {
                showAlreadyVotedSection();
                if (elements.voteTimestamp && savedTimestamp) {
                    const date = new Date(savedTimestamp);
                    elements.voteTimestamp.textContent = `Vote enregistré le ${formatDateTime(date)}`;
                }
            }, 500);
        }
    }
}

// ==================== GESTION EMAIL ====================

async function verifyEmail() {
    const email = elements.emailInput.value.trim();
    
    // Validation basique
    if (!email) {
        showEmailError('Veuillez entrer votre email');
        return;
    }
    
    if (!validateEmail(email)) {
        showEmailError('Format d\'email invalide');
        return;
    }
    
    userEmail = email;
    showLoader('Vérification en cours...');
    
    try {
        const response = await fetch(API_ENDPOINTS.verifyEmail, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showEmailError(data.error);
            return;
        }
        
        hasVoted = data.has_voted;
        
        if (hasVoted) {
            // Sauvegarder l'état
            saveVoteState(email);
            showAlreadyVotedSection();
        } else {
            if (data.can_vote) {
                await loadCandidates();
                showCandidatesSection();
            } else {
                showEmailError('La période de vote n\'est pas active');
            }
        }
        
    } catch (error) {
        console.error('Erreur vérification:', error);
        showEmailError('Erreur de connexion');
    } finally {
        hideLoader();
    }
}

function saveVoteState(email) {
    localStorage.setItem('vote_email_2026', email);
    localStorage.setItem('has_voted_2026', 'true');
    localStorage.setItem('vote_timestamp_2026', new Date().toISOString());
}

function handleEmailEnter(event) {
    if (event.key === 'Enter') {
        verifyEmail();
    }
}

function showEmailError(message) {
    if (elements.emailError) {
        elements.emailError.textContent = message;
        elements.emailError.style.display = 'block';
        
        setTimeout(() => {
            elements.emailError.style.display = 'none';
        }, 5000);
    }
}

// ==================== GESTION CANDIDATS ====================

async function loadCandidates() {
    try {
        showLoader('Chargement des candidates...');
        
        const response = await fetch(API_ENDPOINTS.election);
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        candidates = data.candidates || [];
        currentElection = data;
        
        displayCandidates(candidates);
        
    } catch (error) {
        console.error('Erreur chargement:', error);
        showError('Liste non disponible', 'Impossible de charger les candidates');
    } finally {
        hideLoader();
    }
}

function displayCandidates(candidatesList) {
    if (!elements.candidatesGrid) return;
    
    elements.candidatesGrid.innerHTML = '';
    
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
    
    const initials = getInitials(candidate.prenom, candidate.nom);
    const color = getRandomColor();
    
    card.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${color}">
                ${initials}
            </div>
            <div class="candidate-info">
                <h3>${candidate.prenom} ${candidate.nom}</h3>
                <div class="candidate-class">${candidate.classe}</div>
            </div>
        </div>
        <div class="candidate-description">
            ${candidate.description || 'Candidate sérieuse et motivée.'}
        </div>
        <div class="candidate-select">
            <button type="button" class="select-btn" onclick="selectCandidate(${candidate.id})">
                <i class="fas fa-check"></i> Sélectionner
            </button>
        </div>
    `;
    
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.select-btn')) {
            selectCandidate(candidate.id);
        }
    });
    
    return card;
}

function selectCandidate(candidateId) {
    if (!userEmail) {
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
    
    selectedCandidateId = candidateId;
    selectedCandidate = candidates.find(c => c.id === candidateId);
    
    if (selectedCandidate && elements.selectedInfo) {
        const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
        const color = getRandomColor();
        
        elements.selectedInfo.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-photo" style="background: ${color}">
                    ${initials}
                </div>
                <div class="candidate-info">
                    <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                    <div class="candidate-class">${selectedCandidate.classe}</div>
                </div>
            </div>
            <div class="candidate-description">
                ${selectedCandidate.description || 'Candidate sérieuse et motivée.'}
            </div>
        `;
        
        elements.selectedCandidate.style.display = 'block';
        elements.selectedCandidate.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function filterCandidates(classe) {
    // Mettre à jour les boutons
    elements.filterButtons.forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
    });
    
    const activeBtn = Array.from(elements.filterButtons).find(btn => 
        btn.textContent.includes(classe === 'all' ? 'Toutes' : classe)
    );
    
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.setAttribute('aria-pressed', 'true');
    }
    
    // Filtrer et afficher
    const filtered = classe === 'all' 
        ? candidates 
        : candidates.filter(c => c.classe === classe);
    
    displayCandidates(filtered);
}

function clearSelection() {
    selectedCandidateId = null;
    selectedCandidate = null;
    
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    elements.selectedCandidate.style.display = 'none';
}

// ==================== GESTION VOTE ====================

function showConfirmationModal() {
    if (!selectedCandidate || !userEmail) {
        showError('Sélection incomplète', 'Veuillez sélectionner une candidate');
        return;
    }
    
    const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
    const color = getRandomColor();
    
    elements.confirmCandidate.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${color}">
                ${initials}
            </div>
            <div class="candidate-info">
                <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                <div class="candidate-class">${selectedCandidate.classe}</div>
            </div>
        </div>
        <div class="confirmation-details">
            <p><i class="fas fa-envelope"></i> <strong>Email :</strong> ${userEmail}</p>
            <p><i class="fas fa-calendar"></i> <strong>Date :</strong> ${formatDateTime(new Date())}</p>
        </div>
    `;
    
    elements.confirmationModal.style.display = 'flex';
}

async function submitVote() {
    if (!selectedCandidateId || !userEmail) return;
    
    hideModal();
    showLoader('Enregistrement de votre vote...');
    
    try {
        const response = await fetch(API_ENDPOINTS.vote, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                professeur_email: userEmail,
                candidate_id: selectedCandidateId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Succès
        hasVoted = true;
        saveVoteState(userEmail);
        localStorage.setItem('vote_candidate_id_2026', selectedCandidateId.toString());
        
        // Générer ID de confirmation
        const confirmationId = `VOTE-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
        
        if (elements.confirmationId) {
            elements.confirmationId.textContent = `Référence : ${confirmationId}`;
        }
        
        showConfirmationSection();
        
        // Recharger les stats
        setTimeout(() => loadSystemStatus(), 2000);
        
    } catch (error) {
        console.error('Erreur vote:', error);
        showError('Vote impossible', error.message || 'Erreur d\'enregistrement');
    } finally {
        hideLoader();
    }
}

// ==================== GESTION AFFICHAGE ====================

function showCandidatesSection() {
    hideAllSections();
    elements.candidatesSection.style.display = 'block';
}

function showAlreadyVotedSection() {
    hideAllSections();
    elements.alreadyVotedSection.style.display = 'block';
}

function showConfirmationSection() {
    hideAllSections();
    elements.confirmationSection.style.display = 'block';
}

function showErrorSection(title, message) {
    hideAllSections();
    
    if (elements.errorTitle) elements.errorTitle.textContent = title;
    if (elements.errorMessage) elements.errorMessage.textContent = message;
    
    elements.errorSection.style.display = 'block';
}

function hideAllSections() {
    const sections = [
        elements.emailSection,
        elements.candidatesSection,
        elements.alreadyVotedSection,
        elements.confirmationSection,
        elements.errorSection
    ];
    
    sections.forEach(section => {
        if (section) {
            section.style.display = 'none';
        }
    });
}

// ==================== GESTION MODALS ====================

function hideModal() {
    if (elements.confirmationModal) {
        elements.confirmationModal.style.display = 'none';
    }
}

function showSystemInfo() {
    if (elements.systemInfoModal) {
        elements.systemInfoModal.style.display = 'flex';
    }
}

function hideSystemInfoModal() {
    if (elements.systemInfoModal) {
        elements.systemInfoModal.style.display = 'none';
    }
}

function showAccessibilityInfo() {
    if (elements.accessibilityModal) {
        elements.accessibilityModal.style.display = 'flex';
    }
}

function hideAccessibilityModal() {
    if (elements.accessibilityModal) {
        elements.accessibilityModal.style.display = 'none';
    }
}

// ==================== FONCTIONS UTILITAIRES ====================

function showLoader(message = 'Chargement...') {
    if (elements.loaderMessage) elements.loaderMessage.textContent = message;
    if (elements.globalLoader) elements.globalLoader.style.display = 'flex';
}

function hideLoader() {
    if (elements.globalLoader) elements.globalLoader.style.display = 'none';
}

function showStatus(message, type = 'info') {
    if (!elements.statusMessage || !elements.statusBanner) return;
    
    elements.statusMessage.textContent = message;
    
    const colors = {
        info: '#4361ee',
        success: '#2ecc71',
        warning: '#f39c12',
        error: '#e74c3c'
    };
    
    if (colors[type]) {
        elements.statusBanner.style.borderLeftColor = colors[type];
    }
}

function showError(title, message) {
    console.error(title, message);
    showStatus(`❌ ${title}`, 'error');
    
    if (title.includes('connexion') || title.includes('serveur')) {
        showErrorSection(title, message);
    }
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function getInitials(firstName, lastName) {
    return (firstName?.charAt(0) + lastName?.charAt(0)).toUpperCase() || '??';
}

function getRandomColor() {
    const colors = [
        'linear-gradient(135deg, #4361ee, #3a0ca3)',
        'linear-gradient(135deg, #4cc9f0, #3a86ff)',
        'linear-gradient(135deg, #7209b7, #560bad)',
        'linear-gradient(135deg, #f72585, #b5179e)'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

function formatDateTime(date) {
    if (!date) return '--';
    
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function refreshData() {
    loadSystemStatus();
    showStatus('Données actualisées', 'success');
}

function logout() {
    userEmail = null;
    hasVoted = false;
    selectedCandidateId = null;
    selectedCandidate = null;
    
    if (elements.emailInput) {
        elements.emailInput.value = '';
    }
    
    clearSelection();
    hideAllSections();
    
    if (elements.emailSection) {
        elements.emailSection.style.display = 'block';
    }
    
    showStatus('Prêt pour la vérification', 'info');
}

function retryAction() {
    hideAllSections();
    if (elements.emailSection) {
        elements.emailSection.style.display = 'block';
    }
    initializeApp();
}

function goToEmailSection() {
    hideAllSections();
    if (elements.emailSection) {
        elements.emailSection.style.display = 'block';
    }
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateServerInfo() {
    if (elements.serverInfo) {
        elements.serverInfo.textContent = window.location.hostname;
    }
}

async function fetchWithTimeout(url, options = {}) {
    const { timeout = 10000, ...fetchOptions } = options;
    
    return Promise.race([
        fetch(url, fetchOptions),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout dépassé')), timeout)
        )
    ]);
}

// ==================== ÉVÉNEMENTS ====================

function setupEventListeners() {
    // Fermer modales en cliquant en dehors
    document.addEventListener('click', (e) => {
        if (elements.confirmationModal && e.target === elements.confirmationModal) {
            hideModal();
        }
        if (elements.systemInfoModal && e.target === elements.systemInfoModal) {
            hideSystemInfoModal();
        }
        if (elements.accessibilityModal && e.target === elements.accessibilityModal) {
            hideAccessibilityModal();
        }
    });
    
    // Échap pour fermer modales
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal();
            hideSystemInfoModal();
            hideAccessibilityModal();
        }
    });
    
    // Validation email en temps réel
    if (elements.emailInput) {
        elements.emailInput.addEventListener('input', () => {
            if (elements.emailError) {
                elements.emailError.style.display = 'none';
            }
        });
    }
}

// ==================== EXPORT GLOBAL ====================

window.verifyEmail = verifyEmail;
window.handleEmailEnter = handleEmailEnter;
window.selectCandidate = selectCandidate;
window.filterCandidates = filterCandidates;
window.clearSelection = clearSelection;
window.showConfirmationModal = showConfirmationModal;
window.submitVote = submitVote;
window.hideModal = hideModal;
window.showSystemInfo = showSystemInfo;
window.hideSystemInfoModal = hideSystemInfoModal;
window.showAccessibilityInfo = showAccessibilityInfo;
window.hideAccessibilityModal = hideAccessibilityModal;
window.refreshData = refreshData;
window.logout = logout;
window.retryAction = retryAction;
window.goToEmailSection = goToEmailSection;
window.scrollToTop = scrollToTop;

// Message de démarrage
console.log('=== Système de Vote Scolaire 2026 ===');
console.log('Établissement: Cours privés Source de la Fontaine');
console.log('Version: 2026.1.0');
console.log('URL:', window.location.origin);