// ==================== CONFIGURATION POUR RENDER ====================
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1';

const API_BASE_URL = isLocal 
    ? 'http://localhost:5000/api' 
    : 'https://vote-backend.onrender.com/api';

console.log(`🌐 Environnement: ${isLocal ? 'Local' : 'Production'}`);
console.log(`🔗 API URL: ${API_BASE_URL}`);

let currentElection = null;
let selectedCandidate = null;
let userEmail = null;

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Application de vote scolaire démarrée');
    initApp();
    setupEventListeners();
    loadHomeStats();
    updateDirectLink();
    updateElectionTimer();
});

function initApp() {
    // Vérifier les paramètres d'URL pour le lien direct
    const urlParams = new URLSearchParams(window.location.search);
    const voteId = urlParams.get('vote');
    
    if (voteId) {
        // Mode lien direct : charger directement l'élection
        showLoading();
        loadElectionForVote();
    } else {
        // Mode normal : charger les données de base
        loadHomeStats();
    }
    
    hideLoading();
}

function setupEventListeners() {
    // Boutons principaux
    document.getElementById('start-vote-btn').addEventListener('click', startVoting);
    document.getElementById('share-link-btn').addEventListener('click', showShareModal);
    document.getElementById('view-results-btn').addEventListener('click', showResults);
    document.getElementById('view-results-confirm').addEventListener('click', showResults);
    
    // Navigation
    document.getElementById('back-button').addEventListener('click', showHome);
    document.getElementById('back-from-results').addEventListener('click', showHome);
    document.getElementById('return-home').addEventListener('click', showHome);
    
    // Email modal
    document.querySelector('.close-modal').addEventListener('click', hideEmailModal);
    document.getElementById('cancel-email').addEventListener('click', hideEmailModal);
    document.getElementById('submit-email').addEventListener('click', verifyAndVote);
    document.getElementById('email-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') verifyAndVote();
    });
    
    // Partage modal
    document.querySelector('.close-share-modal').addEventListener('click', hideShareModal);
    document.getElementById('copy-direct-link').addEventListener('click', copyDirectLink);
    document.getElementById('copy-share-link').addEventListener('click', copyShareLink);
    
    // Gestion historique navigateur
    window.addEventListener('popstate', handlePopState);
}

// ==================== TIMER ÉLECTION ====================

function updateElectionTimer() {
    // Mettre à jour le timer toutes les minutes
    setInterval(() => {
        if (currentElection && currentElection.temps_restant) {
            document.getElementById('time-remaining').textContent = currentElection.temps_restant;
        }
    }, 60000);
    
    // Charger les infos de l'élection
    fetch(`${API_BASE_URL}/election`)
        .then(response => response.json())
        .then(data => {
            currentElection = data;
            
            // Mettre à jour les infos de temps
            const timeInfo = document.getElementById('election-time-info');
            if (timeInfo) {
                if (data.can_vote) {
                    timeInfo.innerHTML = `
                        <p><i class="fas fa-clock"></i> <strong>Temps restant :</strong> 
                        <span id="time-remaining">${data.temps_restant || 'Calcul...'}</span></p>
                        <p><i class="fas fa-calendar"></i> <strong>Fin des votes :</strong> 
                        ${new Date(data.date_fin).toLocaleString('fr-FR')} GMT</p>
                    `;
                } else if (data.status === 'pending') {
                    timeInfo.innerHTML = `
                        <p><i class="fas fa-hourglass-start"></i> <strong>Début des votes :</strong> 
                        ${new Date(data.date_debut).toLocaleString('fr-FR')} GMT</p>
                    `;
                } else {
                    timeInfo.innerHTML = `
                        <p><i class="fas fa-flag-checkered"></i> <strong>Élection terminée</strong></p>
                    `;
                }
            }
        })
        .catch(error => console.log('Info temps non disponible:', error));
}

// ==================== FONCTIONS PRINCIPALES ====================

