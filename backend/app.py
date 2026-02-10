from flask import Flask, request, jsonify, send_from_directory, redirect, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import sys
import hashlib
import secrets
from dotenv import load_dotenv

# ==================== CHARGEMENT CONFIGURATION ====================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_PATH = os.path.join(PROJECT_ROOT, 'front')

print("=" * 80)
print("🚀 SYSTÈME DE VOTE SCOLAIRE 2026 - BACKEND FLASK")
print("=" * 80)

if not os.path.exists(FRONTEND_PATH):
    os.makedirs(FRONTEND_PATH, exist_ok=True)

# ==================== CONFIGURATION FLASK ====================

app = Flask(__name__, 
            static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None,
            static_url_path='')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app, supports_credentials=True)

# ==================== CONFIGURATION BASE DE DONNÉES ====================

SQLITE_DB_PATH = os.path.join(BASE_DIR, 'votes.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{SQLITE_DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODÈLES DE BASE DE DONNÉES ====================

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    classe = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'))
    votes_count = db.Column(db.Integer, default=0)
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'))
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    professeur_email = db.Column(db.String(150), nullable=False)
    date_vote = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    
    __table_args__ = (
        db.UniqueConstraint('election_id', 'professeur_email', name='unique_vote_per_election'),
    )

# ==================== INITIALISATION BASE DE DONNÉES ====================

def init_database():
    """Initialise la base de données avec des données de test"""
    with app.app_context():
        try:
            print("🔗 Création des tables...")
            db.create_all()
            print("✅ Tables créées")
            
            # Créer une élection si elle n'existe pas
            election = Election.query.first()
            if not election:
                election = Election(
                    titre="Élection des Délégués Élèves 2026",
                    date_debut=datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc),
                    date_fin=datetime(2026, 2, 13, 23, 59, 59, tzinfo=timezone.utc),
                    statut='active'
                )
                db.session.add(election)
                db.session.commit()
                print("✅ Élection créée")
            
            # Créer les candidates si elles n'existent pas
            if Candidate.query.count() == 0:
                candidates_data = [
                    ('Diallo', 'Binta', '3ème', 'Candidate sérieuse et impliquée'),
                    ('Ngom', 'Maguette', '6ème', 'Dynamique et à l\'écoute'),
                    ('Gomis', 'Eléna Nafissatou', '5ème', 'Responsable et organisée'),
                    ('Séne', 'Diasse', '2nde', 'Créative et motivante'),
                    ('Ndong', 'Ndeye Fatou', '4ème', 'Sait communiquer et représenter')
                ]
                
                for nom, prenom, classe, description in candidates_data:
                    candidate = Candidate(
                        nom=nom,
                        prenom=prenom,
                        classe=classe,
                        description=description,
                        election_id=election.id,
                        votes_count=0
                    )
                    db.session.add(candidate)
                
                db.session.commit()
                print(f"✅ {len(candidates_data)} candidates créées")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

# ==================== ROUTES STATIQUES ====================

@app.route('/')
def serve_index():
    """Sert la page principale de vote"""
    try:
        return send_from_directory(FRONTEND_PATH, 'index.html')
    except:
        return fallback_index()

@app.route('/admin')
def admin_redirect():
    """Redirige /admin vers la page de connexion"""
    return redirect('/admin-login')

