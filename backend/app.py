"""
SYSTÈME DE VOTE SCOLAIRE 2026 - Backend simplifié
Python 3.11 compatible avec Render
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🚀 DÉMARRAGE DU SYSTÈME DE VOTE SCOLAIRE 2026")
print(f"🐍 Python: {sys.version}")
print("=" * 60)

# Application Flask
app = Flask(__name__)
CORS(app)

# Configuration de la base de données
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL non définie!")
    # URL de secours pour développement
    DATABASE_URL = "postgresql://vote_user:sVZxXHKa3RfuRfS2SkcSJUuIJ8C0KMpF@dpg-d64t7q24d50c73eo9nn0-a:5432/vote_vq45"

# Correction pour psycopg2
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

db = SQLAlchemy(app)
logger.info(f"✅ SQLAlchemy initialisé avec: {DATABASE_URL[:50]}...")

# ==================== MODÈLES ====================

class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    classe = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    votes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'))
    professeur_email = db.Column(db.String(150), nullable=False)
    date_vote = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ==================== ROUTES API ====================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check pour Render"""
    return jsonify({
        'status': 'healthy',
        'service': 'vote-scolaire',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@app.route('/api/status', methods=['GET'])
def status():
    """Statut du système"""
    try:
        db_status = 'connected'
        try:
            db.session.execute('SELECT 1')
        except:
            db_status = 'disconnected'
        
        return jsonify({
            'status': 'online',
            'database': db_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '2026.1.0'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/election', methods=['GET'])
def get_election():
    """Récupère l'élection active"""
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        
        return jsonify({
            'election': {
                'id': election.id,
                'titre': election.titre,
                'description': election.description,
                'date_debut': election.date_debut.isoformat() if election.date_debut else None,
                'date_fin': election.date_fin.isoformat() if election.date_fin else None,
                'statut': election.statut
            },
            'candidates': [
                {
                    'id': c.id,
                    'nom': c.nom,
                    'prenom': c.prenom,
                    'nom_complet': f"{c.prenom} {c.nom}",
                    'classe': c.classe,
                    'description': c.description,
                    'votes_count': c.votes_count
                }
                for c in candidates
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def vote():
    """Enregistre un vote"""
    try:
        data = request.json
        email = data.get('professeur_email')
        candidate_id = data.get('candidate_id')
        
        if not email or not candidate_id:
            return jsonify({'error': 'Email et candidat requis'}), 400
        
        # Vérifier si l'email a déjà voté
        existing_vote = Vote.query.filter_by(professeur_email=email).first()
        if existing_vote:
            return jsonify({'error': 'Vous avez déjà voté'}), 400
        
        # Enregistrer le vote
        vote = Vote(
            professeur_email=email,
            candidate_id=candidate_id,
            election_id=1  # ID de l'élection active
        )
        
        # Mettre à jour le compteur du candidat
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            candidate.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote enregistré',
            'vote_id': vote.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def results():
    """Résultats du vote"""
    try:
        candidates = Candidate.query.order_by(Candidate.votes_count.desc()).all()
        total_votes = sum(c.votes_count for c in candidates)
        
        return jsonify({
            'candidates': [
                {
                    'id': c.id,
                    'nom_complet': f"{c.prenom} {c.nom}",
                    'classe': c.classe,
                    'votes': c.votes_count,
                    'percentage': round((c.votes_count / total_votes * 100), 2) if total_votes > 0 else 0
                }
                for c in candidates
            ],
            'total_votes': total_votes,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== INITIALISATION ====================

def init_database():
    """Initialise la base de données"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("✅ Tables créées")
            
            # Créer une élection si elle n'existe pas
            election = Election.query.first()
            if not election:
                election = Election(
                    titre="Élection des Délégués 2026",
                    description="Vote des professeurs pour les délégués élèves",
                    date_debut=datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc),
                    date_fin=datetime(2026, 2, 10, 23, 59, 59, tzinfo=timezone.utc),
                    statut='active'
                )
                db.session.add(election)
                db.session.commit()
                logger.info("✅ Élection créée")
            
            # Créer des candidats s'ils n'existent pas
            if Candidate.query.count() == 0:
                candidates = [
                    Candidate(nom='Martin', prenom='Léa', classe='6ème', election_id=election.id,
                             description='Sérieuse et à l\'écoute'),
                    Candidate(nom='Dubois', prenom='Thomas', classe='5ème', election_id=election.id,
                             description='Dynamique et créatif'),
                    Candidate(nom='Bernard', prenom='Emma', classe='4ème', election_id=election.id,
                             description='Organisée et impliquée'),
                    Candidate(nom='Petit', prenom='Lucas', classe='3ème', election_id=election.id,
                             description='Responsable et expérimenté'),
                    Candidate(nom='Durand', prenom='Chloé', classe='2nde', election_id=election.id,
                             description='Mature et motivée')
                ]
                db.session.add_all(candidates)
                db.session.commit()
                logger.info(f"✅ {len(candidates)} candidats créés")
                
    except Exception as e:
        logger.error(f"❌ Erreur d'initialisation: {e}")

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    # Initialiser la DB
    init_database()
    
    # Démarrer le serveur
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🌐 Démarrage sur le port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)