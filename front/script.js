// Configuration de l'API
const API_BASE_URL = window.location.origin;
const API_ENDPOINTS = {
    election: `${API_BASE_URL}/api/election`,
    vote: `${API_BASE_URL}/api/vote`,
    results: `${API_BASE_URL}/api/results`,
    stats: `${API_BASE_URL}/api/stats`,
    status: `${API_BASE_URL}/api/status`,
    verifyEmail: `${API_BASE_URL}/api/verify-email`
};

// Variables globales
let currentElection = null;
let candidates = [];
let selectedCandidate = null;
let userEmail = null;
let hasVoted = false;
let electionStatus = '';

// Éléments DOM
const elements = {
    electionInfo: document.getElementById('electionInfo'),
    statusBanner: document.getElementById('statusBanner'),
    statusMessage: document.getElementById('statusMessage'),
    timeRemaining: document.getElementById('timeRemaining'),
    votesCount: document.getElementById('votesCount'),
    emailSection: document.getElementById('emailSection'),
    candidatesSection: document.getElementById('candidatesSection'),
    resultsSection: document.getElementById('resultsSection'),
    alreadyVotedSection: document.getElementById('alreadyVotedSection'),
    emailInput: document.getElementById('emailInput'),
    verifyBtn: document.getElementById('verifyBtn'),
    candidatesGrid: document.getElementById('candidatesGrid'),
    selectedCandidate: document.getElementById('selectedCandidate'),
    selectedInfo: document.getElementById('selectedInfo'),
    voteBtn: document.getElementById('voteBtn'),
    totalVotes: document.getElementById('totalVotes'),
    participationRate: document.getElementById('participationRate'),
    timeLeft: document.getElementById('timeLeft'),
    resultsList: document.getElementById('resultsList'),
    confirmationModal: document.getElementById('confirmationModal'),
    successModal: document.getElementById('successModal'),
    confirmCandidate: document.getElementById('confirmCandidate')
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    loadElectionData();
    updateClock();
    setInterval(updateClock, 60000); // Mettre à jour l'horloge chaque minute
});

// Charger les données de l'élection
async function loadElectionData() {
    try {
        const response = await fetch(API_ENDPOINTS.status);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        currentElection = data.election;
        electionStatus = data.election.status;
        
        // Mettre à jour l'interface
        updateElectionDisplay(data);
        
        // Charger les candidats si l'élection est active
        if (electionStatus === 'active') {
            await loadCandidates();
        }
        
    } catch (error) {
        console.error('Erreur de chargement:', error);
        showError('Impossible de se connecter au serveur');
    }
}

// Mettre à jour l'affichage de l'élection
function updateElectionDisplay(data) {
    const election = data.election;
    const stats = data.statistics;
    
    // Mettre à jour les informations
    if (elements.timeRemaining) {
        elements.timeRemaining.textContent = election.temps_restant || '--';
    }
    
    if (elements.votesCount) {
        elements.votesCount.textContent = stats.votes || 0;
    }
    
    // Mettre à jour la bannière de statut
    let statusText = '';
    let statusColor = '#4361ee';
    
    switch (election.status) {
        case 'active':
            statusText = `Élection en cours • ${election.temps_restant} restant`;
            statusColor = '#4cc9f0';
            break;
        case 'pending':
            statusText = `Élection débutera le ${formatDate(election.date_debut)}`;
            statusColor = '#f72585';
            break;
        case 'finished':
            statusText = 'Élection terminée • Résultats disponibles';
            statusColor = '#7209b7';
            break;
        default:
            statusText = 'Statut inconnu';
    }
    
    if (elements.statusMessage) {
        elements.statusMessage.textContent = statusText;
    }
    
    if (elements.statusBanner) {
        elements.statusBanner.style.borderLeftColor = statusColor;
    }
}

// Charger les candidats
async function loadCandidates() {
    try {
        const response = await fetch(API_ENDPOINTS.election);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        candidates = data.candidates || [];
        currentElection = data;
        
        // Afficher les candidats
        displayCandidates(candidates);
        
    } catch (error) {
        console.error('Erreur chargement candidats:', error);
        showError('Impossible de charger les candidats');
    }
}

