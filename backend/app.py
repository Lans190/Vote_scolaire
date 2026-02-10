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

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')
    last_login = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    attempt_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    successful = db.Column(db.Boolean, default=False)

# ==================== FONCTIONS D'AUTHENTIFICATION ====================

def hash_password(password):
    """Hash un mot de passe avec SHA-256 + sel"""
    salt = app.config['SECRET_KEY'][:16]
    return hashlib.sha256((salt + password).encode()).hexdigest()

def check_brute_force(ip_address, username, max_attempts=5, lockout_time=15):
    """Vérifie si une IP ou un utilisateur a trop de tentatives échouées"""
    lockout_threshold = datetime.now(timezone.utc) - timedelta(minutes=lockout_time)
    
    # Compter les tentatives échouées récentes pour cette IP
    ip_attempts = LoginAttempt.query.filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.attempt_time >= lockout_threshold,
        LoginAttempt.successful == False
    ).count()
    
    # Compter les tentatives échouées récentes pour cet utilisateur
    user_attempts = LoginAttempt.query.filter(
        LoginAttempt.username == username,
        LoginAttempt.attempt_time >= lockout_threshold,
        LoginAttempt.successful == False
    ).count()
    
    return ip_attempts >= max_attempts or user_attempts >= max_attempts

def record_login_attempt(username, ip_address, successful):
    """Enregistre une tentative de connexion"""
    attempt = LoginAttempt(
        username=username,
        ip_address=ip_address,
        successful=successful
    )
    db.session.add(attempt)
    db.session.commit()

def login_required(f):
    """Décorateur pour protéger les routes admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({
                'error': 'Accès non autorisé',
                'message': 'Veuillez vous connecter en tant qu\'administrateur'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== INITIALISATION BASE DE DONNÉES ====================

def init_database():
    """Initialise la base de données avec des données de test"""
    with app.app_context():
        try:
            print("🔗 Création des tables...")
            db.create_all()
            print("✅ Tables créées")
            
            # Créer un compte admin par défaut
            if AdminUser.query.count() == 0:
                admin = AdminUser(
                    username='admin',
                    password_hash=hash_password('admin2026'),
                    role='super_admin'
                )
                db.session.add(admin)
                print("✅ Compte admin créé (username: admin, password: admin2026)")
            
            # Créer un compte viewer
            if not AdminUser.query.filter_by(username='viewer').first():
                viewer = AdminUser(
                    username='viewer',
                    password_hash=hash_password('viewer2026'),
                    role='viewer'
                )
                db.session.add(viewer)
                print("✅ Compte viewer créé (username: viewer, password: viewer2026)")
            
            # Créer une élection
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
            
            # Créer les candidates
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
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

# ==================== API D'AUTHENTIFICATION ====================

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    """API de connexion admin"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        ip_address = request.remote_addr
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Identifiants requis'
            }), 400
        
        # Vérifier les tentatives de force brute
        if check_brute_force(ip_address, username):
            record_login_attempt(username, ip_address, False)
            return jsonify({
                'success': False,
                'error': 'Trop de tentatives échouées. Veuillez réessayer dans 15 minutes.'
            }), 429
        
        # Vérifier l'utilisateur
        admin = AdminUser.query.filter_by(username=username, is_active=True).first()
        
        if not admin or admin.password_hash != hash_password(password):
            record_login_attempt(username, ip_address, False)
            return jsonify({
                'success': False,
                'error': 'Identifiants incorrects'
            }), 401
        
        # Mettre à jour la date de dernière connexion
        admin.last_login = datetime.now(timezone.utc)
        record_login_attempt(username, ip_address, True)
        db.session.commit()
        
        # Créer la session
        session['admin_logged_in'] = True
        session['admin_username'] = admin.username
        session['admin_role'] = admin.role
        session['admin_id'] = admin.id
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Connexion réussie',
            'user': {
                'username': admin.username,
                'role': admin.role,
                'last_login': admin.last_login.isoformat() if admin.last_login else None
            },
            'redirect': '/admin-dashboard'
        })
        
    except Exception as e:
        print(f"❌ Erreur login: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erreur serveur'
        }), 500

