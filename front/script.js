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

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    updateServerInfo();
});

// Initialiser l'application
async function initializeApp() {
    try {
        showLoader('Initialisation du système...');
        
        // Charger les données du système
        await loadSystemStatus();
        
        // Vérifier si l'utilisateur a déjà voté
        checkPreviousVote();
        
    } catch (error) {
        console.error('Erreur d\'initialisation:', error);
        showError('Erreur d\'initialisation', 'Impossible de charger les données du système');
    } finally {
        hideLoader();
    }
}

// Charger le statut du système
async function loadSystemStatus() {
    try {
        const response = await fetchWithTimeout(API_ENDPOINTS.status, {
            timeout: 5000
        });
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.system.status === 'error') {
            throw new Error(data.system.error || 'Erreur serveur');
        }
        
        currentElection = data.election;
        electionStatus = data.election.status;
        
        // Mettre à jour l'affichage
        updateSystemDisplay(data);
        
        return data;
        
    } catch (error) {
        console.error('Erreur chargement statut:', error);
        throw error;
    }
}

// Mettre à jour l'affichage du système
function updateSystemDisplay(data) {
    // Mettre à jour les informations d'élection
    if (elements.timeRemaining) {
        elements.timeRemaining.textContent = data.election.temps_restant || '--';
    }
    
    if (elements.votesCount) {
        elements.votesCount.textContent = data.statistics.votes || 0;
    }
    
    // Mettre à jour le message de statut
    let statusText = '';
    let statusType = 'info';
    
    switch (data.election.status) {
        case 'active':
            statusText = `🗳️ Élection en cours • ${data.election.temps_restant} restant`;
            statusType = 'success';
            break;
        case 'pending':
            const startDate = new Date(data.election.date_debut);
            statusText = `⏳ Élection débutera le ${formatDate(startDate)}`;
            statusType = 'warning';
            break;
        case 'finished':
            statusText = '✅ Élection terminée';
            statusType = 'info';
            break;
        default:
            statusText = 'Statut inconnu';
    }
    
    showStatus(statusText, statusType);
}

// Vérifier si l'utilisateur a déjà voté (dans localStorage)
function checkPreviousVote() {
    const savedEmail = localStorage.getItem('vote_email_2026');
    const savedHasVoted = localStorage.getItem('has_voted_2026');
    const savedTimestamp = localStorage.getItem('vote_timestamp_2026');
    
    if (savedEmail && savedHasVoted === 'true') {
        userEmail = savedEmail;
        hasVoted = true;
        
        // Mettre à jour l'horodatage si disponible
        if (savedTimestamp && elements.voteTimestamp) {
            const date = new Date(savedTimestamp);
            elements.voteTimestamp.textContent = `Vote effectué le ${formatDateTime(date)}`;
        }
        
        // Si l'élection est active, montrer la section "déjà voté"
        if (electionStatus === 'active') {
            setTimeout(() => {
                showAlreadyVotedSection();
            }, 500);
        }
    }
}

// ==================== FONCTIONS EMAIL ====================

// Vérifier l'email de l'utilisateur
async function verifyEmail() {
    const email = elements.emailInput.value.trim();
    
    // Validation
    if (!email) {
        showEmailError('Veuillez entrer votre email');
        return;
    }
    
    if (!validateEmail(email)) {
        showEmailError('Veuillez entrer un email valide');
        return;
    }
    
    userEmail = email;
    
    // Désactiver le bouton
    elements.verifyBtn.disabled = true;
    elements.verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Vérification...';
    
    try {
        const response = await fetch(API_ENDPOINTS.verifyEmail, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showEmailError(data.error);
            return;
        }
        
        // Traiter la réponse
        hasVoted = data.has_voted;
        
        if (hasVoted) {
            // Sauvegarder dans localStorage
            localStorage.setItem('vote_email_2026', email);
            localStorage.setItem('has_voted_2026', 'true');
            localStorage.setItem('vote_timestamp_2026', new Date().toISOString());
            
            // Mettre à jour l'horodatage
            if (elements.voteTimestamp) {
                elements.voteTimestamp.textContent = `Vote effectué le ${formatDateTime(new Date())}`;
            }
            
            // Afficher la section "déjà voté"
            showAlreadyVotedSection();
            
        } else {
            // Vérifier si le vote est possible
            if (data.can_vote) {
                // Charger les candidats
                await loadCandidates();
                showCandidatesSection();
            } else {
                showEmailError('Le vote n\'est pas actuellement ouvert');
            }
        }
        
    } catch (error) {
        console.error('Erreur vérification email:', error);
        showEmailError('Erreur de connexion au serveur');
    } finally {
        // Réactiver le bouton
        elements.verifyBtn.disabled = false;
        elements.verifyBtn.innerHTML = '<i class="fas fa-check"></i> Vérifier';
    }
}

