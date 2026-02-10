from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ==================== CONFIGURATION DES CHEMINS ====================

# Pour Render, on détermine les chemins corrects
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # Remonter d'un niveau
FRONTEND_PATH = os.path.join(PROJECT_ROOT, 'front')

print("=" * 80)
print("🚀 SYSTÈME DE VOTE SCOLAIRE 2026 - BACKEND FLASK")
print("=" * 80)
print(f"📁 Dossier backend: {BASE_DIR}")
print(f"📁 Dossier projet: {PROJECT_ROOT}")
print(f"📁 Chemin frontend: {FRONTEND_PATH}")
print(f"📁 Frontend existe: {os.path.exists(FRONTEND_PATH)}")

if os.path.exists(FRONTEND_PATH):
    print(f"📁 Fichiers frontend: {os.listdir(FRONTEND_PATH)}")
else:
    print("⚠️  AVERTISSEMENT: Dossier frontend non trouvé")
    print("📁 Dossiers à la racine:", os.listdir(PROJECT_ROOT) if os.path.exists(PROJECT_ROOT) else "Projet non trouvé")

app = Flask(__name__, static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None)
CORS(app)  # Activer CORS pour toutes les routes

# ==================== CONFIGURATION BASE DE DONNÉES ====================

SQLITE_DB_PATH = os.path.join(BASE_DIR, 'votes.db')
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

print(f"🔗 Base de données: {SQLITE_DB_PATH}")
print(f"🔗 URL Database: {DATABASE_URL}")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vote_2026_la_source_fontaine_secret_secure_key_98765')

db = SQLAlchemy(app)

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
        fin = ensure_timezone(self.date_fin)
        
        if now < fin:
            diff = fin - now
            jours = diff.days
            heures = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            return f"{jours}j {heures:02d}h {minutes:02d}m"
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

# ==================== FONCTIONS UTILITAIRES ====================

def ensure_timezone(dt):
    """Assure qu'une datetime a un timezone UTC"""
    if dt is None:
        return None
    
    if dt.tzinfo is not None:
        # Déjà avec timezone, convertir en UTC
        return dt.astimezone(timezone.utc)
    else:
        # Sans timezone, ajouter UTC
        return dt.replace(tzinfo=timezone.utc)

def check_admin_access():
    """Vérifie si la requête provient de l'admin"""
    admin_secret = request.args.get('admin_secret')
    
    # Secret admin unique
    expected_secret = 'admin2026'
    
    if admin_secret == expected_secret:
        print(f"✅ Accès admin accordé pour: {request.remote_addr}")
        return True
    
    print(f"❌ Accès admin refusé. Secret reçu: {admin_secret}")
    return False

# ==================== ROUTES FRONTEND ====================

@app.route('/')
def index():
    """Page d'accueil - sert index.html"""
    if os.path.exists(FRONTEND_PATH):
        try:
            return send_from_directory(FRONTEND_PATH, 'index.html')
        except Exception as e:
            print(f"❌ Erreur chargement index.html: {e}")
            return fallback_index()
    else:
        return fallback_index()

