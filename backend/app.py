from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ==================== CONFIGURATION ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_PATH = os.path.join(PROJECT_ROOT, 'front')

print("=" * 80)
print("🚀 SYSTÈME DE VOTE SCOLAIRE 2026 - BACKEND FLASK")
print("=" * 80)

# Créer le dossier front s'il n'existe pas
if not os.path.exists(FRONTEND_PATH):
    os.makedirs(FRONTEND_PATH, exist_ok=True)

app = Flask(__name__, 
            static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None,
            static_url_path='')

CORS(app)

# ==================== BASE DE DONNÉES ====================

SQLITE_DB_PATH = os.path.join(BASE_DIR, 'votes.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{SQLITE_DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vote_2026_secret_key')

db = SQLAlchemy(app)

# ==================== MODÈLES ====================

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

# ==================== ROUTES STATIQUES ====================

@app.route('/')
def serve_index():
    """Sert index.html"""
    try:
        return send_from_directory(FRONTEND_PATH, 'index.html')
    except:
        return fallback_index()

@app.route('/admin')
def serve_admin():
    """Sert admin.html"""
    try:
        return send_from_directory(FRONTEND_PATH, 'admin.html')
    except:
        return fallback_admin()

@app.route('/<path:path>')
def serve_static(path):
    """Sert les fichiers statiques"""
    try:
        return send_from_directory(FRONTEND_PATH, path)
    except:
        return jsonify({'error': 'Fichier non trouvé'}), 404

# ==================== API ====================

@app.route('/api/status', methods=['GET'])
def api_status():
    """Statut du système"""
    try:
        election = Election.query.first()
        votes_count = Vote.query.count()
        candidates_count = Candidate.query.count()
        
        now = datetime.now(timezone.utc)
        status = "active"
        temps_restant = "4j 12h"
        
        return jsonify({
            'system': {
                'status': 'online',
                'database': 'SQLite',
                'year': 2026,
                'ecole': 'Cours privés La Source de la Fontaine',
                'timestamp': now.isoformat()
            },
            'election': {
                'status': status,
                'temps_restant': temps_restant,
                'can_vote': True
            },
            'statistics': {
                'votes': votes_count,
                'candidates': candidates_count,
                'participation_rate': round((votes_count / 50) * 100, 1)  # 50 professeurs estimés
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/election', methods=['GET'])
def api_election():
    """Données de l'élection avec candidates"""
    try:
        # Données factices pour les candidates
        candidates = [
            {
                'id': 1,
                'prenom': 'Binta',
                'nom': 'Diallo',
                'classe': '3ème',
                'description': 'Candidate sérieuse et impliquée'
            },
            {
                'id': 2,
                'prenom': 'Maguette',
                'nom': 'Ngom',
                'classe': '6ème',
                'description': 'Dynamique et à l\'écoute'
            },
            {
                'id': 3,
                'prenom': 'Eléna Nafissatou',
                'nom': 'Gomis',
                'classe': '5ème',
                'description': 'Responsable et organisée'
            },
            {
                'id': 4,
                'prenom': 'Diasse',
                'nom': 'Séne',
                'classe': '2nde',
                'description': 'Créative et motivante'
            },
            {
                'id': 5,
                'prenom': 'Ndeye Fatou',
                'nom': 'Ndong',
                'classe': '4ème',
                'description': 'Sait communiquer et représenter'
            }
        ]
        
        return jsonify({
            'status': 'active',
            'title': 'Élection des Délégués Élèves 2026',
            'candidates': candidates
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
                'message': 'Vous avez déjà voté'
            })
        
        # Sinon, peut voter
        return jsonify({
            'has_voted': False,
            'can_vote': True,
            'message': 'Vous pouvez voter'
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
        
        # Vérifier si déjà voté
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        if existing_vote:
            return jsonify({
                'error': 'Vous avez déjà voté',
                'has_voted': True
            }), 400
        
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
        
        db.session.add(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote enregistré',
            'confirmation_id': f'VOTE-{vote.id:06d}',
            'timestamp': vote.date_vote.isoformat() if vote.date_vote else datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def api_results():
    """Résultats (admin)"""
    admin_secret = request.args.get('admin_secret')
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        votes = Vote.query.all()
        candidates = Candidate.query.all()
        
        results = []
        for candidate in candidates:
            candidate_votes = Vote.query.filter_by(candidate_id=candidate.id).count()
            results.append({
                'id': candidate.id,
                'nom_complet': f"{candidate.prenom} {candidate.nom}",
                'classe': candidate.classe,
                'votes': candidate_votes
            })
        
        # Trier par votes
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        return jsonify({
            'total_votes': len(votes),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Statistiques (admin)"""
    admin_secret = request.args.get('admin_secret')
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    try:
        votes = Vote.query.all()
        
        # Group by hour for chart
        votes_by_hour = {}
        for vote in votes:
            hour = vote.date_vote.strftime('%H:00') if vote.date_vote else '00:00'
            votes_by_hour[hour] = votes_by_hour.get(hour, 0) + 1
        
        return jsonify({
            'total_votes': len(votes),
            'votes_by_hour': votes_by_hour,
            'last_votes': [
                {
                    'email': v.professeur_email,
                    'time': v.date_vote.isoformat() if v.date_vote else None
                }
                for v in votes[-10:]  # 10 derniers votes
            ]
        })
    except Exception as e:
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
            <a href="/admin" class="api-link">/admin - Administration</a>
        </div>
    </body>
    </html>
    '''

def fallback_admin():
    return '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin - Vote 2026</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            h1 { color: #4361ee; }
        </style>
    </head>
    <body>
        <h1>🔐 Administration</h1>
        <p>Pour accéder aux résultats, utilisez :</p>
        <p><strong>/api/results?admin_secret=admin2026</strong></p>
        <p><strong>/api/stats?admin_secret=admin2026</strong></p>
    </body>
    </html>
    '''

# ==================== INITIALISATION ====================

def init_db():
    """Initialise la base de données"""
    with app.app_context():
        db.create_all()
        
        # Créer des données de test si nécessaire
        if Election.query.count() == 0:
            election = Election(
                titre="Élection des Délégués 2026",
                date_debut=datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc),
                date_fin=datetime(2026, 2, 13, 23, 59, 59, tzinfo=timezone.utc),
                statut='active'
            )
            db.session.add(election)
            db.session.commit()
            
            candidates_data = [
                ('Diallo', 'Binta', '3ème', 'Candidate sérieuse et impliquée'),
                ('Ngom', 'Maguette', '6ème', 'Dynamique et à l\'écoute'),
                ('Gomis', 'Eléna Nafissatou', '5ème', 'Responsable et organisée'),
                ('Séne', 'Diasse', '2nde', 'Créative et motivante'),
                ('Ndong', 'Ndeye Fatou', '4ème', 'Sait communiquer et représenter')
            ]
            
            for nom, prenom, classe, desc in candidates_data:
                candidate = Candidate(
                    nom=nom,
                    prenom=prenom,
                    classe=classe,
                    description=desc,
                    election_id=election.id
                )
                db.session.add(candidate)
            
            db.session.commit()
            print("✅ Base de données initialisée")

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Serveur démarré sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)