// Gérer l'appui sur Entrée dans le champ email
function handleEmailEnter(event) {
    if (event.key === 'Enter') {
        verifyEmail();
    }
}

// Afficher une erreur email
function showEmailError(message) {
    if (elements.emailError) {
        elements.emailError.textContent = message;
        elements.emailError.style.display = 'block';
        
        // Cacher après 5 secondes
        setTimeout(() => {
            elements.emailError.style.display = 'none';
        }, 5000);
    }
}

// ==================== FONCTIONS CANDIDATS ====================

// Charger les candidats
async function loadCandidates() {
    try {
        // Afficher le loader
        if (elements.loadingCandidates) {
            elements.loadingCandidates.style.display = 'flex';
        }
        
        const response = await fetch(API_ENDPOINTS.election);
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        candidates = data.candidates || [];
        currentElection = data;
        
        // Afficher les candidats
        displayCandidates(candidates);
        
    } catch (error) {
        console.error('Erreur chargement candidats:', error);
        showError('Erreur de chargement', 'Impossible de charger la liste des candidates');
    } finally {
        // Cacher le loader
        if (elements.loadingCandidates) {
            elements.loadingCandidates.style.display = 'none';
        }
    }
}

// Afficher les candidats dans la grille
function displayCandidates(candidatesList) {
    if (!elements.candidatesGrid) return;
    
    // Vider la grille
    elements.candidatesGrid.innerHTML = '';
    
    // Ajouter chaque candidate
    candidatesList.forEach(candidate => {
        const card = createCandidateCard(candidate);
        elements.candidatesGrid.appendChild(card);
    });
}

// Créer une carte de candidate
function createCandidateCard(candidate) {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.dataset.id = candidate.id;
    card.dataset.classe = candidate.classe;
    
    // Générer les initiales pour l'avatar
    const initials = getInitials(candidate.prenom, candidate.nom);
    
    card.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${getRandomColor()}">
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
    
    // Sélection au clic sur toute la carte
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.select-btn')) {
            selectCandidate(candidate.id);
        }
    });
    
    return card;
}