// Afficher les candidats
function displayCandidates(candidatesList) {
    if (!elements.candidatesGrid) return;
    
    elements.candidatesGrid.innerHTML = '';
    
    candidatesList.forEach(candidate => {
        const card = document.createElement('div');
        card.className = 'candidate-card';
        card.dataset.id = candidate.id;
        
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
                ${candidate.description || 'Pas de description disponible.'}
            </div>
            <div class="candidate-votes">
                <span>${candidate.votes_count || 0} votes</span>
                <button class="select-btn" onclick="selectCandidate(${candidate.id})">
                    <i class="fas fa-check"></i> Sélectionner
                </button>
            </div>
        `;
        
        card.onclick = (e) => {
            if (!e.target.closest('.select-btn')) {
                selectCandidate(candidate.id);
            }
        };
        
        elements.candidatesGrid.appendChild(card);
    });
}

// Vérifier l'email
async function verifyEmail() {
    const email = elements.emailInput.value.trim();
    
    if (!email || !validateEmail(email)) {
        showError('Veuillez entrer un email professionnel valide');
        return;
    }
    
    userEmail = email;
    
    // Désactiver le bouton pendant la vérification
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
            showError(data.error);
            elements.verifyBtn.disabled = false;
            elements.verifyBtn.innerHTML = '<i class="fas fa-check"></i> Vérifier';
            return;
        }
        
        hasVoted = data.has_voted;
        
        if (hasVoted) {
            // L'utilisateur a déjà voté
            showAlreadyVoted();
        } else {
            // L'utilisateur peut voter
            if (data.can_vote) {
                showCandidatesSection();
            } else {
                showError('Le vote n\'est pas encore ouvert ou est terminé');
            }
        }
        
    } catch (error) {
        console.error('Erreur vérification email:', error);
        showError('Erreur de connexion au serveur');
    } finally {
        elements.verifyBtn.disabled = false;
        elements.verifyBtn.innerHTML = '<i class="fas fa-check"></i> Vérifier';
    }
}

// Sélectionner une candidate
function selectCandidate(candidateId) {
    // Retirer la sélection précédente
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Ajouter la nouvelle sélection
    const selectedCard = document.querySelector(`.candidate-card[data-id="${candidateId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // Trouver la candidate
    selectedCandidate = candidates.find(c => c.id === candidateId);
    
    if (selectedCandidate) {
        // Afficher les informations de sélection
        elements.selectedInfo.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-photo" style="background: ${getRandomColor()}">
                    ${getInitials(selectedCandidate.prenom, selectedCandidate.nom)}
                </div>
                <div class="candidate-info">
                    <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                    <div class="candidate-class">${selectedCandidate.classe}</div>
                </div>
            </div>
            <div class="candidate-description">
                ${selectedCandidate.description || 'Pas de description disponible.'}
            </div>
        `;
        
        // Afficher la section de confirmation
        elements.selectedCandidate.style.display = 'block';
        
        // Scroll vers la section
        elements.selectedCandidate.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Soumettre le vote
function submitVote() {
    if (!selectedCandidate || !userEmail) {
        showError('Veuillez sélectionner une candidate et vérifier votre email');
        return;
    }
    
    // Afficher la modal de confirmation
    elements.confirmCandidate.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-photo" style="background: ${getRandomColor()}">
                ${getInitials(selectedCandidate.prenom, selectedCandidate.nom)}
            </div>
            <div class="candidate-info">
                <h3>${selectedCandidate.prenom} ${selectedCandidate.nom}</h3>
                <div class="candidate-class">${selectedCandidate.classe}</div>
            </div>
        </div>
        <p><strong>Email :</strong> ${userEmail}</p>
    `;
    
    elements.confirmationModal.style.display = 'flex';
}

// Confirmer le vote (appelé depuis la modal)
async function confirmVote() {
    hideModal();
    
    // Désactiver le bouton
    elements.voteBtn.disabled = true;
    elements.voteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';
    
    try {
        const response = await fetch(API_ENDPOINTS.vote, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                professeur_email: userEmail,
                candidate_id: selectedCandidate.id
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            elements.voteBtn.disabled = false;
            elements.voteBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Confirmer mon vote';
            return;
        }
        
        // Succès !
        showSuccessModal();
        hasVoted = true;
        
        // Recharger les données
        setTimeout(() => {
            loadElectionData();
            showAlreadyVoted();
        }, 3000);
        
    } catch (error) {
        console.error('Erreur envoi vote:', error);
        showError('Erreur d\'envoi du vote');
        elements.voteBtn.disabled = false;
        elements.voteBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Confirmer mon vote';
    }
}

// Afficher les résultats
async function showResults() {
    try {
        const response = await fetch(API_ENDPOINTS.results);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Mettre à jour les statistiques
        if (elements.totalVotes) {
            elements.totalVotes.textContent = data.total_votes || 0;
        }
        
        if (elements.participationRate) {
            const rate = data.results.length > 0 ? 
                Math.round(data.total_votes / 50 * 100) : 0;
            elements.participationRate.textContent = `${rate}%`;
        }
        
        if (elements.timeLeft && currentElection) {
            elements.timeLeft.textContent = currentElection.temps_restant || '--';
        }
        
        // Afficher les résultats
        displayResults(data.results);
        
        // Afficher la section résultats
        hideAllSections();
        elements.resultsSection.style.display = 'block';
        
    } catch (error) {
        console.error('Erreur chargement résultats:', error);
        showError('Impossible de charger les résultats');
    }
}

// Afficher les résultats
function displayResults(results) {
    if (!elements.resultsList) return;
    
    elements.resultsList.innerHTML = '';
    
    results.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        item.innerHTML = `
            <div class="result-info">
                <div class="result-rank">${index + 1}</div>
                <div class="result-name">
                    <h4>${result.candidate.nom_complet}</h4>
                    <div class="result-class">${result.candidate.classe}</div>
                </div>
            </div>
            <div class="result-bar">
                <div class="bar-fill" style="width: ${Math.min(result.percentage, 100)}%"></div>
            </div>
            <div class="result-numbers">
                <div class="result-votes">${result.votes} votes</div>
                <div class="result-percentage">${result.percentage.toFixed(1)}%</div>
            </div>
        `;
        
        elements.resultsList.appendChild(item);
    });
}

// Afficher la section des candidats
function showCandidatesSection() {
    hideAllSections();
    elements.candidatesSection.style.display = 'block';
}

// Afficher la section "déjà voté"
function showAlreadyVoted() {
    hideAllSections();
    elements.alreadyVotedSection.style.display = 'block';
}

// Cacher toutes les sections
function hideAllSections() {
    elements.emailSection.style.display = 'none';
    elements.candidatesSection.style.display = 'none';
    elements.resultsSection.style.display = 'none';
    elements.alreadyVotedSection.style.display = 'none';
}

// Cacher la modal
function hideModal() {
    elements.confirmationModal.style.display = 'none';
}

// Cacher la modal de succès
function hideSuccessModal() {
    elements.successModal.style.display = 'none';
}

// Afficher la modal de succès
function showSuccessModal() {
    elements.successModal.style.display = 'flex';
}

// Actualiser les données
function refreshData() {
    loadElectionData();
    if (hasVoted) {
        showResults();
    }
}

// Mettre à jour l'horloge
function updateClock() {
    if (elements.timeRemaining && currentElection && currentElection.temps_restant) {
        elements.timeRemaining.textContent = currentElection.temps_restant;
    }
}

// Fonctions utilitaires
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function getInitials(firstName, lastName) {
    return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
}

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

function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showError(message) {
    // Simple affichage d'erreur
    alert(`Erreur : ${message}`);
}

// Exposer les fonctions au scope global
window.verifyEmail = verifyEmail;
window.selectCandidate = selectCandidate;
window.submitVote = submitVote;
window.confirmVote = confirmVote;
window.showResults = showResults;
window.hideModal = hideModal;
window.hideSuccessModal = hideSuccessModal;
window.refreshData = refreshData;