@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    """Déconnexion admin"""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Déconnexion réussie'
    })

@app.route('/api/admin/session', methods=['GET'])
def api_admin_session():
    """Vérifier la session admin"""
    if session.get('admin_logged_in'):
        return jsonify({
            'authenticated': True,
            'user': {
                'username': session.get('admin_username'),
                'role': session.get('admin_role')
            }
        })
    return jsonify({'authenticated': False})

# ==================== ROUTES PAGES HTML ====================

@app.route('/')
def serve_index():
    """Page principale de vote"""
    try:
        return send_from_directory(FRONTEND_PATH, 'index.html')
    except:
        return '''
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Système de Vote 2026</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                    color: white;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: rgba(255,255,255,0.95);
                    padding: 30px;
                    border-radius: 20px;
                    color: #333;
                }
                h1 {
                    color: #4361ee;
                    text-align: center;
                }
                .api-link {
                    display: block;
                    padding: 15px;
                    background: #e9ecef;
                    margin: 10px 0;
                    border-radius: 8px;
                    text-decoration: none;
                    color: #333;
                    transition: all 0.3s;
                }
                .api-link:hover {
                    background: #4361ee;
                    color: white;
                    transform: translateX(10px);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🗳️ Système de Vote Scolaire 2026</h1>
                <p>Backend Flask fonctionnel. API disponibles :</p>
                <a href="/api/status" class="api-link">/api/status - Statut du système</a>
                <a href="/api/election" class="api-link">/api/election - Liste des candidates</a>
                <a href="/admin-login" class="api-link">/admin-login - Connexion administration</a>
                <a href="/api/results?admin_secret=admin2026" class="api-link">/api/results - Résultats (Admin)</a>
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <h3>📊 Système en cours d'exécution</h3>
                    <p>Le serveur backend est opérationnel. Pour tester le système de vote :</p>
                    <ol>
                        <li>Accédez à l'interface admin via le lien ci-dessus</li>
                        <li>Utilisez le mot de passe : <strong>admin2026</strong></li>
                        <li>Explorez le tableau de bord administrateur</li>
                    </ol>
                </div>
            </div>
        </body>
        </html>
        '''

@app.route('/admin')
def admin_redirect():
    """Redirige vers la page de connexion admin"""
    return redirect('/admin-login')