// Sélectionner une candidate
function selectCandidate(candidateId) {
    // Vérifier si l'email a été validé
    if (!userEmail) {
        showError('Validation requise', 'Veuillez d\'abord vérifier votre email');
        return;
    }
    
    // Désélectionner la candidate précédente
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Sélectionner la nouvelle candidate
    const selectedCard = document.querySelector(`.candidate-card[data-id="${candidateId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
        selectedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // Stocker l'ID de la candidate sélectionnée
    selectedCandidateId = candidateId;
    selectedCandidate = candidates.find(c => c.id === candidateId);
    
    // Afficher les informations de sélection
    if (selectedCandidate && elements.selectedInfo) {
        const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
        
        elements.selectedInfo.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-photo" style="background: ${getRandomColor()}">
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
        
        // Afficher la section de confirmation
        elements.selectedCandidate.style.display = 'block';
        
        // Scroll vers le haut de la section sélectionnée
        elements.selectedCandidate.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Filtrer les candidats par classe
function filterCandidates(classe) {
    // Mettre à jour les boutons de filtre
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
    
    // Filtrer les candidats
    let filteredCandidates;
    if (classe === 'all') {
        filteredCandidates = candidates;
    } else {
        filteredCandidates = candidates.filter(c => c.classe === classe);
    }
    
    // Afficher les candidats filtrés
    displayCandidates(filteredCandidates);
}

// Effacer la sélection
function clearSelection() {
    selectedCandidateId = null;
    selectedCandidate = null;
    
    // Désélectionner toutes les cartes
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Cacher la section de sélection
    elements.selectedCandidate.style.display = 'none';
}

// ==================== FONCTIONS DE VOTE ====================

// Afficher la modal de confirmation
function showConfirmationModal() {
    if (!selectedCandidate || !userEmail) {
        showError('Sélection incomplète', 'Veuillez sélectionner une candidate');
        return;
    }
    
    // Préparer le contenu de confirmation
    const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
    
    elements.confirmCandidate.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${getRandomColor()}">
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
            <p><i class="fas fa-shield-alt"></i> <strong>Statut :</strong> Vote anonyme et sécurisé</p>
        </div>
    `;
    
    // Afficher la modal
    elements.confirmationModal.style.display = 'flex';
}

// Soumettre le vote (appelé depuis la modal)
async function submitVote() {
    if (!selectedCandidateId || !userEmail) {
        showError('Données manquantes', 'Impossible de soumettre le vote');
        return;
    }
    
    // Cacher la modal
    hideModal();
    
    // Afficher le loader
    showLoader('Enregistrement de votre vote...');
    
    try {
        const response = await fetch(API_ENDPOINTS.vote, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                professeur_email: userEmail,
                candidate_id: selectedCandidateId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Succès !
        hasVoted = true;
        
        // Sauvegarder dans localStorage
        localStorage.setItem('vote_email_2026', userEmail);
        localStorage.setItem('has_voted_2026', 'true');
        localStorage.setItem('vote_timestamp_2026', new Date().toISOString());
        localStorage.setItem('vote_candidate_id_2026', selectedCandidateId.toString());
        
        // Générer un ID de confirmation
        const confirmationId = `VOTE-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
        
        // Mettre à jour l'affichage de confirmation
        if (elements.confirmationId) {
            elements.confirmationId.textContent = `ID: ${confirmationId}`;
        }
        
        // Afficher la section de confirmation
        showConfirmationSection();
        
        // Recharger les données du système
        setTimeout(() => {
            loadSystemStatus();
        }, 2000);
        
    } catch (error) {
        console.error('Erreur envoi vote:', error);
        showError('Erreur d\'envoi', error.message || 'Impossible d\'enregistrer votre vote');
    } finally {
        hideLoader();
    }
}

// ==================== FONCTIONS D'AFFICHAGE ====================

// Afficher la section des candidats
function showCandidatesSection() {
    hideAllSections();
    elements.candidatesSection.style.display = 'block';
    elements.candidatesSection.setAttribute('aria-hidden', 'false');
}

// Afficher la section "déjà voté"
function showAlreadyVotedSection() {
    hideAllSections();
    elements.alreadyVotedSection.style.display = 'block';
    elements.alreadyVotedSection.setAttribute('aria-hidden', 'false');
    
    // Mettre à jour l'horodatage
    if (elements.voteTimestamp) {
        const savedTimestamp = localStorage.getItem('vote_timestamp_2026');
        if (savedTimestamp) {
            const date = new Date(savedTimestamp);
            elements.voteTimestamp.textContent = `Vote effectué le ${formatDateTime(date)}`;
        }
    }
}

// Afficher la section de confirmation
function showConfirmationSection() {
    hideAllSections();
    elements.confirmationSection.style.display = 'block';
    elements.confirmationSection.setAttribute('aria-hidden', 'false');
}

// Afficher la section d'erreur
function showErrorSection(title, message) {
    hideAllSections();
    
    if (elements.errorTitle) {
        elements.errorTitle.textContent = title;
    }
    
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }
    
    elements.errorSection.style.display = 'block';
    elements.errorSection.setAttribute('aria-hidden', 'false');
}

// Cacher toutes les sections
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
            section.setAttribute('aria-hidden', 'true');
        }
    });
}

// ==================== FONCTIONS MODALS ====================

// Cacher la modal de confirmation
function hideModal() {
    elements.confirmationModal.style.display = 'none';
}

// Afficher les informations système
function showSystemInfo() {
    elements.systemInfoModal.style.display = 'flex';
}

// Cacher les informations système
function hideSystemInfoModal() {
    elements.systemInfoModal.style.display = 'none';
}

// Afficher les informations d'accessibilité
function showAccessibilityInfo() {
    elements.accessibilityModal.style.display = 'flex';
}

// Cacher les informations d'accessibilité
function hideAccessibilityModal() {
    elements.accessibilityModal.style.display = 'none';
}

// ==================== FONCTIONS UTILITAIRES ====================

// Afficher le loader global
function showLoader(message = 'Chargement...') {
    if (elements.loaderMessage) {
        elements.loaderMessage.textContent = message;
    }
    if (elements.globalLoader) {
        elements.globalLoader.style.display = 'flex';
    }
}

// Cacher le loader global
function hideLoader() {
    if (elements.globalLoader) {
        elements.globalLoader.style.display = 'none';
    }
}

// Afficher un message de statut
function showStatus(message, type = 'info') {
    if (!elements.statusMessage || !elements.statusBanner) return;
    
    elements.statusMessage.textContent = message;
    
    // Définir la couleur selon le type
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

// Afficher une erreur
function showError(title, message) {
    console.error(title, message);
    showStatus(`❌ ${title}: ${message}`, 'error');
    
    // Si c'est une erreur critique, afficher la section d'erreur
    if (title.includes('connexion') || title.includes('serveur')) {
        showErrorSection(title, message);
    }
}

// Valider un email
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Obtenir les initiales d'un nom
function getInitials(firstName, lastName) {
    return (firstName?.charAt(0) + lastName?.charAt(0)).toUpperCase() || '??';
}

// Générer une couleur aléatoire
function getRandomColor() {
    const colors = [
        'linear-gradient(135deg, #4361ee, #3a0ca3)',
        'linear-gradient(135deg, #4cc9f0, #3a86ff)',
        'linear-gradient(135deg, #7209b7, #560bad)',
        'linear-gradient(135deg, #f72585, #b5179e)',
        'linear-gradient(135deg, #4895ef, #4361ee)'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Formater une date
function formatDate(date) {
    if (!date) return '--';
    
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Formater une date avec l'heure
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

// Rafraîchir les données
function refreshData() {
    loadSystemStatus();
    showStatus('Données actualisées', 'success');
}

// Se déconnecter (réinitialiser la session)
function logout() {
    // Réinitialiser les variables
    userEmail = null;
    hasVoted = false;
    selectedCandidateId = null;
    selectedCandidate = null;
    
    // Vider le champ email
    if (elements.emailInput) {
        elements.emailInput.value = '';
    }
    
    // Effacer la sélection
    clearSelection();
    
    // Revenir à la section email
    hideAllSections();
    elements.emailSection.style.display = 'block';
    elements.emailSection.setAttribute('aria-hidden', 'false');
    
    // Effacer le localStorage (optionnel)
    // localStorage.removeItem('vote_email_2026');
    // localStorage.removeItem('has_voted_2026');
    // localStorage.removeItem('vote_timestamp_2026');
    
    showStatus('Prêt pour la vérification', 'info');
}

// Retenter une action après erreur
function retryAction() {
    hideAllSections();
    elements.emailSection.style.display = 'block';
    initializeApp();
}

// Retourner à la section email
function goToEmailSection() {
    hideAllSections();
    elements.emailSection.style.display = 'block';
}

// Scroller vers le haut
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Mettre à jour les infos serveur
function updateServerInfo() {
    if (elements.serverInfo) {
        elements.serverInfo.textContent = `Serveur : ${window.location.hostname}`;
    }
}

// Fetch avec timeout
function fetchWithTimeout(url, options = {}) {
    const { timeout = 10000, ...fetchOptions } = options;
    
    return Promise.race([
        fetch(url, fetchOptions),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), timeout)
        )
    ]);
}

// ==================== ÉCOUTEURS D'ÉVÉNEMENTS ====================

function setupEventListeners() {
    // Fermer les modales en cliquant en dehors
    document.addEventListener('click', (e) => {
        // Modal de confirmation
        if (elements.confirmationModal && elements.confirmationModal.style.display === 'flex') {
            if (e.target === elements.confirmationModal || e.target.classList.contains('modal-overlay')) {
                hideModal();
            }
        }
        
        // Modal système
        if (elements.systemInfoModal && elements.systemInfoModal.style.display === 'flex') {
            if (e.target === elements.systemInfoModal || e.target.classList.contains('modal-overlay')) {
                hideSystemInfoModal();
            }
        }
        
        // Modal accessibilité
        if (elements.accessibilityModal && elements.accessibilityModal.style.display === 'flex') {
            if (e.target === elements.accessibilityModal || e.target.classList.contains('modal-overlay')) {
                hideAccessibilityModal();
            }
        }
    });
    
    // Fermer les modales avec la touche Échap
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal();
            hideSystemInfoModal();
            hideAccessibilityModal();
        }
    });
    
    // Validation en temps réel de l'email
    if (elements.emailInput) {
        elements.emailInput.addEventListener('input', () => {
            if (elements.emailError) {
                elements.emailError.style.display = 'none';
            }
        });
    }
}

// ==================== EXPORT DES FONCTIONS GLOBALES ====================

// Exposer les fonctions au scope global
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

// Initialisation finale
setTimeout(() => {
    console.log('Système de vote 2026 - Cours privés Source de la Fontaine');
    console.log('Version: 2026.1.0');
    console.log('Serveur:', API_BASE_URL);
}, 1000);