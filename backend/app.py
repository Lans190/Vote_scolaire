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

# ==================== CONFIGURATION BASE DE DONNÉES AVEC SSL ====================

# URL CORRECTE POUR RENDER FRANKFURT AVEC SSL
DATABASE_URL_CORRECTE = "postgresql://vote_user:sVZxXHKa3RfuRfS2SkcSJUuIJ8C0KMpF@dpg-d64t7q24d50c73e0n9nn0-a.frankfurt-postgres.render.com:5432/vote_vq45?sslmode=require"

print(f"🔗 URL avec SSL configurée: {DATABASE_URL_CORRECTE[:70]}...")

# Obtenir l'URL de l'environnement ou utiliser l'URL corrigée
database_url = os.getenv('DATABASE_URL', DATABASE_URL_CORRECTE)

# S'assurer que le mode SSL est activé
if '?sslmode=' not in database_url:
    database_url += '?sslmode=require'
    print(f"✅ SSL mode ajouté à l'URL")

# Configuration Flask avec options SQLAlchemy pour SSL
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {
        'sslmode': 'require'
    }
}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2026_vote_scolaire')

db = SQLAlchemy(app)

# ==================== MODÈLES SIMPLIFIÉS ====================

class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200))
    date_debut = db.Column(db.DateTime)
    date_fin = db.Column(db.DateTime)
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
    date_vote = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== INITIALISATION SÉCURISÉE ====================

def init_database_safe():
    """Initialisation sécurisée avec gestion d'erreurs"""
    try:
        print("🔗 Connexion à la base de données...")
        with app.app_context():
            # Test de connexion simple
            db.session.execute('SELECT 1')
            print("✅ Connexion SSL réussie")
            
            # Créer les tables
            db.create_all()
            print("✅ Tables créées/vérifiées")
            
            # Créer une élection si elle n'existe pas
            election = Election.query.first()
            if not election:
                election = Election(
                    titre="Élection des Délégués Élèves - Février 2026",
                    date_debut=datetime(2026, 2, 8, 0, 0, 0),
                    date_fin=datetime(2026, 2, 10, 23, 59, 59),
                    statut='active'
                )
                db.session.add(election)
                db.session.commit()
                print("✅ Élection 2026 créée")
            
            # Créer des candidats si nécessaire
            if Candidate.query.count() == 0:
                candidates = [
                    Candidate(nom="Martin", prenom="Léa", classe="6ème", election_id=1),
                    Candidate(nom="Dubois", prenom="Thomas", classe="5ème", election_id=1),
                    Candidate(nom="Bernard", prenom="Emma", classe="4ème", election_id=1),
                    Candidate(nom="Petit", prenom="Lucas", classe="3ème", election_id=1),
                    Candidate(nom="Durand", prenom="Chloé", classe="2nde", election_id=1)
                ]
                db.session.add_all(candidates)
                db.session.commit()
                print(f"✅ {len(candidates)} candidats créés")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("💡 Mode démo activé - Données en mémoire")
        return False

# ==================== ROUTES API SIMPLIFIÉES ====================

@app.route('/')
def index():
    if os.path.exists(FRONTEND_PATH):
        return send_from_directory(FRONTEND_PATH, 'index.html')
    return '''
    <html>
    <head><title>Vote Scolaire 2026</title></head>
    <body>
        <h1>🗳️ Système de Vote Scolaire 2026</h1>
        <p>✅ Backend opérationnel</p>
        <p><a href="/api/status">Statut API</a></p>
    </body>
    </html>
    '''

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'database': 'PostgreSQL (Frankfurt) avec SSL',
        'year': 2026,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/election')
def api_election():
    try:
        election = Election.query.first()
        candidates = Candidate.query.all()
        
        return jsonify({
            'election': {
                'titre': election.titre if election else "Élection 2026",
                'date_debut': election.date_debut.isoformat() if election else "2026-02-08T00:00:00",
                'date_fin': election.date_fin.isoformat() if election else "2026-02-10T23:59:59",
                'statut': election.statut if election else "active"
            },
            'candidates': [
                {
                    'id': c.id,
                    'nom': c.nom,
                    'prenom': c.prenom,
                    'classe': c.classe,
                    'votes_count': c.votes_count
                } for c in candidates
            ] if candidates else []
        })
    except Exception as e:
        # Mode démo si la DB échoue
        return jsonify({
            'election': {
                'titre': 'Élection des Délégués 2026 (Mode démo)',
                'date_debut': '2026-02-08T00:00:00',
                'date_fin': '2026-02-10T23:59:59',
                'statut': 'active'
            },
            'candidates': [
                {'id': 1, 'nom': 'Martin', 'prenom': 'Léa', 'classe': '6ème', 'votes_count': 0},
                {'id': 2, 'nom': 'Dubois', 'prenom': 'Thomas', 'classe': '5ème', 'votes_count': 0},
                {'id': 3, 'nom': 'Bernard', 'prenom': 'Emma', 'classe': '4ème', 'votes_count': 0}
            ]
        })

@app.route('/api/vote', methods=['POST'])
def api_vote():
    try:
        data = request.json
        email = data.get('email')
        candidate_id = data.get('candidate_id')
        
        if not email or '@' not in email:
            return jsonify({'error': 'Email invalide'}), 400
        
        # Enregistrer le vote
        vote = Vote(
            professeur_email=email,
            candidate_id=candidate_id,
            election_id=1
        )
        
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            candidate.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote enregistré'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 SYSTÈME DE VOTE SCOLAIRE 2026")
    print("=" * 80)
    
    # Initialisation sécurisée
    db_ok = init_database_safe()
    
    if db_ok:
        print("✅ Base de données connectée avec SSL")
    else:
        print("⚠️  Mode démo - Connexion SSL échouée")
    
    port = int(os.getenv('PORT', 10000))
    print(f"🌐 Port: {port}")
    print(f"🔗 URL publique: https://vote-scolaire.onrender.com")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)