@app.route('/admin-login')
def admin_login():
    """Page de connexion admin"""
    try:
        # Essaie de servir le fichier admin-login.html depuis le dossier front
        return send_from_directory(FRONTEND_PATH, 'admin-login.html')
    except Exception as e:
        print(f"⚠️ Impossible de charger admin-login.html: {str(e)}")
        # Fallback si le fichier n'existe pas
        return '''
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Connexion Admin - Élections 2026</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                
                .login-container {
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    width: 100%;
                    max-width: 500px;
                    overflow: hidden;
                }
                
                .login-header {
                    background: linear-gradient(135deg, #4361ee, #3a0ca3);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }
                
                .login-header i {
                    font-size: 3rem;
                    margin-bottom: 20px;
                }
                
                .login-header h1 {
                    font-size: 2rem;
                    margin-bottom: 10px;
                }
                
                .login-header p {
                    opacity: 0.9;
                }
                
                .login-form {
                    padding: 40px;
                }
                
                .input-group {
                    margin-bottom: 25px;
                    position: relative;
                }
                
                .input-group i {
                    position: absolute;
                    left: 20px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: #4361ee;
                    font-size: 1.2rem;
                }
                
                input[type="password"] {
                    width: 100%;
                    padding: 18px 20px 18px 55px;
                    border: 2px solid #e0e0e0;
                    border-radius: 12px;
                    font-size: 1rem;
                    outline: none;
                    transition: border-color 0.3s;
                }
                
                input[type="password"]:focus {
                    border-color: #4361ee;
                    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
                }
                
                .btn-login {
                    width: 100%;
                    padding: 18px;
                    background: linear-gradient(135deg, #4361ee, #3a0ca3);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 1.1rem;
                    font-weight: bold;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    transition: all 0.3s;
                }
                
                .btn-login:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 10px 25px rgba(67, 97, 238, 0.3);
                }
                
                .error-message {
                    background: rgba(255, 89, 94, 0.1);
                    border-left: 4px solid #ff595e;
                    color: #ff595e;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    display: none;
                    align-items: center;
                    gap: 10px;
                }
                
                .login-footer {
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9rem;
                    border-top: 1px solid #eee;
                }
                
                .back-link {
                    display: inline-block;
                    margin-top: 20px;
                    color: #4361ee;
                    text-decoration: none;
                    font-weight: 600;
                }
                
                .back-link:hover {
                    text-decoration: underline;
                }
                
                .info-box {
                    background: rgba(67, 97, 238, 0.1);
                    border-left: 4px solid #4361ee;
                    color: #4361ee;
                    padding: 12px;
                    border-radius: 8px;
                    margin: 15px 0;
                    text-align: center;
                    font-size: 0.9rem;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <div class="login-container">
                <div class="login-header">
                    <i class="fas fa-lock"></i>
                    <h1>Portail Administrateur</h1>
                    <p>Élections Délégués 2026 - Cours privés La Source de la Fontaine</p>
                </div>
                
                <div class="login-form">
                    <div class="info-box">
                        <i class="fas fa-info-circle"></i>
                        <span>Utilisez le mot de passe : <strong>admin2026</strong></span>
                    </div>
                    
                    <div class="input-group">
                        <i class="fas fa-key"></i>
                        <input type="password" 
                               id="adminPassword" 
                               placeholder="Code d'accès administrateur"
                               autocomplete="off"
                               autofocus>
                    </div>
                    
                    <div class="error-message" id="errorMessage">
                        <i class="fas fa-exclamation-circle"></i>
                        <span>Code incorrect</span>
                    </div>
                    
                    <button class="btn-login" onclick="loginAdmin()">
                        <i class="fas fa-sign-in-alt"></i>
                        <span>SE CONNECTER</span>
                    </button>
                    
                    <p style="text-align: center; margin-top: 25px; color: #666; font-size: 0.9rem;">
                        <i class="fas fa-info-circle"></i> Mot de passe : admin2026
                    </p>
                </div>
                
                <div class="login-footer">
                    <p>Système de vote électronique sécurisé - Version 2.0</p>
                    <a href="/" class="back-link">
                        <i class="fas fa-arrow-left"></i>
                        Retour à l'interface de vote
                    </a>
                </div>
            </div>
            
            <script>
                const ADMIN_SECRET = 'admin2026';
                
                function loginAdmin() {
                    const password = document.getElementById('adminPassword').value.trim();
                    const errorElement = document.getElementById('errorMessage');
                    
                    if (!password) {
                        showError('Veuillez entrer le code d\'accès');
                        return;
                    }
                    
                    if (password === ADMIN_SECRET) {
                        // Connexion réussie - rediriger vers la page admin
                        window.location.href = '/admin-dashboard';
                    } else {
                        showError('Code incorrect. Essayez : admin2026');
                    }
                }
                
                function showError(message) {
                    const errorElement = document.getElementById('errorMessage');
                    errorElement.querySelector('span').textContent = message;
                    errorElement.style.display = 'flex';
                    
                    // Animation
                    errorElement.style.opacity = '0';
                    errorElement.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        errorElement.style.transition = 'all 0.3s ease';
                        errorElement.style.opacity = '1';
                        errorElement.style.transform = 'translateY(0)';
                    }, 10);
                }
                
                // Entrée pour valider
                document.getElementById('adminPassword').addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        loginAdmin();
                    }
                });
                
                // Focus sur le champ mot de passe
                setTimeout(() => {
                    document.getElementById('adminPassword').focus();
                }, 100);
            </script>
        </body>
        </html>
        '''