async function loadHomeStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) {
            console.log('API non disponible, vérifiez la connexion');
            return;
        }
        
        const data = await response.json();
        
        // Mettre à jour les statistiques
        document.getElementById('vote-count').textContent = `${data.statistics.total_votes} votes`;
        document.getElementById('participation-rate').textContent = `${data.statistics.participation_rate}% participation`;
        
        // Mettre à jour les infos de période
        const periodInfo = document.getElementById('period-info');
        if (periodInfo && data.periode_vote) {
            const debut = new Date(data.periode_vote.date_debut);
            const fin = new Date(data.periode_vote.date_fin);
            
            periodInfo.innerHTML = `
                <p><i class="fas fa-play-circle"></i> <strong>Début :</strong> ${debut.toLocaleString('fr-FR')} GMT</p>
                <p><i class="fas fa-stop-circle"></i> <strong>Fin :</strong> ${fin.toLocaleString('fr-FR')} GMT</p>
                ${data.periode_vote.vote_actif ? 
                    '<p class="vote-active"><i class="fas fa-check-circle"></i> <strong>Votes actifs</strong></p>' :
                    '<p class="vote-inactive"><i class="fas fa-times-circle"></i> <strong>Votes fermés</strong></p>'
                }
            `;
        }
        
    } catch (error) {
        console.log('Statistiques non disponibles:', error);
    }
}

function startVoting() {
    showLoading();
    
    // Charger l'élection
    fetch(`${API_BASE_URL}/election`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            currentElection = data;
            
            // Vérifier si les votes sont actifs
            if (!data.can_vote) {
                let message = '';
                if (data.status === 'pending') {
                    message = `Les votes commencent le ${new Date(data.date_debut).toLocaleString('fr-FR')} GMT`;
                } else {
                    message = `Les votes sont terminés depuis le ${new Date(data.date_fin).toLocaleString('fr-FR')} GMT`;
                }
                
                showNotification(message, 'warning');
                hideLoading();
                return;
            }
            
            showVoteInterface();
            displayCandidates();
            hideLoading();
        })
        .catch(error => {
            console.error('Erreur chargement élection:', error);
            showNotification(`Erreur: ${error.message}`, 'error');
            hideLoading();
        });
}

function showVoteInterface() {
    document.getElementById('home-section').style.display = 'none';
    document.getElementById('vote-section').style.display = 'block';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('confirmation-section').style.display = 'none';
    
    // Mettre à jour l'URL pour le partage
    const newUrl = `${window.location.pathname}?vote=${currentElection.id}`;
    window.history.pushState({}, '', newUrl);
}

