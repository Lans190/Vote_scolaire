from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins - ADAPTÉ POUR RENDER
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_DIR, '..', 'front')

print(f"📁 Chemin frontend: {FRONTEND_PATH}")
print(f"📁 Existe: {os.path.exists(FRONTEND_PATH)}")

app = Flask(__name__, static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None)
CORS(app)

# ==================== CONFIGURATION BASE DE DONNÉES ====================

# URL FIXE POUR RENDER - À UTILISER TEMPORAIREMENT
DATABASE_URL_FIXE = "postgresql://vote_user:sVZxXHKa3RfuRfS2SkcSJUuIJ8C0KMpF@dpg-d64t7q24d50c73eo9nn0-a.render.com:5432/vote_vq45"

print(f"🔗 URL de base de données fixe: {DATABASE_URL_FIXE[:60]}...")

# Utiliser l'URL fixe par défaut
database_url = os.getenv('DATABASE_URL', DATABASE_URL_FIXE)

# Correction automatique si nécessaire
if database_url and '-a' in database_url and 'render.com' not in database_url:
    print("⚠️  Correction automatique du nom d'hôte...")
    database_url = database_url.replace('@dpg-d64t7q24d50c73eo9nn0-a', '@dpg-d64t7q24d50c73eo9nn0-a.render.com:5432')
    print(f"🔧 URL corrigée: {database_url[:70]}...")

# Configuration Flask
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2026_vote_scolaire')

db = SQLAlchemy(app)

# ==================== MODÈLES (SIMPLIFIÉS) ====================

class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200))
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    classe = db.Column(db.String(50))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    votes_count = db.Column(db.Integer, default=0)

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'))
    professeur_email = db.Column(db.String(150))
    date_vote = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ==================== ROUTES ====================

@app.route('/')
def index():
    if os.path.exists(FRONTEND_PATH):
        return send_from_directory(FRONTEND_PATH, 'index.html')
    return '''
    <html>
    <head><title>Vote Scolaire 2026</title></head>
    <body>
        <h1>🗳️ Système de Vote Scolaire 2026</h1>
        <p>Backend opérationnel</p>
        <p><a href="/api/status">Statut API</a></p>
        <p><a href="/api/election">Élection</a></p>
    </body>
    </html>
    '''

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'database': 'configured' if database_url else 'not_configured',
        'year': 2026,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/election')
def get_election():
    try:
        # Test simple sans DB
        return jsonify({
            'titre': 'Élection des Délégués - 2026',
            'date_debut': '2026-02-08T00:00:00Z',
            'date_fin': '2026-02-10T23:59:59Z',
            'statut': 'active',
            'candidates': [
                {'id': 1, 'nom': 'Martin', 'prenom': 'Léa', 'classe': '6ème'},
                {'id': 2, 'nom': 'Dubois', 'prenom': 'Thomas', 'classe': '5ème'},
                {'id': 3, 'nom': 'Bernard', 'prenom': 'Emma', 'classe': '4ème'}
            ]
        })
    except:
        return jsonify({'error': 'Base de données indisponible'}), 503

# ==================== INITIALISATION ====================

def init_database_safe():
    """Initialisation sécurisée de la base de données"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ Tables créées avec succès")
            return True
    except Exception as e:
        print(f"⚠️  Base de données non disponible: {str(e)[:100]}")
        print("💡 Le frontend fonctionnera mais sans données persistantes")
        return False

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 SYSTÈME DE VOTE SCOLAIRE 2026")
    print("=" * 80)
    
    # Initialisation sécurisée
    init_database_safe()
    
    port = int(os.getenv('PORT', 10000))
    print(f"🌐 Port: {port}")
    print(f"🔗 Base de données: {'Connectée' if 'render.com' in database_url else 'Configuration requise'}")
    print("=" * 80)
    
    app.run(debug=False, port=port, host='0.0.0.0')