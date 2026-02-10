// Configuration de l'API
const API_BASE_URL = window.location.origin;
const API_ENDPOINTS = {
    election: `${API_BASE_URL}/api/election`,
    vote: `${API_BASE_URL}/api/vote`,
    verifyEmail: `${API_BASE_URL}/api/verify-email`,
    status: `${API_BASE_URL}/api/status`,
    results: `${API_BASE_URL}/api/results`,
    stats: `${API_BASE_URL}/api/stats`
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
    
    // Section candidates
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
    confirmationEmail: document.getElementById('confirmationEmail'),
    confirmationTime: document.getElementById('confirmationTime'),
    
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
    serverInfo: document.getElementById('serverInfo'),
    footerYear: document.getElementById('footerYear')
};

// ==================== INITIALISATION ====================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    updateServerInfo();
    updateFooterYear();
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
        
        if (data.system && data.system.status === 'error') {
            throw new Error('Erreur de configuration du serveur');
        }
        
        console.log('✅ API connectée:', data.system);
        return true;
        
    } catch (error) {
        console.error('Erreur connexion API:', error);
        throw new Error('Impossible de se connecter au serveur de vote');
    }
}

async function loadSystemStatus() {
    try {
        const response = await fetch(API_ENDPOINTS.status);
        if (!response.ok) {
            throw new Error(`Statut: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentElection = data.election;
        electionStatus = data.election ? data.election.status : 'inactive';
        
        updateSystemDisplay(data);
        return data;
        
    } catch (error) {
        console.error('Erreur chargement statut:', error);
        throw error;
    }
}

function updateSystemDisplay(data) {
    // Mettre à jour le temps restant
    if (elements.timeRemaining && data.election && data.election.temps_restant) {
        elements.timeRemaining.textContent = data.election.temps_restant;
        elements.timeRemaining.style.display = 'block';
    }
    
    // Mettre à jour les statistiques
    if (data.statistics) {
        if (elements.votesCount && data.statistics.votes !== undefined) {
            elements.votesCount.textContent = data.statistics.votes;
        }
    }
    
    // Mettre à jour le message de statut
    if (data.election) {
        updateStatusMessage(data.election);
    }
}

function updateStatusMessage(election) {
    if (!elements.statusMessage) return;
    
    let statusText = '';
    let statusType = 'info';
    
    switch (election.status) {
        case 'active':
            statusText = `🗳️ Vote en cours • ${election.temps_restant || 'Temps restant'} restant`;
            statusType = 'success';
            break;
        case 'pending':
            statusText = '⏳ L\'élection débutera prochainement';
            statusType = 'warning';
            break;
        case 'finished':
            statusText = '✅ Élection terminée';
            statusType = 'info';
            break;
        default:
            statusText = '📡 Connexion établie au système';
            statusType = 'info';
    }
    
    elements.statusMessage.textContent = statusText;
    showStatus(statusText, statusType);
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

function clearUserSession() {
    userEmail = null;
    hasVoted = false;
    selectedCandidateId = null;
    selectedCandidate = null;
    
    localStorage.removeItem('vote_email_2026');
    localStorage.removeItem('has_voted_2026');
    localStorage.removeItem('vote_timestamp_2026');
    localStorage.removeItem('vote_candidate_id_2026');
    
    if (elements.emailInput) {
        elements.emailInput.value = '';
    }
}

// ==================== GESTION EMAIL ====================

async function verifyEmail() {
    const email = elements.emailInput.value.trim().toLowerCase();
    
    // Validation basique
    if (!email) {
        showEmailError('Veuillez entrer votre email');
        return;
    }
    
    if (!validateEmail(email)) {
        showEmailError('Format d\'email invalide (exemple: nom@ecole.fr)');
        return;
    }
    
    userEmail = email;
    showLoader('Vérification en cours...');
    
    try {
        const response = await fetch(API_ENDPOINTS.verifyEmail, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        
        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showEmailError(data.error);
            return;
        }
        
        hasVoted = data.has_voted;
        
        if (hasVoted) {
            // Sauvegarder l'état
            saveVoteState(email, data.vote_date);
            showAlreadyVotedSection();
            showStatus('✅ Vous avez déjà voté', 'info');
        } else {
            if (data.can_vote) {
                await loadCandidates();
                showCandidatesSection();
                showStatus('✅ Email validé • Sélectionnez une candidate', 'success');
            } else {
                showEmailError(data.message || 'La période de vote n\'est pas active');
                showStatus('⏸️ Vote non disponible', 'warning');
            }
        }
        
    } catch (error) {
        console.error('Erreur vérification:', error);
        showEmailError('Erreur de connexion au serveur');
        showStatus('❌ Erreur de vérification', 'error');
    } finally {
        hideLoader();
    }
}

function saveVoteState(email, voteDate = null) {
    localStorage.setItem('vote_email_2026', email);
    localStorage.setItem('has_voted_2026', 'true');
    localStorage.setItem('vote_timestamp_2026', voteDate || new Date().toISOString());
}

function handleEmailEnter(event) {
    if (event.key === 'Enter') {
        verifyEmail();
    }
}

function showEmailError(message) {
    if (elements.emailError) {
        elements.emailError.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        elements.emailError.style.display = 'block';
        
        // Animation d'apparition
        elements.emailError.style.opacity = '0';
        elements.emailError.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            elements.emailError.style.transition = 'all 0.3s ease';
            elements.emailError.style.opacity = '1';
            elements.emailError.style.transform = 'translateY(0)';
        }, 10);
        
        // Auto-dissimulation après 8 secondes
        setTimeout(() => {
            if (elements.emailError.style.display === 'block') {
                elements.emailError.style.opacity = '0';
                elements.emailError.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    elements.emailError.style.display = 'none';
                }, 300);
            }
        }, 8000);
    }
}

// ==================== GESTION CANDIDATES ====================

async function loadCandidates() {
    try {
        showLoader('Chargement des candidates...');
        
        const response = await fetch(API_ENDPOINTS.election);
        if (!response.ok) {
            throw new Error(`Erreur: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        candidates = data.candidates || [];
        currentElection = data;
        
        if (candidates.length === 0) {
            throw new Error('Aucune candidate disponible');
        }
        
        displayCandidates(candidates);
        
    } catch (error) {
        console.error('Erreur chargement:', error);
        showError('Liste non disponible', 'Impossible de charger les candidates. Veuillez réessayer.');
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
    
    // Trier par classe (ordre logique)
    const classOrder = ['2nde', '3ème', '4ème', '5ème', '6ème'];
    candidatesList.sort((a, b) => {
        return classOrder.indexOf(a.classe) - classOrder.indexOf(b.classe);
    });
    
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
    card.setAttribute('aria-label', `Candidate: ${candidate.prenom} ${candidate.nom}, Classe: ${candidate.classe}`);
    card.setAttribute('tabindex', '0');
    
    // Initiales pour l'avatar
    const initials = getInitials(candidate.prenom, candidate.nom);
    
    // Couleur basée sur la classe
    const color = getColorByClass(candidate.classe);
    
    card.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${color}">
                ${initials}
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
            <button type="button" class="select-btn" onclick="selectCandidate(${candidate.id})" 
                    aria-label="Sélectionner ${candidate.prenom} ${candidate.nom}">
                <i class="fas fa-check-circle"></i> Sélectionner
            </button>
        </div>
    `;
    
    // Interaction tactile/click
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.select-btn')) {
            selectCandidate(candidate.id);
        }
    });
    
    // Support clavier
    card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            selectCandidate(candidate.id);
        }
    });
    
    // Animation d'entrée
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        card.style.transition = 'all 0.5s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    }, 10);
    
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
        card.setAttribute('aria-selected', 'false');
    });
    
    // Sélectionner nouveau
    const selectedCard = document.querySelector(`.candidate-card[data-id="${candidateId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
        selectedCard.setAttribute('aria-selected', 'true');
        
        // Animation de sélection
        selectedCard.style.transform = 'scale(0.98)';
        setTimeout(() => {
            selectedCard.style.transform = 'scale(1)';
        }, 150);
    }
    
    selectedCandidateId = candidateId;
    selectedCandidate = candidates.find(c => c.id === candidateId);
    
    if (selectedCandidate && elements.selectedInfo) {
        const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
        const color = getColorByClass(selectedCandidate.classe);
        
        elements.selectedInfo.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-photo" style="background: ${color}">
                    ${initials}
                </div>
                <div class="candidate-info">
                    <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                    <div class="candidate-class">
                        <i class="fas fa-graduation-cap"></i> ${selectedCandidate.classe}
                    </div>
                </div>
            </div>
            <div class="candidate-description">
                ${selectedCandidate.description || `<em>Votre sélection pour la classe de ${selectedCandidate.classe}</em>`}
            </div>
            <div class="selection-confirmation">
                <i class="fas fa-check-circle"></i> Prête à voter pour cette candidate
            </div>
        `;
        
        // Afficher avec animation
        elements.selectedCandidate.style.display = 'block';
        elements.selectedCandidate.style.opacity = '0';
        
        setTimeout(() => {
            elements.selectedCandidate.style.transition = 'all 0.3s ease';
            elements.selectedCandidate.style.opacity = '1';
            elements.selectedCandidate.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start',
                inline: 'nearest'
            });
        }, 10);
        
        // Activer le bouton de vote
        if (elements.voteBtn) {
            elements.voteBtn.disabled = false;
            elements.voteBtn.classList.add('active');
        }
        
        showStatus('✅ Candidate sélectionnée • Prêt à voter', 'success');
    }
}

function filterCandidates(classe) {
    // Mettre à jour les boutons de filtre
    elements.filterButtons.forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
    });
    
    const activeBtn = Array.from(elements.filterButtons).find(btn => {
        if (classe === 'all') return btn.textContent.includes('Toutes');
        return btn.textContent.includes(classe);
    });
    
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.setAttribute('aria-pressed', 'true');
    }
    
    // Filtrer et afficher
    let filtered = [];
    if (classe === 'all') {
        filtered = candidates;
    } else {
        filtered = candidates.filter(c => c.classe === classe);
    }
    
    displayCandidates(filtered);
    
    // Message de filtre
    if (filtered.length === 0) {
        showStatus(`⚠️ Aucune candidate en ${classe}`, 'warning');
    } else {
        showStatus(`📋 ${filtered.length} candidate(s) en ${classe === 'all' ? 'toutes classes' : classe}`, 'info');
    }
}

function clearSelection() {
    selectedCandidateId = null;
    selectedCandidate = null;
    
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
        card.setAttribute('aria-selected', 'false');
    });
    
    elements.selectedCandidate.style.display = 'none';
    
    if (elements.voteBtn) {
        elements.voteBtn.disabled = true;
        elements.voteBtn.classList.remove('active');
    }
    
    showStatus('↩️ Sélection annulée • Choisissez une candidate', 'info');
}

// ==================== GESTION VOTE ====================

function showConfirmationModal() {
    if (!selectedCandidate || !userEmail) {
        showError('Sélection incomplète', 'Veuillez sélectionner une candidate');
        return;
    }
    
    const initials = getInitials(selectedCandidate.prenom, selectedCandidate.nom);
    const color = getColorByClass(selectedCandidate.classe);
    
    elements.confirmCandidate.innerHTML = `
        <div class="confirmation-header">
            <h3><i class="fas fa-shield-alt"></i> Confirmation de vote</h3>
            <p>Veuillez vérifier vos informations avant de confirmer</p>
        </div>
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${color}">
                ${initials}
            </div>
            <div class="candidate-info">
                <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                <div class="candidate-class">
                    <i class="fas fa-graduation-cap"></i> ${selectedCandidate.classe}
                </div>
            </div>
        </div>
        <div class="confirmation-details">
            <div class="detail-item">
                <i class="fas fa-envelope"></i>
                <div>
                    <strong>Email vérifié :</strong>
                    <span>${userEmail}</span>
                </div>
            </div>
            <div class="detail-item">
                <i class="fas fa-calendar-check"></i>
                <div>
                    <strong>Date et heure :</strong>
                    <span>${formatDateTime(new Date())}</span>
                </div>
            </div>
            <div class="detail-item">
                <i class="fas fa-user-check"></i>
                <div>
                    <strong>Votre choix :</strong>
                    <span>${selectedCandidate.prenom} ${selectedCandidate.nom}</span>
                </div>
            </div>
        </div>
        <div class="confirmation-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <p><strong>Attention :</strong> Ce vote est définitif et ne peut pas être modifié.</p>
        </div>
    `;
    
    // Afficher la modal avec animation
    elements.confirmationModal.style.display = 'flex';
    elements.confirmationModal.style.opacity = '0';
    
    setTimeout(() => {
        elements.confirmationModal.style.transition = 'opacity 0.3s ease';
        elements.confirmationModal.style.opacity = '1';
    }, 10);
    
    // Focus sur le bouton d'annulation pour l'accessibilité
    setTimeout(() => {
        const cancelBtn = elements.confirmationModal.querySelector('.cancel-btn');
        if (cancelBtn) cancelBtn.focus();
    }, 100);
}

async function submitVote() {
    if (!selectedCandidateId || !userEmail) return;
    
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
                professeur_email: userEmail,
                candidate_id: selectedCandidateId
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.error) {
            throw new Error(data.error || `Erreur: ${response.status}`);
        }
        
        // Succès
        hasVoted = true;
        saveVoteState(userEmail, data.timestamp);
        localStorage.setItem('vote_candidate_id_2026', selectedCandidateId.toString());
        
        // Afficher l'ID de confirmation
        if (elements.confirmationId) {
            elements.confirmationId.textContent = data.confirmation_id || `VOTE-${Date.now()}`;
        }
        
        if (elements.confirmationEmail) {
            elements.confirmationEmail.textContent = userEmail;
        }
        
        if (elements.confirmationTime) {
            elements.confirmationTime.textContent = formatDateTime(new Date());
        }
        
        showConfirmationSection();
        showStatus('✅ Vote enregistré avec succès !', 'success');
        
        // Recharger les stats après un délai
        setTimeout(() => {
            loadSystemStatus().catch(console.error);
        }, 3000);
        
        // Son de succès (si autorisé)
        playSuccessSound();
        
    } catch (error) {
        console.error('Erreur vote:', error);
        
        let errorMessage = 'Erreur d\'enregistrement';
        if (error.message.includes('déjà voté')) {
            errorMessage = 'Vous avez déjà voté pour cette élection';
            hasVoted = true;
            saveVoteState(userEmail);
            showAlreadyVotedSection();
        } else if (error.message.includes('terminée')) {
            errorMessage = 'La période de vote est terminée';
            electionStatus = 'finished';
            updateStatusMessage({ status: 'finished', temps_restant: 'Terminé' });
        } else if (error.message.includes('pas encore commencé')) {
            errorMessage = 'L\'élection n\'a pas encore commencé';
            electionStatus = 'pending';
            updateStatusMessage({ status: 'pending', temps_restant: 'En attente' });
        }
        
        showError('Vote impossible', errorMessage);
    } finally {
        hideLoader();
    }
}

// ==================== GESTION AFFICHAGE ====================

function showCandidatesSection() {
    hideAllSections();
    elements.candidatesSection.style.display = 'block';
    
    // Animation d'entrée
    elements.candidatesSection.style.opacity = '0';
    setTimeout(() => {
        elements.candidatesSection.style.transition = 'opacity 0.5s ease';
        elements.candidatesSection.style.opacity = '1';
    }, 10);
}

function showAlreadyVotedSection() {
    hideAllSections();
    elements.alreadyVotedSection.style.display = 'block';
    
    // Récupérer la date du vote
    const savedTimestamp = localStorage.getItem('vote_timestamp_2026');
    if (elements.voteTimestamp && savedTimestamp) {
        const date = new Date(savedTimestamp);
        elements.voteTimestamp.textContent = formatDateTime(date);
    }
}

function showConfirmationSection() {
    hideAllSections();
    elements.confirmationSection.style.display = 'block';
    
    // Animation
    elements.confirmationSection.style.opacity = '0';
    elements.confirmationSection.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        elements.confirmationSection.style.transition = 'all 0.5s ease';
        elements.confirmationSection.style.opacity = '1';
        elements.confirmationSection.style.transform = 'translateY(0)';
    }, 10);
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
            section.style.opacity = '0';
        }
    });
}

// ==================== GESTION MODALS ====================

function hideModal() {
    if (elements.confirmationModal) {
        elements.confirmationModal.style.opacity = '0';
        setTimeout(() => {
            elements.confirmationModal.style.display = 'none';
        }, 300);
    }
}

function showSystemInfo() {
    if (elements.systemInfoModal) {
        loadSystemInfo();
        elements.systemInfoModal.style.display = 'flex';
        elements.systemInfoModal.style.opacity = '0';
        
        setTimeout(() => {
            elements.systemInfoModal.style.transition = 'opacity 0.3s ease';
            elements.systemInfoModal.style.opacity = '1';
        }, 10);
    }
}

async function loadSystemInfo() {
    try {
        const response = await fetch(API_ENDPOINTS.status);
        const data = await response.json();
        
        const infoContent = document.getElementById('systemInfoContent');
        if (infoContent) {
            infoContent.innerHTML = `
                <div class="info-grid">
                    <div class="info-item">
                        <i class="fas fa-server"></i>
                        <div>
                            <strong>Statut serveur :</strong>
                            <span>${data.system?.status === 'online' ? '✅ En ligne' : '❌ Hors ligne'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-database"></i>
                        <div>
                            <strong>Base de données :</strong>
                            <span>${data.system?.database || 'SQLite'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-calendar-alt"></i>
                        <div>
                            <strong>Année scolaire :</strong>
                            <span>${data.system?.year || '2026'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-school"></i>
                        <div>
                            <strong>Établissement :</strong>
                            <span>${data.system?.ecole || 'Cours privés Source de la Fontaine'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-users"></i>
                        <div>
                            <strong>Candidates :</strong>
                            <span>${data.statistics?.candidates || '0'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-vote-yea"></i>
                        <div>
                            <strong>Votes enregistrés :</strong>
                            <span>${data.statistics?.votes || '0'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-chart-line"></i>
                        <div>
                            <strong>Participation :</strong>
                            <span>${data.statistics?.participation_rate || '0'}%</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-clock"></i>
                        <div>
                            <strong>Dernière mise à jour :</strong>
                            <span>${new Date(data.system?.timestamp).toLocaleTimeString('fr-FR')}</span>
                        </div>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur chargement info:', error);
    }
}

function hideSystemInfoModal() {
    if (elements.systemInfoModal) {
        elements.systemInfoModal.style.opacity = '0';
        setTimeout(() => {
            elements.systemInfoModal.style.display = 'none';
        }, 300);
    }
}

function showAccessibilityInfo() {
    if (elements.accessibilityModal) {
        elements.accessibilityModal.style.display = 'flex';
        elements.accessibilityModal.style.opacity = '0';
        
        setTimeout(() => {
            elements.accessibilityModal.style.transition = 'opacity 0.3s ease';
            elements.accessibilityModal.style.opacity = '1';
        }, 10);
    }
}

function hideAccessibilityModal() {
    if (elements.accessibilityModal) {
        elements.accessibilityModal.style.opacity = '0';
        setTimeout(() => {
            elements.accessibilityModal.style.display = 'none';
        }, 300);
    }
}

// ==================== FONCTIONS UTILITAIRES ====================

function showLoader(message = 'Chargement...') {
    if (elements.loaderMessage) {
        elements.loaderMessage.textContent = message;
        elements.loaderMessage.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${message}`;
    }
    if (elements.globalLoader) {
        elements.globalLoader.style.display = 'flex';
        elements.globalLoader.style.opacity = '0';
        
        setTimeout(() => {
            elements.globalLoader.style.transition = 'opacity 0.3s ease';
            elements.globalLoader.style.opacity = '1';
        }, 10);
    }
}

function hideLoader() {
    if (elements.globalLoader) {
        elements.globalLoader.style.opacity = '0';
        setTimeout(() => {
            elements.globalLoader.style.display = 'none';
        }, 300);
    }
}

function showStatus(message, type = 'info') {
    if (!elements.statusMessage || !elements.statusBanner) return;
    
    const icons = {
        info: '📡',
        success: '✅',
        warning: '⚠️',
        error: '❌'
    };
    
    elements.statusMessage.innerHTML = `${icons[type] || ''} ${message}`;
    
    const colors = {
        info: '#4361ee',
        success: '#2ecc71',
        warning: '#f39c12',
        error: '#e74c3c'
    };
    
    if (colors[type]) {
        elements.statusBanner.style.borderLeftColor = colors[type];
        elements.statusBanner.style.background = `${colors[type]}10`;
    }
    
    // Animation
    elements.statusBanner.style.opacity = '0';
    elements.statusBanner.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
        elements.statusBanner.style.transition = 'all 0.3s ease';
        elements.statusBanner.style.opacity = '1';
        elements.statusBanner.style.transform = 'translateY(0)';
    }, 10);
}

function showError(title, message) {
    console.error(title, message);
    showStatus(`❌ ${title}`, 'error');
    
    if (title.includes('connexion') || title.includes('serveur') || title.includes('indisponible')) {
        showErrorSection(title, message);
    }
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function getInitials(firstName, lastName) {
    if (!firstName || !lastName) return '??';
    return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
}

function getColorByClass(classe) {
    const colorMap = {
        '2nde': 'linear-gradient(135deg, #4361ee, #3a0ca3)',
        '3ème': 'linear-gradient(135deg, #4cc9f0, #3a86ff)',
        '4ème': 'linear-gradient(135deg, #7209b7, #560bad)',
        '5ème': 'linear-gradient(135deg, #f72585, #b5179e)',
        '6ème': 'linear-gradient(135deg, #2ecc71, #27ae60)'
    };
    
    return colorMap[classe] || 'linear-gradient(135deg, #6c757d, #495057)';
}

function formatDateTime(date) {
    if (!date || isNaN(new Date(date))) return '--';
    
    return new Date(date).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function refreshData() {
    showLoader('Actualisation des données...');
    loadSystemStatus()
        .then(() => showStatus('✅ Données actualisées', 'success'))
        .catch(() => showStatus('❌ Erreur d\'actualisation', 'error'))
        .finally(() => hideLoader());
}

function logout() {
    clearUserSession();
    clearSelection();
    hideAllSections();
    
    if (elements.emailSection) {
        elements.emailSection.style.display = 'block';
    }
    
    showStatus('👋 Session terminée • Prêt pour la vérification', 'info');
    playLogoutSound();
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

function updateFooterYear() {
    if (elements.footerYear) {
        elements.footerYear.textContent = new Date().getFullYear();
    }
}

async function fetchWithTimeout(url, options = {}) {
    const { timeout = 10000, ...fetchOptions } = options;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Timeout dépassé - Le serveur met trop de temps à répondre');
        }
        throw error;
    }
}

function playSuccessSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 523.25; // Do
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        // Audio non supporté ou bloqué - silence
    }
}

function playLogoutSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 392.00; // Sol
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
        // Audio non supporté ou bloqué - silence
    }
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
        
        // Raccourci Ctrl+R pour rafraîchir (avec confirmation)
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            if (confirm('Actualiser les données du système ?')) {
                refreshData();
            }
        }
    });
    
    // Validation email en temps réel
    if (elements.emailInput) {
        elements.emailInput.addEventListener('input', () => {
            if (elements.emailError) {
                elements.emailError.style.display = 'none';
            }
        });
        
        // Auto-focus sur l'email si la section est visible
        if (elements.emailSection && elements.emailSection.style.display !== 'none') {
            setTimeout(() => {
                elements.emailInput.focus();
            }, 100);
        }
    }
    
    // Online/Offline detection
    window.addEventListener('online', () => {
        showStatus('✅ Connexion rétablie', 'success');
        setTimeout(() => refreshData(), 1000);
    });
    
    window.addEventListener('offline', () => {
        showStatus('❌ Hors ligne - Reconnexion en cours...', 'error');
    });
    
    // Validation email avec Entrée
    elements.emailInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            verifyEmail();
        }
    });
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
console.log('Candidates:');
console.log('  • Binta Diallo (3ème)');
console.log('  • Maguette Ngom (6ème)');
console.log('  • Eléna Nafissatou Gomis (5ème)');
console.log('  • Diasse Séne (2nde)');
console.log('  • Ndeye Fatou Ndong (4ème)');
console.log('Version: 2.0.0');
console.log('URL:', window.location.origin);
console.log('Timestamp:', new Date().toLocaleString('fr-FR'));