@app.route('/admin-login')
def admin_login():
    """Page de connexion admin"""
    try:
        return send_from_directory(FRONTEND_PATH, 'admin-login.html')
    except:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Admin Login</title></head>
        <body>
            <h1>Connexion Admin</h1>
            <form onsubmit="login()">
                <input type="password" id="password" placeholder="Mot de passe admin">
                <button>Se connecter</button>
            </form>
            <script>
                function login() {
                    event.preventDefault();
                    if(document.getElementById('password').value === 'admin2026') {
                        // CORRECTION : redirection sans .html
                        window.location.href = '/admin-dashboard';
                    } else {
                        alert('Mot de passe incorrect');
                    }
                }
            </script>
        </body>
        </html>
        '''

@app.route('/admin-dashboard')
def admin_dashboard():
    """Tableau de bord admin"""
    try:
        return send_from_directory(FRONTEND_PATH, 'admin-dashboard.html')
    except:
        # Dashboard de fallback amélioré
        return '''
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tableau de Bord Admin</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                header {
                    background: linear-gradient(135deg, #4361ee, #3a0ca3);
                    color: white;
                    padding: 30px;
                    border-radius: 15px;
                    margin-bottom: 30px;
                    text-align: center;
                }
                h1 {
                    margin: 0;
                    font-size: 2.5rem;
                }
                .subtitle {
                    opacity: 0.9;
                    margin-top: 10px;
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .stat-card {
                    background: #f8f9fa;
                    border-radius: 15px;
                    padding: 25px;
                    border-left: 5px solid #4361ee;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .stat-card h3 {
                    margin: 0 0 15px 0;
                    color: #333;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .stat-value {
                    font-size: 2.5rem;
                    font-weight: bold;
                    color: #4361ee;
                    margin-bottom: 5px;
                }
                .actions {
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    margin: 30px 0;
                }
                .btn {
                    padding: 15px 25px;
                    border: none;
                    border-radius: 10px;
                    font-size: 1rem;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    transition: all 0.3s;
                    text-decoration: none;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #4361ee, #3a0ca3);
                    color: white;
                }
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                }
                .btn-danger {
                    background: #dc3545;
                    color: white;
                }
                .btn:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
                }
                .results-section {
                    background: #f8f9fa;
                    border-radius: 15px;
                    padding: 25px;
                    margin-top: 30px;
                }
                .results-section h2 {
                    color: #4361ee;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th {
                    background: #4361ee;
                    color: white;
                    padding: 15px;
                    text-align: left;
                }
                td {
                    padding: 12px 15px;
                    border-bottom: 1px solid #dee2e6;
                }
                tr:hover {
                    background: #f1f3f4;
                }
                .percentage-bar {
                    background: #e9ecef;
                    border-radius: 10px;
                    height: 20px;
                    margin-top: 5px;
                    overflow: hidden;
                }
                .percentage-fill {
                    background: linear-gradient(90deg, #4361ee, #3a0ca3);
                    height: 100%;
                    border-radius: 10px;
                }
                footer {
                    text-align: center;
                    margin-top: 40px;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9rem;
                }
                .alert {
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    display: none;
                }
                .alert-success {
                    background: #d4edda;
                    color: #155724;
                    border-left: 4px solid #28a745;
                }
                .alert-error {
                    background: #f8d7da;
                    color: #721c24;
                    border-left: 4px solid #dc3545;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1><i class="fas fa-tachometer-alt"></i> Tableau de Bord Admin</h1>
                    <p class="subtitle">Système de Vote Électronique - Élections 2026</p>
                    <p style="margin-top: 15px; font-size: 0.9rem;">
                        <i class="fas fa-user-shield"></i> Interface d'administration
                    </p>
                </header>
                
                <div class="alert alert-success" id="successAlert">
                    <i class="fas fa-check-circle"></i>
                    <span id="successMessage"></span>
                </div>
                
                <div class="alert alert-error" id="errorAlert">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span id="errorMessage"></span>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3><i class="fas fa-vote-yea"></i> Votes Totaux</h3>
                        <div class="stat-value" id="totalVotes">0</div>
                        <p>Nombre total de votes enregistrés</p>
                    </div>
                    
                    <div class="stat-card">
                        <h3><i class="fas fa-users"></i> Candidates</h3>
                        <div class="stat-value" id="totalCandidates">0</div>
                        <p>Nombre de candidates en lice</p>
                    </div>
                    
                    <div class="stat-card">
                        <h3><i class="fas fa-chart-line"></i> Participation</h3>
                        <div class="stat-value" id="participation">0%</div>
                        <p>Taux de participation estimé</p>
                    </div>
                </div>
                
                <div class="actions">
                    <button class="btn btn-primary" onclick="loadResults()">
                        <i class="fas fa-sync-alt"></i>
                        Actualiser
                    </button>
                    
                    <button class="btn btn-secondary" onclick="viewFullResults()">
                        <i class="fas fa-chart-bar"></i>
                        Voir Résultats
                    </button>
                    
                    <button class="btn btn-danger" onclick="resetAllVotes()">
                        <i class="fas fa-trash-alt"></i>
                        Réinitialiser
                    </button>
                    
                    <a href="/admin-login" class="btn btn-secondary">
                        <i class="fas fa-sign-out-alt"></i>
                        Déconnexion
                    </a>
                </div>
                
                <div class="results-section">
                    <h2><i class="fas fa-poll"></i> Résultats en Temps Réel</h2>
                    <div id="resultsContainer">
                        <p>Chargement des résultats...</p>
                    </div>
                </div>
                
                <footer>
                    <p>© 2026 - Cours privés La Source de la Fontaine</p>
                    <p style="margin-top: 10px;">
                        <i class="fas fa-shield-alt"></i> Système sécurisé
                    </p>
                </footer>
            </div>
            
            <script>
                // Charger les données au démarrage
                window.onload = function() {
                    loadResults();
                };
                
                async function loadResults() {
                    try {
                        // Charger les résultats avec le secret admin
                        const response = await fetch('/api/results?admin_secret=admin2026');
                        const data = await response.json();
                        
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        
                        // Mettre à jour les statistiques
                        document.getElementById('totalVotes').textContent = data.total_votes;
                        document.getElementById('totalCandidates').textContent = data.candidates_count;
                        
                        // Calculer le pourcentage de participation
                        const participation = Math.min(Math.round((data.total_votes / 50) * 100), 100);
                        document.getElementById('participation').textContent = participation + '%';
                        
                        // Afficher les résultats
                        displayResults(data.results);
                        
                    } catch (error) {
                        console.error('Erreur:', error);
                        showError('Impossible de charger les données. Vérifiez le secret admin.');
                    }
                }
                
                function displayResults(results) {
                    let html = '<table>';
                    html += '<thead>';
                    html += '<tr>';
                    html += '<th>Rang</th>';
                    html += '<th>Candidate</th>';
                    html += '<th>Classe</th>';
                    html += '<th>Votes</th>';
                    html += '<th>Pourcentage</th>';
                    html += '</tr>';
                    html += '</thead>';
                    html += '<tbody>';
                    
                    results.forEach(result => {
                        html += '<tr>';
                        html += `<td><strong>#${result.rank}</strong></td>`;
                        html += `<td>${result.nom_complet}</td>`;
                        html += `<td>${result.classe}</td>`;
                        html += `<td>${result.votes}</td>`;
                        html += `<td>
                            ${result.percentage}%
                            <div class="percentage-bar">
                                <div class="percentage-fill" style="width: ${Math.min(result.percentage, 100)}%"></div>
                            </div>
                        </td>`;
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table>';
                    document.getElementById('resultsContainer').innerHTML = html;
                }
                
                async function viewFullResults() {
                    try {
                        const response = await fetch('/api/results?admin_secret=admin2026');
                        const data = await response.json();
                        
                        if (data.error) {
                            alert('Erreur: ' + data.error);
                            return;
                        }
                        
                        // Ouvrir dans un nouvel onglet
                        const resultsWindow = window.open('', '_blank');
                        resultsWindow.document.write(`
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <title>Résultats Détail - Élections 2026</title>
                                <style>
                                    body { font-family: Arial, sans-serif; padding: 30px; }
                                    h1 { color: #4361ee; }
                                    .result-item { 
                                        margin: 20px 0; 
                                        padding: 20px; 
                                        background: #f8f9fa; 
                                        border-radius: 10px;
                                        border-left: 5px solid #4361ee;
                                    }
                                    .rank { font-size: 24px; font-weight: bold; color: #4361ee; }
                                </style>
                            </head>
                            <body>
                                <h1>📊 Résultats Détail - Élections 2026</h1>
                                <p><strong>Total votes:</strong> ${data.total_votes}</p>
                                ${data.results.map(result => `
                                    <div class="result-item">
                                        <div class="rank">#${result.rank}</div>
                                        <h2>${result.nom_complet}</h2>
                                        <p><strong>Classe:</strong> ${result.classe}</p>
                                        <p><strong>Votes:</strong> ${result.votes}</p>
                                        <p><strong>Pourcentage:</strong> ${result.percentage}%</p>
                                    </div>
                                `).join('')}
                            </body>
                            </html>
                        `);
                        
                    } catch (error) {
                        alert('Erreur lors du chargement des résultats');
                    }
                }
                
                async function resetAllVotes() {
                    if (!confirm('⚠️ ATTENTION: Voulez-vous vraiment réinitialiser TOUS les votes ?')) {
                        return;
                    }
                    
                    try {
                        const response = await fetch('/api/admin/reset-votes?admin_secret=admin2026', {
                            method: 'POST'
                        });
                        const data = await response.json();
                        
                        if (data.success) {
                            showSuccess(`${data.votes_deleted} votes réinitialisés`);
                            // Recharger les données
                            loadResults();
                        } else {
                            showError('Erreur: ' + (data.error || 'Action non autorisée'));
                        }
                    } catch (error) {
                        showError('Erreur de connexion au serveur');
                    }
                }
                
                function showSuccess(message) {
                    const alert = document.getElementById('successAlert');
                    document.getElementById('successMessage').textContent = message;
                    alert.style.display = 'block';
                    
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 3000);
                }
                
                function showError(message) {
                    const alert = document.getElementById('errorAlert');
                    document.getElementById('errorMessage').textContent = message;
                    alert.style.display = 'block';
                    
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 5000);
                }
                
                // Actualiser automatiquement toutes les 30 secondes
                setInterval(() => {
                    loadResults();
                }, 30000);
            </script>
        </body>
        </html>
        '''

@app.route('/<path:path>')
def serve_static(path):
    """Sert les fichiers statiques"""
    try:
        return send_from_directory(FRONTEND_PATH, path)
    except:
        return jsonify({'error': 'Fichier non trouvé', 'path': path}), 404

# ==================== API PUBLIQUE ====================

@app.route('/api/status', methods=['GET'])
def api_status():
    """Statut du système"""
    try:
        election = Election.query.first()
        votes_count = Vote.query.count()
        candidates_count = Candidate.query.count()
        
        now = datetime.now(timezone.utc)
        
        # Calcul du temps restant
        temps_restant = "4j 12h"
        if election and election.date_fin:
            fin = election.date_fin
            if isinstance(fin, datetime):
                if fin.tzinfo is None:
                    fin = fin.replace(tzinfo=timezone.utc)
                diff = fin - now
                if diff.total_seconds() > 0:
                    jours = diff.days
                    heures = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    temps_restant = f"{jours}j {heures:02d}h {minutes:02d}m"
                else:
                    temps_restant = "Terminé"
        
        return jsonify({
            'system': {
                'status': 'online',
                'database': 'SQLite',
                'year': 2026,
                'ecole': 'Cours privés La Source de la Fontaine',
                'timestamp': now.isoformat()
            },
            'election': {
                'status': 'active',
                'temps_restant': temps_restant,
                'can_vote': True
            },
            'statistics': {
                'votes': votes_count,
                'candidates': candidates_count,
                'participation_rate': round((votes_count / 50) * 100, 1) if votes_count > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/election', methods=['GET'])
def api_election():
    """Données de l'élection avec candidates"""
    try:
        candidates = Candidate.query.all()
        
        candidates_list = []
        for candidate in candidates:
            candidates_list.append({
                'id': candidate.id,
                'nom': candidate.nom,
                'prenom': candidate.prenom,
                'nom_complet': candidate.nom_complet,
                'classe': candidate.classe,
                'description': candidate.description or f"Candidate pour la classe de {candidate.classe}",
                'votes_count': candidate.votes_count
            })
        
        return jsonify({
            'status': 'active',
            'title': 'Élection des Délégués Élèves 2026',
            'candidates': candidates_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
def api_verify_email():
    """Vérifie si un email peut voter"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        # Vérifier si déjà voté
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        
        if existing_vote:
            return jsonify({
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None,
                'message': 'Vous avez déjà voté pour cette élection'
            })
        
        # Sinon, peut voter
        return jsonify({
            'has_voted': False,
            'can_vote': True,
            'message': 'Vous pouvez voter',
            'email': email
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def api_vote():
    """Enregistre un vote"""
    try:
        data = request.json
        email = data.get('professeur_email', '').strip().lower()
        candidate_id = data.get('candidate_id')
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        if not candidate_id:
            return jsonify({'error': 'Candidate requis'}), 400
        
        try:
            candidate_id = int(candidate_id)
        except:
            return jsonify({'error': 'ID de candidate invalide'}), 400
        
        # Vérifier si déjà voté
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        if existing_vote:
            return jsonify({
                'error': 'Vous avez déjà voté',
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None
            }), 400
        
        # Vérifier si la candidate existe
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate non trouvée'}), 404
        
        # Créer l'élection si elle n'existe pas
        election = Election.query.first()
        if not election:
            election = Election(
                titre="Élection 2026",
                date_debut=datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc),
                date_fin=datetime(2026, 2, 13, 23, 59, 59, tzinfo=timezone.utc),
                statut='active'
            )
            db.session.add(election)
            db.session.commit()
        
        # Enregistrer le vote
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id,
            professeur_email=email,
            ip_address=request.remote_addr
        )
        
        # Mettre à jour le compteur de votes
        candidate.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        print(f"✅ Vote enregistré: {email} → {candidate.nom_complet}")
        
        return jsonify({
            'success': True,
            'message': 'Votre vote a été enregistré avec succès',
            'confirmation_id': f'VOTE-{vote.id:06d}',
            'timestamp': vote.date_vote.isoformat() if vote.date_vote else datetime.now(timezone.utc).isoformat(),
            'candidate': candidate.nom_complet,
            'classe': candidate.classe
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur vote: {str(e)}")
        return jsonify({'error': 'Erreur serveur: ' + str(e)}), 500

# ==================== API ADMIN (PROTÉGÉE) ====================

@app.route('/api/results', methods=['GET'])
def api_results():
    """Résultats du vote - ADMIN SEULEMENT"""
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({
            'error': 'Accès refusé',
            'message': 'Cette fonctionnalité est réservée à l\'administration',
            'hint': 'Utilisez ?admin_secret=admin2026'
        }), 403
    
    try:
        # Récupérer toutes les candidates avec leurs votes
        candidates = Candidate.query.all()
        total_votes = Vote.query.count()
        
        results = []
        for candidate in candidates:
            # Compter les votes pour cette candidate
            candidate_votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            
            # Calculer le pourcentage
            percentage = (candidate_votes / total_votes * 100) if total_votes > 0 else 0
            
            results.append({
                'id': candidate.id,
                'nom': candidate.nom,
                'prenom': candidate.prenom,
                'nom_complet': candidate.nom_complet,
                'classe': candidate.classe,
                'description': candidate.description,
                'votes': candidate_votes,
                'votes_count': candidate.votes_count,
                'percentage': round(percentage, 2)
            })
        
        # Trier par nombre de votes (décroissant)
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        # Ajouter le rang
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return jsonify({
            'election': {
                'title': 'Élection 2026',
                'total_votes': total_votes,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'results': results,
            'total_votes': total_votes,
            'candidates_count': len(candidates)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Statistiques détaillées - ADMIN SEULEMENT"""
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        # Récupérer tous les votes
        votes = Vote.query.order_by(Vote.date_vote.desc()).limit(50).all()
        
        # Derniers votants
        recent_voters = []
        for vote in votes:
            candidate = Candidate.query.get(vote.candidate_id)
            recent_voters.append({
                'email': vote.professeur_email,
                'date_vote': vote.date_vote.isoformat() if vote.date_vote else None,
                'candidate_id': vote.candidate_id,
                'candidate_nom': candidate.nom_complet if candidate else 'N/A',
                'candidate_classe': candidate.classe if candidate else 'N/A'
            })
        
        # Votes par heure
        votes_by_hour = {}
        for vote in votes:
            if vote.date_vote:
                hour = vote.date_vote.strftime('%H:00')
                votes_by_hour[hour] = votes_by_hour.get(hour, 0) + 1
        
        total_votes = Vote.query.count()
        total_candidates = Candidate.query.count()
        
        return jsonify({
            'total_votes': total_votes,
            'total_candidates': total_candidates,
            'votes_last_hour': len([v for v in votes if v.date_vote and (datetime.now(timezone.utc) - v.date_vote).total_seconds() < 3600]),
            'votes_by_hour': votes_by_hour,
            'votants': recent_voters,
            'last_update': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-votes', methods=['POST'])
def reset_votes():
    """Réinitialise tous les votes - ADMIN SEULEMENT"""
    admin_secret = request.args.get('admin_secret') or request.json.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        # Compter les votes avant suppression
        votes_count = Vote.query.count()
        
        # Supprimer tous les votes
        deleted_count = Vote.query.delete()
        
        # Réinitialiser les compteurs des candidates
        candidates = Candidate.query.all()
        for candidate in candidates:
            candidate.votes_count = 0
        
        db.session.commit()
        
        print(f"✅ {deleted_count} votes réinitialisés par l'admin")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} votes ont été réinitialisés',
            'votes_deleted': deleted_count,
            'candidates_reset': len(candidates),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur réinitialisation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-user', methods=['POST'])
def reset_user_vote():
    """Réinitialise le vote d'un utilisateur spécifique"""
    admin_secret = request.args.get('admin_secret') or request.json.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        # Trouver et supprimer le vote de cet utilisateur
        vote = Vote.query.filter_by(professeur_email=email).first()
        
        if not vote:
            return jsonify({
                'success': False,
                'message': f'Aucun vote trouvé pour {email}'
            }), 404
        
        # Décrémenter le compteur de la candidate
        candidate = Candidate.query.get(vote.candidate_id)
        if candidate and candidate.votes_count > 0:
            candidate.votes_count -= 1
        
        # Supprimer le vote
        db.session.delete(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Vote de {email} réinitialisé',
            'email': email,
            'candidate_reset': candidate.nom_complet if candidate else 'N/A',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== PAGES DE FALLBACK ====================

def fallback_index():
    return '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Système de Vote 2026</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }
            .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; color: #333; }
            h1 { color: #4361ee; }
            .api-link { display: block; padding: 10px; background: #e9ecef; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🗳️ Système de Vote Scolaire 2026</h1>
            <p>Backend Flask fonctionnel. API disponibles :</p>
            <a href="/api/status" class="api-link">/api/status - Statut</a>
            <a href="/api/election" class="api-link">/api/election - Candidates</a>
            <a href="/admin-login" class="api-link">/admin-login - Administration</a>
            <a href="/api/results?admin_secret=admin2026" class="api-link">/api/results - Résultats (Admin)</a>
        </div>
    </body>
    </html>
    '''

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    # Initialiser la base de données
    if init_database():
        print("✅ Base de données initialisée avec succès")
    else:
        print("⚠️  Base de données non initialisée correctement")
    
    # Démarrer le serveur
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Serveur démarré sur le port {port}")
    print(f"🌐 URL publique: http://localhost:{port}")
    print(f"🔐 URL admin: http://localhost:{port}/admin-login")
    print(f"🔑 Mot de passe admin: admin2026")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)