@app.route('/admin-dashboard')
def admin_dashboard():
    """Tableau de bord admin"""
    try:
        # Essaie de servir le fichier admin-dashboard.html depuis le dossier front
        return send_from_directory(FRONTEND_PATH, 'admin-dashboard.html')
    except Exception as e:
        print(f"⚠️ Impossible de charger admin-dashboard.html: {str(e)}")
        # Fallback si le fichier n'existe pas
        return '''
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tableau de Bord Admin - Élections 2026</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: white;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                header {
                    background: linear-gradient(135deg, #4361ee, #3a0ca3);
                    color: white;
                    padding: 30px;
                    border-radius: 15px;
                    margin-bottom: 30px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                
                h1 {
                    margin: 0;
                    font-size: 2.5rem;
                    margin-bottom: 10px;
                }
                
                .subtitle {
                    opacity: 0.9;
                    margin-top: 5px;
                }
                
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                
                .stat-card {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 25px;
                    color: #333;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                    border-left: 5px solid #4361ee;
                    transition: transform 0.3s;
                }
                
                .stat-card:hover {
                    transform: translateY(-5px);
                }
                
                .stat-card h3 {
                    margin: 0 0 15px 0;
                    color: #4361ee;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                
                .stat-value {
                    font-size: 2.5rem;
                    font-weight: bold;
                    color: #3a0ca3;
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
                    font-weight: 600;
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
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    margin-top: 30px;
                    color: #333;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
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
                    background: #f8f9fa;
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
                    color: rgba(255,255,255,0.7);
                    font-size: 0.9rem;
                }
                
                .alert {
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    display: none;
                }
                
                .alert-success {
                    background: rgba(40, 167, 69, 0.2);
                    color: #155724;
                    border-left: 4px solid #28a745;
                }
                
                .alert-error {
                    background: rgba(220, 53, 69, 0.2);
                    color: #721c24;
                    border-left: 4px solid #dc3545;
                }
                
                .loading {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(67, 97, 238, 0.3);
                    border-radius: 50%;
                    border-top-color: #4361ee;
                    animation: spin 1s ease-in-out infinite;
                }
                
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <div class="container">
                <header>
                    <h1><i class="fas fa-tachometer-alt"></i> Tableau de Bord Admin</h1>
                    <p class="subtitle">Système de Vote Électronique - Élections 2026</p>
                    <p style="margin-top: 15px; font-size: 0.9rem; opacity: 0.8;">
                        <i class="fas fa-user-shield"></i> Connecté en tant qu'Administrateur
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
                        <p>Taux de participation</p>
                    </div>
                </div>
                
                <div class="actions">
                    <button class="btn btn-primary" onclick="loadResults()">
                        <i class="fas fa-sync-alt"></i>
                        Actualiser
                    </button>
                    
                    <button class="btn btn-secondary" onclick="viewFullResults()">
                        <i class="fas fa-chart-bar"></i>
                        Résultats Complets
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
                        <i class="fas fa-shield-alt"></i> Interface sécurisée - Accès réservé
                    </p>
                </footer>
            </div>
            
            <script>
                // Charger les données au démarrage
                window.onload = function() {
                    loadStats();
                };
                
                async function loadStats() {
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
                        showError('Impossible de charger les données');
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
                
                function loadResults() {
                    document.getElementById('resultsContainer').innerHTML = '<p><i class="fas fa-spinner loading"></i> Chargement...</p>';
                    loadStats();
                    showSuccess('Données actualisées');
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
                            loadStats();
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
                    loadStats();
                }, 30000);
            </script>
        </body>
        </html>
        '''
                        `);
                        
                    } catch (error) {
                        showError('Erreur lors du chargement des résultats');
                    }
                }
                
                async function viewStats() {
                    try {
                        const response = await fetch('/api/admin/stats', {
                            credentials: 'include'
                        });
                        const data = await response.json();
                        
                        if (data.error) {
                            showError(data.error);
                            return;
                        }
                        
                        const statsWindow = window.open('', '_blank');
                        statsWindow.document.write(`
                            <html>
                            <head>
                                <title>Statistiques - Élections 2026</title>
                            </head>
                            <body>
                                <h1>📈 Statistiques</h1>
                                <p>Total votes: ${data.total_votes}</p>
                                <p>Votes dernière heure: ${data.votes_last_hour}</p>
                                <p>Candidates: ${data.total_candidates}</p>
                            </body>
                            </html>
                        `);
                    } catch (error) {
                        showError('Erreur lors du chargement des statistiques');
                    }
                }
                
                function openResetModal() {
                    document.getElementById('resetModal').style.display = 'flex';
                }
                
                function closeResetModal() {
                    document.getElementById('resetModal').style.display = 'none';
                    document.getElementById('resetEmail').value = '';
                }
                
                async function resetUserVote() {
                    const email = document.getElementById('resetEmail').value.trim();
                    
                    if (!email || !email.includes('@')) {
                        showError('Veuillez entrer un email valide');
                        return;
                    }
                    
                    if (!confirm(`Confirmez-vous la réinitialisation du vote pour ${email} ?`)) {
                        return;
                    }
                    
                    try {
                        const response = await fetch('/api/admin/reset-user', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            credentials: 'include',
                            body: JSON.stringify({ email: email })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            showSuccess(`Vote de ${email} réinitialisé avec succès`);
                            closeResetModal();
                            await loadStats();
                        } else {
                            showError(data.error || 'Erreur lors de la réinitialisation');
                        }
                        
                    } catch (error) {
                        showError('Erreur de connexion au serveur');
                    }
                }
                
                function openFullResetModal() {
                    document.getElementById('fullResetModal').style.display = 'flex';
                    document.getElementById('confirmText').addEventListener('input', function() {
                        const confirmBtn = document.getElementById('resetAllBtn');
                        confirmBtn.disabled = this.value.toUpperCase() !== 'CONFIRMER';
                    });
                }
                
                function closeFullResetModal() {
                    document.getElementById('fullResetModal').style.display = 'none';
                    document.getElementById('confirmText').value = '';
                    document.getElementById('resetAllBtn').disabled = true;
                }
                
                async function resetAllVotes() {
                    if (!confirm('⚠️ Êtes-vous ABSOLUMENT SÛR de vouloir réinitialiser TOUS les votes ?')) {
                        return;
                    }
                    
                    try {
                        const response = await fetch('/api/admin/reset-votes', {
                            method: 'POST',
                            credentials: 'include'
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            showSuccess(`${data.votes_deleted} votes ont été réinitialisés`);
                            closeFullResetModal();
                            await loadStats();
                        } else {
                            showError(data.error || 'Erreur lors de la réinitialisation');
                        }
                        
                    } catch (error) {
                        showError('Erreur de connexion au serveur');
                    }
                }
                
                async function logout() {
                    try {
                        await fetch('/api/admin/logout', {
                            method: 'POST',
                            credentials: 'include'
                        });
                    } catch (error) {
                        console.error('Logout error:', error);
                    }
                    window.location.href = '/admin-login';
                }
                
                function showSuccess(message) {
                    const alert = document.getElementById('successAlert');
                    document.getElementById('successMessage').textContent = message;
                    alert.style.display = 'block';
                    
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 5000);
                }
                
                function showError(message) {
                    const alert = document.getElementById('errorAlert');
                    document.getElementById('errorMessage').textContent = message;
                    alert.style.display = 'block';
                    
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 5000);
                }
                
                window.onclick = function(event) {
                    if (event.target.id === 'resetModal' || event.target.id === 'fullResetModal') {
                        event.target.style.display = 'none';
                    }
                };
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
        
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        
        if existing_vote:
            return jsonify({
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None,
                'message': 'Vous avez déjà voté pour cette élection'
            })
        
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
        
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        if existing_vote:
            return jsonify({
                'error': 'Vous avez déjà voté',
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None
            }), 400
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate non trouvée'}), 404
        
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
        
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id,
            professeur_email=email,
            ip_address=request.remote_addr
        )
        
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

# ==================== API ADMIN PROTÉGÉE ====================

@app.route('/api/admin/results', methods=['GET'])
@login_required
def api_admin_results():
    """Résultats du vote - ADMIN SEULEMENT"""
    try:
        candidates = Candidate.query.all()
        total_votes = Vote.query.count()
        
        results = []
        for candidate in candidates:
            candidate_votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            
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
        
        results.sort(key=lambda x: x['votes'], reverse=True)
        
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
            'candidates_count': len(candidates),
            'viewed_by': session.get('admin_username'),
            'role': session.get('admin_role')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@login_required
def api_admin_stats():
    """Statistiques détaillées - ADMIN SEULEMENT"""
    try:
        votes = Vote.query.order_by(Vote.date_vote.desc()).limit(50).all()
        
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
        
        total_votes = Vote.query.count()
        total_candidates = Candidate.query.count()
        
        return jsonify({
            'total_votes': total_votes,
            'total_candidates': total_candidates,
            'votes_last_hour': len([v for v in votes if v.date_vote and (datetime.now(timezone.utc) - v.date_vote).total_seconds() < 3600]),
            'votants': recent_voters,
            'last_update': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-votes', methods=['POST'])
@login_required
def api_admin_reset_votes():
    """Réinitialise tous les votes - SUPER ADMIN SEULEMENT"""
    try:
        if session.get('admin_role') != 'super_admin':
            return jsonify({
                'success': False,
                'error': 'Permission refusée. Réservé aux super administrateurs.'
            }), 403
        
        deleted_count = Vote.query.delete()
        
        candidates = Candidate.query.all()
        for candidate in candidates:
            candidate.votes_count = 0
        
        db.session.commit()
        
        print(f"✅ {deleted_count} votes réinitialisés par {session.get('admin_username')}")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} votes ont été réinitialisés',
            'votes_deleted': deleted_count,
            'candidates_reset': len(candidates),
            'action_by': session.get('admin_username'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur réinitialisation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-user', methods=['POST'])
@login_required
def api_admin_reset_user_vote():
    """Réinitialise le vote d'un utilisateur spécifique"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        vote = Vote.query.filter_by(professeur_email=email).first()
        
        if not vote:
            return jsonify({
                'success': False,
                'message': f'Aucun vote trouvé pour {email}'
            }), 404
        
        candidate = Candidate.query.get(vote.candidate_id)
        if candidate and candidate.votes_count > 0:
            candidate.votes_count -= 1
        
        db.session.delete(vote)
        db.session.commit()
        
        print(f"✅ Vote de {email} réinitialisé par {session.get('admin_username')}")
        
        return jsonify({
            'success': True,
            'message': f'Vote de {email} réinitialisé',
            'email': email,
            'candidate_reset': candidate.nom_complet if candidate else 'N/A',
            'action_by': session.get('admin_username'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/change-password', methods=['POST'])
@login_required
def api_admin_change_password():
    """Changer le mot de passe admin"""
    try:
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Tous les champs sont requis'}), 400
        
        admin = AdminUser.query.get(session.get('admin_id'))
        if not admin:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        if admin.password_hash != hash_password(current_password):
            return jsonify({'error': 'Mot de passe actuel incorrect'}), 401
        
        admin.password_hash = hash_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mot de passe changé avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    # Initialiser la base de données
    if init_database():
        print("✅ Base de données initialisée avec succès")
    else:
        print("⚠️  Base de données non initialisée correctement")
    
    # Démarrer le serveur
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Serveur démarré sur http://localhost:{port}")
    print(f"🔐 URL admin: http://localhost:{port}/admin-login")
    print("=" * 80)
    print("🔑 Comptes disponibles:")
    print("   - admin / admin2026 (super_admin)")
    print("   - viewer / viewer2026 (viewer)")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)