function displayCandidates() {
    const voteContent = document.getElementById('vote-content');
    
    if (!currentElection || !currentElection.candidates) {
        voteContent.innerHTML = '<p class="error">Aucune candidate disponible</p>';
        return;
    }
    
    // Afficher les infos de temps
    voteContent.innerHTML = `
        <div class="vote-time-info">
            <h3><i class="fas fa-clock"></i> Période de vote</h3>
            <p><strong>Début :</strong> ${new Date(currentElection.date_debut).toLocaleString('fr-FR')} GMT</p>
            <p><strong>Fin :</strong> ${new Date(currentElection.date_fin).toLocaleString('fr-FR')} GMT</p>
            <p><strong>Temps restant :</strong> ${currentElection.temps_restant || ''}</p>
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                <p><strong>Important :</strong> Un seul vote par professeur. Vérification par email académique.</p>
            </div>
        </div>
        
        <h3><i class="fas fa-female"></i> Candidates :</h3>
        <p class="section-subtitle">Sélectionnez la candidate de votre choix</p>
        
        <div id="candidates-container" class="candidates-grid">
            ${currentElection.candidates.map((candidate, index) => `
                <div class="candidate-card" data-id="${candidate.id}">
                    <div class="candidate-header">
                        <img src="${candidate.photo_url || `https://ui-avatars.com/api/?name=${candidate.prenom}+${candidate.nom}&background=4361ee&color=fff&size=100`}" 
                             alt="${candidate.prenom} ${candidate.nom}" 
                             class="candidate-photo">
                        <div class="candidate-info">
                            <h4 class="candidate-name">${candidate.prenom} ${candidate.nom}</h4>
                            <span class="candidate-class">Classe de ${candidate.classe}</span>
                            <div class="candidate-votes">
                                <i class="fas fa-vote-yea"></i> ${candidate.votes_count} votes
                            </div>
                        </div>
                    </div>
                    <p class="candidate-description">"${candidate.description}"</p>
                    <div class="select-indicator">
                        <i class="fas fa-check"></i>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="vote-actions">
            <button class="btn-secondary" onclick="showHome()">
                <i class="fas fa-times"></i> Annuler
            </button>
            <button id="confirm-vote-btn" class="btn-primary" onclick="showEmailModal()" disabled>
                <i class="fas fa-check"></i> Confirmer mon vote
            </button>
        </div>
    `;
    
    // Ajouter les événements de sélection
    const candidatesContainer = document.getElementById('candidates-container');
    const confirmBtn = document.getElementById('confirm-vote-btn');
    
    candidatesContainer.querySelectorAll('.candidate-card').forEach(card => {
        card.addEventListener('click', () => {
            // Désélectionner toutes les cartes
            candidatesContainer.querySelectorAll('.candidate-card').forEach(c => {
                c.classList.remove('selected');
            });
            
            // Sélectionner cette carte
            card.classList.add('selected');
            selectedCandidate = parseInt(card.dataset.id);
            confirmBtn.disabled = false;
        });
    });
}

// ==================== VOTE ====================

function showEmailModal() {
    document.getElementById('email-modal').style.display = 'flex';
    document.getElementById('email-input').value = '';
    document.getElementById('email-error').style.display = 'none';
    document.getElementById('email-input').focus();
}

function hideEmailModal() {
    document.getElementById('email-modal').style.display = 'none';
}

async function verifyAndVote() {
    const email = document.getElementById('email-input').value.trim();
    const emailError = document.getElementById('email-error');
    
    // Validation basique
    if (!email || !email.includes('@')) {
        emailError.textContent = 'Veuillez entrer une adresse email académique valide';
        emailError.style.display = 'block';
        return;
    }
    
    // Vérifier si l'email a déjà voté
    try {
        const response = await fetch(`${API_BASE_URL}/verify-email`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.has_voted) {
            emailError.textContent = 'Cet email a déjà voté pour cette élection';
            emailError.style.display = 'block';
            return;
        }
        
        // Vérifier si l'élection est active
        if (!data.can_vote) {
            emailError.textContent = `Les votes ne sont pas actifs. ${data.vote_period}`;
            emailError.style.display = 'block';
            return;
        }
        
        // Si tout est OK, soumettre le vote
        userEmail = email;
        hideEmailModal();
        submitVote();
        
    } catch (error) {
        console.error('Erreur vérification email:', error);
        emailError.textContent = `Erreur de vérification: ${error.message}`;
        emailError.style.display = 'block';
    }
}

async function submitVote() {
    showLoading();
    
    try {
        const voteData = {
            professeur_email: userEmail,
            candidate_id: selectedCandidate
        };
        
        console.log('📤 Envoi vote:', voteData);
        
        const response = await fetch(`${API_BASE_URL}/vote`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(voteData)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Afficher l'erreur détaillée
            const errorMsg = data.error || 'Erreur lors du vote';
            throw new Error(errorMsg);
        }
        
        // Succès !
        showConfirmation(data);
        loadHomeStats(); // Mettre à jour les stats
        
    } catch (error) {
        console.error('Erreur vote:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
        showHome();
    } finally {
        hideLoading();
    }
}

function showConfirmation(voteData) {
    const candidate = currentElection.candidates.find(c => c.id === selectedCandidate);
    
    document.getElementById('home-section').style.display = 'none';
    document.getElementById('vote-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('confirmation-section').style.display = 'block';
    
    document.getElementById('vote-details').innerHTML = `
        <p><i class="fas fa-user-check"></i> <strong>Votre choix :</strong> ${candidate.prenom} ${candidate.nom}</p>
        <p><i class="fas fa-graduation-cap"></i> <strong>Classe :</strong> ${candidate.classe}</p>
        <p><i class="fas fa-envelope"></i> <strong>Email vérifié :</strong> ${userEmail}</p>
        <p><i class="fas fa-clock"></i> <strong>Heure du vote :</strong> ${new Date().toLocaleString('fr-FR')}</p>
        <p><i class="fas fa-vote-yea"></i> <strong>Total votes pour cette candidate :</strong> ${candidate.votes_count}</p>
    `;
    
    // Nettoyer l'URL
    window.history.replaceState({}, '', window.location.pathname);
    showNotification('✅ Vote enregistré avec succès !', 'success');
}

// ==================== RÉSULTATS ====================

async function showResults() {
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/results`);
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        document.getElementById('home-section').style.display = 'none';
        document.getElementById('vote-section').style.display = 'none';
        document.getElementById('confirmation-section').style.display = 'none';
        document.getElementById('results-section').style.display = 'block';
        
        displayResults(data);
        
    } catch (error) {
        console.error('Erreur chargement résultats:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function displayResults(data) {
    const resultsContent = document.getElementById('results-content');
    
    resultsContent.innerHTML = `
        <div class="results-container">
            <div class="results-header">
                <h3>Résultats de l'élection</h3>
                <p>${currentElection ? currentElection.titre : data.election.titre}</p>
                ${data.is_finished ? 
                    '<div class="alert alert-success"><i class="fas fa-flag-checkered"></i> Élection terminée</div>' :
                    '<div class="alert alert-info"><i class="fas fa-clock"></i> Résultats en temps réel</div>'
                }
            </div>
            
            <div class="results-stats">
                <div class="result-stat">
                    <span class="result-stat-value">${data.total_votes}</span>
                    <span class="result-stat-label">Votes totaux</span>
                </div>
                <div class="result-stat">
                    <span class="result-stat-value">${data.results.length}</span>
                    <span class="result-stat-label">Candidates</span>
                </div>
                <div class="result-stat">
                    <span class="result-stat-value">${data.total_votes > 0 ? Math.round((data.total_votes / 50) * 100) : 0}%</span>
                    <span class="result-stat-label">Participation</span>
                </div>
            </div>
            
            <div class="results-list">
                ${data.results.map((result, index) => `
                    <div class="result-item ${index === 0 ? 'winner' : ''}">
                        <div class="result-rank">${index + 1}</div>
                        <div class="result-details">
                            <div class="result-name">${result.candidate.nom_complet}</div>
                            <div class="result-class">Classe de ${result.candidate.classe}</div>
                            <div class="result-description">${result.candidate.description}</div>
                        </div>
                        <div class="result-bar-container">
                            <div class="result-bar">
                                <div class="result-bar-fill" style="width: ${result.percentage}%"></div>
                            </div>
                            <div class="result-numbers">
                                <span>${result.votes} votes</span>
                                <span>${result.percentage}%</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <div class="results-footer">
                <p><i class="fas fa-database"></i> Données en temps réel depuis PostgreSQL</p>
                <p><i class="fas fa-calendar"></i> Période de vote : ${new Date(data.election.date_debut).toLocaleString('fr-FR')} GMT - ${new Date(data.election.date_fin).toLocaleString('fr-FR')} GMT</p>
                <p><small>Mis à jour : ${new Date().toLocaleString('fr-FR')}</small></p>
            </div>
        </div>
    `;
}

// ==================== PARTAGE ====================

function updateDirectLink() {
    const baseUrl = window.location.origin + window.location.pathname;
    const voteUrl = currentElection ? `${baseUrl}?vote=${currentElection.id}` : baseUrl;
    
    const directLink = document.getElementById('direct-link');
    const shareLinkInput = document.getElementById('share-link-input');
    
    if (directLink) directLink.textContent = voteUrl;
    if (shareLinkInput) shareLinkInput.value = voteUrl;
}

function showShareModal() {
    updateDirectLink();
    document.getElementById('share-modal').style.display = 'flex';
}

function hideShareModal() {
    document.getElementById('share-modal').style.display = 'none';
}

function copyDirectLink() {
    const link = document.getElementById('direct-link').textContent;
    copyToClipboard(link, 'Lien copié !');
}

function copyShareLink() {
    const link = document.getElementById('share-link-input').value;
    copyToClipboard(link, 'Lien copié dans le presse-papier !');
}

function shareViaEmail() {
    const link = document.getElementById('share-link-input').value;
    const subject = encodeURIComponent('Vote des délégués élèves');
    const body = encodeURIComponent(`Bonjour,\n\nVous pouvez voter pour les délégués élèves via ce lien :\n${link}\n\nPériode de vote : 8-10 février 2026\n\nCordialement,`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
}

function shareViaWhatsApp() {
    const link = document.getElementById('share-link-input').value;
    const text = encodeURIComponent(`Vote des délégués élèves\nLien: ${link}\nPériode: 8-10 février 2026`);
    window.open(`https://wa.me/?text=${text}`);
}

function shareViaTeams() {
    const link = document.getElementById('share-link-input').value;
    const text = encodeURIComponent(`Vote des délégués élèves\n\nLien: ${link}\n\nPériode de vote:\n• Début: 8 février 2026\n• Fin: 10 février 2026\n\nUn seul vote par professeur`);
    window.open(`https://teams.microsoft.com/share?text=${text}`);
}

// ==================== NAVIGATION ====================

function showHome() {
    document.getElementById('home-section').style.display = 'block';
    document.getElementById('vote-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('confirmation-section').style.display = 'none';
    
    selectedCandidate = null;
    userEmail = null;
    
    // Nettoyer l'URL
    window.history.replaceState({}, '', window.location.pathname);
    loadHomeStats(); // Recharger les stats
}

function handlePopState() {
    const urlParams = new URLSearchParams(window.location.search);
    const voteId = urlParams.get('vote');
    
    if (voteId && currentElection) {
        showVoteInterface();
    } else {
        showHome();
    }
}

// ==================== LIEN DIRECT ====================

async function loadElectionForVote() {
    try {
        const response = await fetch(`${API_BASE_URL}/election`);
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        currentElection = await response.json();
        
        showVoteInterface();
        displayCandidates();
        
    } catch (error) {
        console.error('Erreur chargement élection directe:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
        showHome();
    }
}

// ==================== UTILITAIRES ====================

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notification-text');
    
    notificationText.textContent = message;
    
    // Changer la couleur selon le type
    if (type === 'error') {
        notification.style.background = '#f72585';
        notification.style.color = 'white';
    } else if (type === 'success') {
        notification.style.background = '#4cc9f0';
        notification.style.color = 'white';
    } else if (type === 'warning') {
        notification.style.background = '#f39c12';
        notification.style.color = 'black';
    } else {
        notification.style.background = '#4361ee';
        notification.style.color = 'white';
    }
    
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function showLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'flex';
}

function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
}

function copyToClipboard(text, message) {
    navigator.clipboard.writeText(text)
        .then(() => showNotification(message, 'success'))
        .catch(() => {
            // Fallback pour anciens navigateurs
            const tempInput = document.createElement('input');
            tempInput.value = text;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            showNotification(message, 'success');
        });
}

// Version alternative pour le débogage
function testConnection() {
    console.log('🔗 Test de connexion à l\'API...');
    fetch(`${API_BASE_URL}/status`)
        .then(response => {
            console.log('Status:', response.status);
            if (response.ok) {
                return response.json();
            }
            throw new Error(`HTTP ${response.status}`);
        })
        .then(data => {
            console.log('✅ API connectée:', data);
            showNotification('✅ Connecté à l\'API', 'success');
        })
        .catch(error => {
            console.error('❌ API non accessible:', error);
            showNotification('❌ API non accessible', 'error');
        });
}

// Tester la connexion au chargement
setTimeout(testConnection, 1000);