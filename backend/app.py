from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import sys

# Charger les variables d'environnement
load_dotenv()

print(f"🐍 Python version: {sys.version}")

# ==================== CONFIGURATION ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_DIR, '..', 'front')

app = Flask(__name__, static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None)
CORS(app)

# ==================== CONFIGURATION POSTGRESQL ====================

database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/vote')

# Transformation pour psycopg v3 (compatible Python 3.13)
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    # Correction pour Render (ajouter le port si manquant)
    if '-a/' in database_url and ':5432' not in database_url:
        database_url = database_url.replace('-a/', '-a:5432/')

print(f"🔗 URL DB: {database_url[:70]}...")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vote-scolaire-2026')  # Optionnel

db = SQLAlchemy(app)
print("✅ SQLAlchemy initialisé avec psycopg v3")

# ==================== MODÈLES ====================

class Election(db.Model):
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    candidates = db.relationship('Candidate', backref='election_ref', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='election_ref', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'titre': self.titre,
            'description': self.description,
            'date_debut': self.date_debut.isoformat() if self.date_debut else None,
            'date_fin': self.date_fin.isoformat() if self.date_fin else None,
            'statut': self.statut,
            'candidates_count': len(self.candidates),
            'votes_count': len(self.votes),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'temps_restant': self.get_temps_restant()
        }
    
    def get_temps_restant(self):
        """Calcule le temps restant avant la fin du vote"""
        if not self.date_fin:
            return None
        
        now = datetime.now(timezone.utc)
        fin = self.date_fin.astimezone(timezone.utc) if self.date_fin.tzinfo else self.date_fin.replace(tzinfo=timezone.utc)
        
        if now < fin:
            diff = fin - now
            jours = diff.days
            heures = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            return f"{jours}j {heures}h {minutes}m"
        else:
            return "Terminé"