def fallback_index():
    """Page de fallback si le frontend n'est pas disponible"""
    return '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Système de Vote Scolaire 2026</title>
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }
            .container { max-width: 1000px; margin: 0 auto; background: rgba(255, 255, 255, 0.95); padding: 40px; border-radius: 20px; color: #333; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            .header { text-align: center; margin-bottom: 40px; }
            .logo { font-size: 3rem; margin-bottom: 20px; }
            h1 { color: #4361ee; font-size: 2.5rem; margin-bottom: 10px; }
            h2 { color: #7209b7; font-size: 1.8rem; margin-bottom: 30px; }
            .card { background: #f8f9fa; padding: 25px; border-radius: 15px; margin: 20px 0; border-left: 6px solid #4361ee; }
            .api-link { display: block; padding: 15px 20px; background: #e9ecef; margin: 10px 0; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; transition: all 0.3s; border: 2px solid transparent; }
            .api-link:hover { background: #4361ee; color: white; transform: translateY(-3px); border-color: #3a0ca3; }
            .api-link i { margin-right: 10px; }
            .status { display: inline-block; padding: 10px 20px; background: #4cc9f0; color: white; border-radius: 20px; font-weight: bold; }
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🗳️</div>
                <h1>Système de Vote Scolaire 2026</h1>
                <h2>Cours privés "La Source de la Fontaine"</h2>
                <div class="status">📡 BACKEND OPERATIONNEL</div>
            </div>
            
            <div class="card">
                <h3><i class="fas fa-rocket"></i> API Backend Prête</h3>
                <p>Le serveur Flask fonctionne correctement. Les API suivantes sont disponibles :</p>
                
                <a href="/api/status" class="api-link">
                    <i class="fas fa-chart-bar"></i> 📊 /api/status - Statut du système
                </a>
                <a href="/api/election" class="api-link">
                    <i class="fas fa-school"></i> 🏫 /api/election - Élection active
                </a>
                <a href="/api/results?admin_secret=admin2026" class="api-link">
                    <i class="fas fa-lock"></i> 🔐 /api/results - Résultats (Admin)
                </a>
                <a href="/api/stats?admin_secret=admin2026" class="api-link">
                    <i class="fas fa-chart-line"></i> 📈 /api/stats - Statistiques (Admin)
                </a>
                
                <div style="margin-top: 30px; padding: 20px; background: rgba(67, 97, 238, 0.1); border-radius: 10px;">
                    <h4><i class="fas fa-info-circle"></i> Informations techniques</h4>
                    <p><strong>Base de données :</strong> SQLite</p>
                    <p><strong>Période de vote :</strong> 9-13 février 2026</p>
                    <p><strong>Version :</strong> 2.0.0</p>
                    <p><strong>Serveur :</strong> Flask avec SQLAlchemy</p>
                </div>
            </div>
            
            <p style="text-align: center; margin-top: 40px; color: #666; padding-top: 20px; border-top: 2px solid #eee;">
                <i class="fas fa-copyright"></i> 2026 - Cours privés La Source de la Fontaine - Tous droits réservés
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/<path:path>')
def serve_frontend(path):
    """Sert les fichiers statiques du frontend"""
    if os.path.exists(FRONTEND_PATH):
        try:
            return send_from_directory(FRONTEND_PATH, path)
        except Exception as e:
            print(f"❌ Erreur chargement {path}: {e}")
            return jsonify({'error': 'Fichier non trouvé', 'path': path}), 404
    else:
        return jsonify({'error': 'Frontend non disponible'}), 404

# ==================== INITIALISATION BASE DE DONNÉES ====================

def init_database():
    """Initialise la base de données SQLite"""
    with app.app_context():
        try:
            print("🔗 Initialisation de la base de données...")
            
            # Créer les tables
            db.create_all()
            print("✅ Tables créées/vérifiées")
            
            # Vérifier si une élection existe
            election = Election.query.filter_by(statut='active').first()
            
            if not election:
                # Période de vote : 9-13 février 2026
                date_debut = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
                date_fin = datetime(2026, 2, 13, 23, 59, 59, tzinfo=timezone.utc)
                
                election = Election(
                    titre="Élection des Délégués Élèves 2026",
                    description="Vote des professeurs pour élire les délégués élèves de chaque classe. Période de vote : du 9 au 13 février 2026.",
                    date_debut=date_debut,
                    date_fin=date_fin,
                    statut='active'
                )
                db.session.add(election)
                db.session.commit()
                print(f"✅ Nouvelle élection 2026 créée")
                print(f"📅 Période de vote : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}")
            else:
                print(f"✅ Élection existante chargée: {election.titre}")
            
            # Vérifier et créer les candidates
            candidates_count = Candidate.query.filter_by(election_id=election.id).count()
            
            if candidates_count == 0:
                # Liste des candidates réelles
                candidates_data = [
                    {'nom': 'Diallo', 'prenom': 'Binta', 'classe': '3ème', 'description': 'Candidate sérieuse et impliquée'},
                    {'nom': 'Ngom', 'prenom': 'Maguette', 'classe': '6ème', 'description': 'Dynamique et à l\'écoute'},
                    {'nom': 'Gomis', 'prenom': 'Eléna Nafissatou', 'classe': '5ème', 'description': 'Responsable et organisée'},
                    {'nom': 'Séne', 'prenom': 'Diasse', 'classe': '2nde', 'description': 'Créative et motivante'},
                    {'nom': 'Ndong', 'prenom': 'Ndeye Fatou', 'classe': '4ème', 'description': 'Sait communiquer et représenter'}
                ]
                
                for cand_data in candidates_data:
                    candidate = Candidate(
                        nom=cand_data['nom'],
                        prenom=cand_data['prenom'],
                        classe=cand_data['classe'],
                        description=cand_data['description'],
                        election_id=election.id,
                        photo_url=f"https://ui-avatars.com/api/?name={cand_data['prenom']}+{cand_data['nom']}&background=random&color=fff&size=200&bold=true"
                    )
                    db.session.add(candidate)
                
                db.session.commit()
                print(f"✅ {len(candidates_data)} candidates créées")
            else:
                print(f"✅ {candidates_count} candidates existantes chargées")
            
            total_votes = Vote.query.count()
            print(f"📊 Total votes enregistrés : {total_votes}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

# ==================== ROUTES API ====================

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Retourne le statut complet du système"""
    try:
        election = Election.query.filter_by(statut='active').first()
        candidates_count = Candidate.query.count() if Candidate.query.first() else 0
        votes_count = Vote.query.count()
        
        now = datetime.now(timezone.utc)
        status = "inactive"
        can_vote = False
        temps_restant = None
        
        if election:
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            
            if debut and fin:
                if debut <= now <= fin:
                    status = "active"
                    can_vote = True
                    # Calcul précis du temps restant
                    temps_restant_seconds = int((fin - now).total_seconds())
                    jours = temps_restant_seconds // 86400
                    heures = (temps_restant_seconds % 86400) // 3600
                    minutes = (temps_restant_seconds % 3600) // 60
                    temps_restant = f"{jours}j {heures:02d}h {minutes:02d}m"
                elif now < debut:
                    status = "pending"
                    temps_restant = "Pas encore commencé"
                else:
                    status = "finished"
                    temps_restant = "Terminé"
        
        # Nombre total de professeurs (estimation)
        total_professeurs = 50
        participation_rate = round((votes_count / total_professeurs * 100), 1) if total_professeurs > 0 else 0
        
        return jsonify({
            'system': {
                'status': 'online',
                'timestamp': now.isoformat(),
                'database': 'SQLite',
                'year': 2026,
                'ecole': 'Cours privés La Source de la Fontaine',
                'version': '2.0.0',
                'environment': 'production' if not app.debug else 'development'
            },
            'election': {
                'status': status,
                'title': election.titre if election else None,
                'description': election.description if election else None,
                'date_debut': election.date_debut.isoformat() if election else None,
                'date_fin': election.date_fin.isoformat() if election else None,
                'temps_restant': temps_restant,
                'can_vote': can_vote
            },
            'statistics': {
                'candidates': candidates_count,
                'votes': votes_count,
                'total_professeurs': total_professeurs,
                'participation_rate': participation_rate,
                'remaining_votes': max(0, total_professeurs - votes_count)
            }
        })
    except Exception as e:
        print(f"❌ Erreur status: {str(e)}")
        return jsonify({
            'error': 'Erreur serveur',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': str(e)
        }), 500

@app.route('/api/election', methods=['GET'])
def get_election():
    """Récupère l'élection active avec les candidates"""
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        candidates = Candidate.query.filter_by(election_id=election.id).order_by(Candidate.classe).all()
        
        result = election.to_dict()
        result['candidates'] = [c.to_dict() for c in candidates]
        
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur récupération élection: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    """Enregistre un nouveau vote"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        professeur_email = data.get('professeur_email', '').strip().lower()
        candidate_id = data.get('candidate_id')
        
        # Validation
        if not professeur_email:
            return jsonify({'error': 'Email du professeur requis'}), 400
        
        if not candidate_id:
            return jsonify({'error': 'ID de la candidate requis'}), 400
        
        # Validation email simple
        if '@' not in professeur_email or '.' not in professeur_email:
            return jsonify({'error': 'Format d\'email invalide'}), 400
        
        try:
            candidate_id = int(candidate_id)
        except ValueError:
            return jsonify({'error': 'ID de candidate invalide'}), 400
        
        # Vérifier l'élection active
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 400
        
        # Vérifier les dates
        now = datetime.now(timezone.utc)
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        
        if debut and now < debut:
            return jsonify({'error': 'L\'élection n\'a pas encore commencé'}), 400
        
        if fin and now > fin:
            return jsonify({'error': 'L\'élection est terminée'}), 400
        
        # Vérifier si le professeur a déjà voté
        existing_vote = Vote.query.filter_by(
            election_id=election.id,
            professeur_email=professeur_email
        ).first()
        
        if existing_vote:
            return jsonify({
                'error': 'Vous avez déjà voté',
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None
            }), 400
        
        # Vérifier si la candidate existe
        candidate = Candidate.query.filter_by(id=candidate_id, election_id=election.id).first()
        if not candidate:
            return jsonify({'error': 'Candidate non trouvée'}), 404
        
        # Enregistrer le vote
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id,
            professeur_email=professeur_email,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        # Mettre à jour le compteur de votes
        candidate.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        print(f"✅ Vote enregistré: {professeur_email} → {candidate.prenom} {candidate.nom}")
        
        return jsonify({
            'success': True,
            'message': 'Votre vote a été enregistré avec succès',
            'confirmation_id': f"VOTE-{vote.id:06d}",
            'timestamp': vote.date_vote.isoformat() if vote.date_vote else now.isoformat(),
            'year': 2026,
            'ecole': 'Cours privés La Source de la Fontaine',
            'candidate': f"{candidate.prenom} {candidate.nom}",
            'classe': candidate.classe
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors du vote: {str(e)}")
        return jsonify({'error': 'Erreur serveur lors de l\'enregistrement du vote'}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Récupère les résultats du vote - ADMIN SEULEMENT"""
    if not check_admin_access():
        return jsonify({
            'error': 'Accès refusé',
            'message': 'Cette fonctionnalité est réservée à l\'administration',
            'hint': 'Utilisez ?admin_secret=admin2026'
        }), 403
    
    try:
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
                'percentage': round(percentage, 2)
            })
        
        # Trier par nombre de votes (décroissant)
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        # Ajouter le rang
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return jsonify({
            'election': election.to_dict(),
            'total_votes': total_votes,
            'results': results,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'year': 2026,
            'ecole': 'Cours privés La Source de la Fontaine'
        })
    except Exception as e:
        print(f"❌ Erreur résultats: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Statistiques détaillées - ADMIN SEULEMENT"""
    if not check_admin_access():
        return jsonify({
            'error': 'Accès refusé',
            'message': 'Cette fonctionnalité est réservée à l\'administration',
            'hint': 'Utilisez ?admin_secret=admin2026'
        }), 403
    
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        # Calculer les statistiques de base
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        total_candidates = Candidate.query.filter_by(election_id=election.id).count()
        total_professeurs = 50
        
        now_utc = datetime.now(timezone.utc)
        
        # Vérifier les dates avec timezone
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        
        # Temps restant
        temps_restant = timedelta(0)
        if fin and now_utc < fin:
            temps_restant = fin - now_utc
        
        # Votes des dernières 24 heures
        yesterday_utc = now_utc - timedelta(hours=24)
        last_24h = Vote.query.filter(
            Vote.election_id == election.id,
            Vote.created_at >= yesterday_utc
        ).count()
        
        # Votes par candidate
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        votes_by_candidate = []
        for c in candidates:
            votes_by_candidate.append({
                'id': c.id,
                'nom_complet': f"{c.prenom} {c.nom}",
                'classe': c.classe,
                'votes': c.votes_count
            })
        
        # Trier par votes décroissants
        votes_by_candidate.sort(key=lambda x: x['votes'], reverse=True)
        
        # Liste des votants (limité à 50)
        votes = Vote.query.filter_by(election_id=election.id)\
            .order_by(Vote.created_at.desc())\
            .limit(50)\
            .all()
        
        votants = []
        for v in votes:
            candidate = Candidate.query.get(v.candidate_id)
            votants.append({
                'email': v.professeur_email,
                'date_vote': v.created_at.isoformat() if v.created_at else None,
                'candidate_id': v.candidate_id,
                'candidate_nom': f"{candidate.prenom} {candidate.nom}" if candidate else "N/A",
                'candidate_classe': candidate.classe if candidate else "N/A"
            })
        
        # Calculs
        participation_rate = round((total_votes / total_professeurs * 100), 2) if total_professeurs > 0 else 0
        
        return jsonify({
            'election': {
                'id': election.id,
                'titre': election.titre,
                'date_debut': election.date_debut.isoformat() if election.date_debut else None,
                'date_fin': election.date_fin.isoformat() if election.date_fin else None,
                'statut': election.statut,
                'temps_restant': election.get_temps_restant()
            },
            'statistics': {
                'total_votes': total_votes,
                'total_candidates': total_candidates,
                'total_professeurs': total_professeurs,
                'votes_last_24h': last_24h,
                'participation_rate': participation_rate,
                'remaining_votes': max(0, total_professeurs - total_votes),
                'temps_restant_jours': temps_restant.days,
                'temps_restant_heures': int(temps_restant.seconds // 3600) if temps_restant else 0,
                'temps_restant_minutes': int((temps_restant.seconds % 3600) // 60) if temps_restant else 0,
                'votes_by_candidate': votes_by_candidate
            },
            'votants': votants,
            'recent_votes': votants[:10],
            'total_votants': total_votes,
            'periode_vote': {
                'date_debut': election.date_debut.isoformat() if election.date_debut else None,
                'date_fin': election.date_fin.isoformat() if election.date_fin else None,
                'vote_actif': election.date_debut and election.date_fin and 
                              (ensure_timezone(election.date_debut) <= now_utc <= ensure_timezone(election.date_fin))
            },
            'updated_at': now_utc.isoformat(),
            'year': 2026,
            'ecole': 'Cours privés La Source de la Fontaine',
            'access': 'admin'
        })
        
    except Exception as e:
        print(f"❌ Erreur statistiques: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': 'Erreur serveur',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Vérifie si un email a déjà voté"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        vote = Vote.query.filter_by(
            election_id=election.id,
            professeur_email=email
        ).first()
        
        # Vérifier si l'élection est en cours
        now = datetime.now(timezone.utc)
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        
        can_vote = debut and fin and (debut <= now <= fin)
        has_voted = vote is not None
        
        response = {
            'has_voted': has_voted,
            'email': email,
            'can_vote': can_vote,
            'election_status': 'active' if can_vote else 'inactive'
        }
        
        if has_voted:
            response['vote_date'] = vote.date_vote.isoformat() if vote.date_vote else None
            response['message'] = 'Vous avez déjà voté pour cette élection'
            response['can_vote'] = False
        elif can_vote:
            response['message'] = 'Vous pouvez voter'
        else:
            response['message'] = 'La période de vote n\'est pas active'
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Erreur vérification email: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/reset-votes', methods=['POST'])
def reset_votes():
    """Réinitialise tous les votes - ADMIN SEULEMENT"""
    if not check_admin_access():
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        # Supprimer tous les votes
        deleted_count = Vote.query.delete()
        
        # Réinitialiser les compteurs
        candidates = Candidate.query.all()
        for candidate in candidates:
            candidate.votes_count = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} votes réinitialisés',
            'votes_deleted': deleted_count,
            'candidates_reset': len(candidates),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur réinitialisation: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== LANCEMENT DE L'APPLICATION ====================

if __name__ == '__main__':
    print("=" * 80)
    print("🏫 ÉCOLE : Cours privés La Source de la Fontaine")
    print("🗳️  CANDIDATES 2026 :")
    print("   • Binta Diallo (3ème)")
    print("   • Maguette Ngom (6ème)")
    print("   • Eléna Nafissatou Gomis (5ème)")
    print("   • Diasse Séne (2nde)")
    print("   • Ndeye Fatou Ndong (4ème)")
    print("=" * 80)
    
    # Initialiser la base de données
    if init_database():
        print("✅ Base de données initialisée avec succès")
    else:
        print("⚠️  Base de données non initialisée correctement")
    
    print("=" * 80)
    
    # Obtenir le port depuis les variables d'environnement (pour Render)
    port = int(os.getenv('PORT', 10000))
    
    print(f"📡 SERVEUR FLASK DÉMARRÉ")
    print(f"🌐 Port d'écoute: {port}")
    print(f"🌍 URL Local: http://localhost:{port}")
    print(f"📋 API Élection : http://localhost:{port}/api/election")
    print(f"🔐 API Résultats : http://localhost:{port}/api/results?admin_secret=admin2026")
    print(f"📊 API Statistiques : http://localhost:{port}/api/stats?admin_secret=admin2026")
    print(f"⚙️  API Status : http://localhost:{port}/api/status")
    print("=" * 80)
    print("⏰ PÉRIODE DE VOTE : 9-13 février 2026")
    print("=" * 80)
    print("👨‍🏫 PRÊT POUR LES VOTES DES PROFESSEURS !")
    print("=" * 80)
    
    # Démarrer le serveur
    app.run(debug=False, port=port, host='0.0.0.0')