class Candidate(db.Model):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    classe = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(500), default='')
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    votes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    votes = db.relationship('Vote', backref='candidate_ref', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'prenom': self.prenom,
            'nom_complet': f"{self.prenom} {self.nom}",
            'classe': self.classe,
            'description': self.description,
            'photo_url': self.photo_url,
            'election_id': self.election_id,
            'votes_count': self.votes_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    professeur_email = db.Column(db.String(150), nullable=False)
    date_vote = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        db.UniqueConstraint('election_id', 'professeur_email', name='unique_vote_per_election'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'election_id': self.election_id,
            'candidate_id': self.candidate_id,
            'professeur_email': self.professeur_email,
            'date_vote': self.date_vote.isoformat() if self.date_vote else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Page d'accueil - Redirige vers le frontend"""
    try:
        return send_from_directory(FRONTEND_PATH, 'index.html')
    except:
        return jsonify({
            'message': 'API Vote Scolaire 2026', 
            'status': 'online',
            'api_endpoints': {
                'status': '/api/status',
                'election': '/api/election',
                'results': '/api/results',
                'stats': '/api/stats'
            }
        })

@app.route('/<path:path>')
def serve_frontend(path):
    """Sert les fichiers statiques du frontend"""
    return send_from_directory(FRONTEND_PATH, path)

# ==================== INITIALISATION ====================

def ensure_timezone(dt):
    """Assure qu'une datetime a un timezone UTC"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def init_database():
    """Initialise la base de données avec les dates CORRECTES 2026"""
    with app.app_context():
        try:
            print("🔗 Création des tables...")
            db.create_all()
            print("✅ Tables créées avec succès")
            
            election = Election.query.filter_by(statut='active').first()
            
            if not election:
                # DATES EXACTES POUR 2026
                date_debut = datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
                date_fin = datetime(2026, 2, 10, 23, 59, 59, tzinfo=timezone.utc)
                
                election = Election(
                    titre="Élection des Délégués Élèves - Février 2026",
                    description="Vote des professeurs pour élire les délégués élèves de chaque classe (6ème à 2nde). Période de vote : 8 au 10 février 2026.",
                    date_debut=date_debut,
                    date_fin=date_fin,
                    statut='active'
                )
                db.session.add(election)
                db.session.commit()
                print("✅ Élection 2026 créée")
                print(f"📅 Date de début: {date_debut}")
                print(f"📅 Date de fin: {date_fin}")
            
            candidates_count = Candidate.query.filter_by(election_id=election.id).count()
            
            if candidates_count == 0:
                candidates_data = [
                    {'nom': 'Martin', 'prenom': 'Léa', 'classe': '6ème',
                     'description': 'Sérieuse, à l\'écoute, toujours prête à aider ses camarades.'},
                    {'nom': 'Dubois', 'prenom': 'Thomas', 'classe': '5ème',
                     'description': 'Dynamique, créatif, bon communicateur.'},
                    {'nom': 'Bernard', 'prenom': 'Emma', 'classe': '4ème',
                     'description': 'Organisée, impliquée dans la vie scolaire.'},
                    {'nom': 'Petit', 'prenom': 'Lucas', 'classe': '3ème',
                     'description': 'Responsable, expérimenté.'},
                    {'nom': 'Durand', 'prenom': 'Chloé', 'classe': '2nde',
                     'description': 'Mature, motivée.'}
                ]
                
                for cand_data in candidates_data:
                    candidate = Candidate(
                        nom=cand_data['nom'],
                        prenom=cand_data['prenom'],
                        classe=cand_data['classe'],
                        description=cand_data['description'],
                        election_id=election.id,
                        photo_url=f"https://ui-avatars.com/api/?name={cand_data['prenom']}+{cand_data['nom']}&background=4361ee&color=fff"
                    )
                    db.session.add(candidate)
                
                db.session.commit()
                print(f"✅ {len(candidates_data)} candidates créées")
            
            total_votes = Vote.query.count()
            print(f"📊 Total votes enregistrés : {total_votes}")
            
            # Afficher le statut
            now = datetime.now(timezone.utc)
            if election.date_debut:
                debut = ensure_timezone(election.date_debut)
                fin = ensure_timezone(election.date_fin)
                
                if now < debut:
                    print(f"⏳ L'élection débutera le: {debut.strftime('%d/%m/%Y %H:%M')}")
                elif debut <= now <= fin:
                    print(f"✅ L'élection est en cours (fin: {fin.strftime('%d/%m/%Y %H:%M')})")
                else:
                    print(f"⏰ L'élection est terminée (depuis: {fin.strftime('%d/%m/%Y %H:%M')})")
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()

# ==================== API ROUTES ====================

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Retourne le statut complet du système"""
    try:
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            candidates_count = Candidate.query.count()
            votes_count = Vote.query.count()
            
            now = datetime.now(timezone.utc)
            status = "inactive"
            can_vote = False
            
            if election:
                debut = ensure_timezone(election.date_debut)
                fin = ensure_timezone(election.date_fin)
                
                if debut and fin:
                    if debut <= now <= fin:
                        status = "active"
                        can_vote = True
                    elif now < debut:
                        status = "pending"
                    else:
                        status = "finished"
            
            return jsonify({
                'system': {
                    'status': 'online',
                    'timestamp': now.isoformat(),
                    'python_version': sys.version.split()[0],
                    'database': 'PostgreSQL',
                    'year': 2026
                },
                'election': {
                    'status': status,
                    'title': election.titre if election else None,
                    'date_debut': election.date_debut.isoformat() if election else None,
                    'date_fin': election.date_fin.isoformat() if election else None,
                    'temps_restant': election.get_temps_restant() if election else None,
                    'can_vote': can_vote
                },
                'statistics': {
                    'candidates': candidates_count,
                    'votes': votes_count,
                    'participation_rate': round((votes_count / 50 * 100), 2) if votes_count > 0 else 0
                }
            })
    except Exception as e:
        print(f"❌ Erreur status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/election', methods=['GET'])
def get_election():
    """Récupère l'élection active avec les candidats"""
    try:
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            if not election:
                return jsonify({'error': 'Aucune élection active'}), 404
            
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            now = datetime.now(timezone.utc)
            
            election_status = "active" if debut <= now <= fin else "pending" if now < debut else "finished"
            
            candidates = Candidate.query.filter_by(election_id=election.id).all()
            
            result = election.to_dict()
            result['candidates'] = [c.to_dict() for c in candidates]
            result['status'] = election_status
            result['can_vote'] = debut <= now <= fin
            
            return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur récupération élection: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    """Enregistre un nouveau vote"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        professeur_email = data.get('professeur_email')
        candidate_id = data.get('candidate_id')
        
        if not professeur_email or not candidate_id:
            return jsonify({'error': 'professeur_email et candidate_id sont requis'}), 400
        
        if '@' not in professeur_email or '.' not in professeur_email:
            return jsonify({'error': 'Email invalide'}), 400
        
        try:
            candidate_id = int(candidate_id)
        except ValueError:
            return jsonify({'error': 'candidate_id doit être un nombre valide'}), 400
        
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            if not election:
                return jsonify({'error': 'Aucune élection active'}), 400
            
            now = datetime.now(timezone.utc)
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            
            if now < debut:
                return jsonify({'error': f'L\'élection n\'a pas encore commencé'}), 400
            
            if now > fin:
                return jsonify({'error': f'L\'élection est terminée'}), 400
            
            existing_vote = Vote.query.filter_by(
                election_id=election.id,
                professeur_email=professeur_email
            ).first()
            
            if existing_vote:
                return jsonify({'error': 'Ce professeur a déjà voté'}), 400
            
            candidate = Candidate.query.filter_by(id=candidate_id, election_id=election.id).first()
            if not candidate:
                return jsonify({'error': 'Candidat non trouvé'}), 404
            
            vote = Vote(
                election_id=election.id,
                candidate_id=candidate_id,
                professeur_email=professeur_email,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            candidate.votes_count += 1
            
            db.session.add(vote)
            db.session.commit()
            
            print(f"✅ Vote enregistré pour {professeur_email}")
            
            return jsonify({
                'success': True,
                'message': 'Vote enregistré avec succès',
                'vote': vote.to_dict(),
                'candidate': candidate.to_dict(),
                'votes_count': candidate.votes_count
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors du vote: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Récupère les résultats du vote"""
    try:
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            if not election:
                return jsonify({'error': 'Aucune élection active'}), 404
            
            candidates = Candidate.query.filter_by(election_id=election.id).all()
            total_votes = sum(c.votes_count for c in candidates)
            
            results = []
            for candidate in candidates:
                percentage = (candidate.votes_count / total_votes * 100) if total_votes > 0 else 0
                results.append({
                    'candidate': candidate.to_dict(),
                    'votes': candidate.votes_count,
                    'percentage': round(percentage, 2),
                    'rank': None
                })
            
            results.sort(key=lambda x: x['votes'], reverse=True)
            for i, result in enumerate(results, 1):
                result['rank'] = i
            
            now = datetime.now(timezone.utc)
            fin = ensure_timezone(election.date_fin)
            is_finished = now > fin
            
            return jsonify({
                'election': election.to_dict(),
                'total_votes': total_votes,
                'results': results,
                'is_finished': is_finished,
                'updated_at': now.isoformat()
            })
    except Exception as e:
        print(f"❌ Erreur résultats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Statistiques détaillées"""
    try:
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            if not election:
                return jsonify({'error': 'Aucune élection active'}), 404
            
            total_votes = Vote.query.filter_by(election_id=election.id).count()
            total_candidates = Candidate.query.filter_by(election_id=election.id).count()
            
            now_utc = datetime.now(timezone.utc)
            fin = ensure_timezone(election.date_fin)
            temps_restant = fin - now_utc if fin > now_utc else timedelta(0)
            
            return jsonify({
                'election': election.to_dict(),
                'statistics': {
                    'total_votes': total_votes,
                    'total_candidates': total_candidates,
                    'participation_rate': round((total_votes / 50 * 100), 2) if total_votes > 0 else 0,
                    'temps_restant_jours': temps_restant.days,
                    'temps_restant_heures': int(temps_restant.seconds // 3600)
                },
                'updated_at': now_utc.isoformat()
            })
    except Exception as e:
        print(f"❌ Erreur statistiques: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Vérifie si un email a déjà voté"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        with app.app_context():
            election = Election.query.filter_by(statut='active').first()
            if not election:
                return jsonify({'error': 'Aucune élection active'}), 404
            
            vote = Vote.query.filter_by(
                election_id=election.id,
                professeur_email=email
            ).first()
            
            now = datetime.now(timezone.utc)
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            
            can_vote = debut <= now <= fin
            
            return jsonify({
                'has_voted': vote is not None,
                'email': email,
                'can_vote': can_vote
            })
    except Exception as e:
        print(f"❌ Erreur vérification email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-test', methods=['POST'])
def reset_test_data():
    """Réinitialise les données de test (développement seulement)"""
    try:
        with app.app_context():
            Vote.query.delete()
            
            candidates = Candidate.query.all()
            for candidate in candidates:
                candidate.votes_count = 0
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Données de test réinitialisées'
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 DÉMARRAGE DU SYSTÈME DE VOTE SCOLAIRE 2026")
    print("=" * 60)
    
    # Initialiser la base de données
    init_database()
    
    print("=" * 60)
    port = int(os.getenv('PORT', 5000))
    print(f"🌐 Serveur sur le port: {port}")
    print(f"📡 URL: http://localhost:{port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)