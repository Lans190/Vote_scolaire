from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
import secrets
from dotenv import load_dotenv
import warnings
from sqlalchemy.exc import SAWarning

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
app.config['SESSION_COOKIE_SECURE'] = True  # True pour production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app, supports_credentials=True, origins=[
    'https://vote-scolaire.onrender.com',
    'http://localhost:3000',
    'http://localhost:5000'
])

# ==================== CONFIGURATION POSTGRESQL (RENDER) ====================

# Récupérer l'URL de PostgreSQL depuis Render
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Render utilise "postgres://" mais SQLAlchemy veut "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print(f"✅ PostgreSQL configuré (Render)")
    print(f"📊 Connexion à PostgreSQL établie")
else:
    # Fallback SQLite pour développement local
    SQLITE_DB_PATH = os.path.join(BASE_DIR, 'votes.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{SQLITE_DB_PATH}'
    print(f"⚠️  Mode développement: SQLite local")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_size': 10,
    'max_overflow': 20,
}

db = SQLAlchemy(app)

# ==================== MODÈLES DE BASE DE DONNÉES ====================

class Election(db.Model):
    __tablename__ = 'election'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Candidate(db.Model):
    __tablename__ = 'candidate'
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
    __tablename__ = 'vote'
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
            print("🔗 Création des tables si elles n'existent pas...")
            db.create_all()
            print("✅ Tables vérifiées/créées")
            
            # Vérifier si une élection existe déjà
            election = Election.query.first()
            
            if not election:
                print("📝 Création de l'élection par défaut...")
                election = Election(
                    titre="Élection des Délégués Élèves 2026",
                    date_debut=datetime(2026, 2, 10, 0, 0, 0, tzinfo=timezone.utc),
                    date_fin=datetime(2026, 3, 15, 23, 59, 59, tzinfo=timezone.utc),  # Prolongée
                    statut='active'
                )
                db.session.add(election)
                db.session.flush()  # Pour obtenir l'ID sans commit
                
                # Créer les candidates UNIQUEMENT si aucune n'existe
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
                print(f"✅ Élection et candidates créées")
            else:
                print(f"✅ Élection existante trouvée: '{election.titre}'")
                
                # Vérifier et créer les candidates si manquantes
                if Candidate.query.count() == 0 and election:
                    print("⚠️  Aucune candidate trouvée, création...")
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
            
            # Statistiques finales
            candidates_count = Candidate.query.count()
            votes_count = Vote.query.count()
            print(f"📊 État initial: {candidates_count} candidates, {votes_count} votes")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
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
    <form onsubmit="login(event)">
        <input type="password" id="password" placeholder="Mot de passe admin">
        <button>Se connecter</button>
    </form>
    <script>
        function login(e) {
            e.preventDefault();
            if(document.getElementById('password').value === 'admin2026') {
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
        return fallback_admin_dashboard()

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
        temps_restant = "En cours"
        if election and election.date_fin:
            fin = election.date_fin
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
                if election.statut == 'active':
                    election.statut = 'closed'
                    db.session.commit()
        
        # Vérifier si on peut voter
        can_vote = True
        if election and election.statut != 'active':
            can_vote = False
        elif election and election.date_fin and election.date_fin < now:
            can_vote = False
        
        return jsonify({
            'system': {
                'status': 'online',
                'database': 'PostgreSQL' if DATABASE_URL else 'SQLite',
                'year': 2026,
                'ecole': 'Cours privés La Source de la Fontaine',
                'timestamp': now.isoformat(),
                'persistent': bool(DATABASE_URL)
            },
            'election': {
                'status': election.statut if election else 'inactive',
                'titre': election.titre if election else 'Non configurée',
                'temps_restant': temps_restant,
                'can_vote': can_vote,
                'date_fin': election.date_fin.isoformat() if election and election.date_fin else None
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
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection configurée'}), 404
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        
        # Configuration des images des candidates
        candidate_images = {
            1: '/static/candidates/1.jpg',
            2: '/static/candidates/2.jpg',
            3: '/static/candidates/3.jpg',
            4: '/static/candidates/4.jpg',
            5: '/static/candidates/5.jpg',
        }
        
        # Couleurs pour les avatars de secours
        avatar_colors = [
            '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
            '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#9b5de5'
        ]
        
        candidates_list = []
        for idx, candidate in enumerate(candidates):
            # Initiales pour l'avatar
            initials = f"{candidate.prenom[0]}{candidate.nom[0]}"
            # Couleur basée sur l'ID
            color = avatar_colors[candidate.id % len(avatar_colors)]
            
            candidates_list.append({
                'id': candidate.id,
                'nom': candidate.nom,
                'prenom': candidate.prenom,
                'nom_complet': candidate.nom_complet,
                'classe': candidate.classe,
                'description': candidate.description or f"Candidate pour la classe de {candidate.classe}",
                'votes_count': candidate.votes_count,
                'image_url': candidate_images.get(candidate.id, f'/static/candidates/{candidate.id}.jpg'),
                'avatar_color': color,
                'initials': initials
            })
        
        return jsonify({
            'status': election.statut,
            'title': election.titre,
            'date_fin': election.date_fin.isoformat() if election.date_fin else None,
            'candidates': candidates_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
def api_verify_email():
    """Vérifie si un email peut voter"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({'error': 'Email valide requis'}), 400
        
        # Vérifier l'élection
        election = Election.query.first()
        if not election or election.statut != 'active':
            return jsonify({
                'has_voted': False,
                'can_vote': False,
                'message': 'L\'élection n\'est pas active'
            })
        
        # Vérifier si déjà voté
        existing_vote = Vote.query.filter_by(
            professeur_email=email,
            election_id=election.id
        ).first()
        
        if existing_vote:
            return jsonify({
                'has_voted': True,
                'vote_date': existing_vote.date_vote.isoformat() if existing_vote.date_vote else None,
                'message': 'Vous avez déjà voté pour cette élection',
                'can_vote': False
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
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
            
        email = data.get('professeur_email', '').strip().lower()
        candidate_id = data.get('candidate_id')
        
        if not email or '@' not in email:
            return jsonify({'error': 'Email valide requis'}), 400
        
        if not candidate_id:
            return jsonify({'error': 'Candidate requis'}), 400
        
        try:
            candidate_id = int(candidate_id)
        except:
            return jsonify({'error': 'ID de candidate invalide'}), 400
        
        # Vérifier l'élection
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection configurée'}), 404
            
        if election.statut != 'active':
            return jsonify({'error': 'L\'élection n\'est plus active'}), 400
        
        # Vérifier si déjà voté
        existing_vote = Vote.query.filter_by(
            professeur_email=email,
            election_id=election.id
        ).first()
        
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
        
        # Vérifier que la candidate appartient à cette élection
        if candidate.election_id != election.id:
            return jsonify({'error': 'Candidate ne fait pas partie de cette élection'}), 400
        
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
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        # Récupérer toutes les candidates de cette élection
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        
        # Images des candidates
        candidate_images = {
            1: '/static/candidates/1.jpg',
            2: '/static/candidates/2.jpg',
            3: '/static/candidates/3.jpg',
            4: '/static/candidates/4.jpg',
            5: '/static/candidates/5.jpg',
        }
        
        results = []
        for candidate in candidates:
            # Compter les votes pour cette candidate
            candidate_votes = Vote.query.filter_by(
                election_id=election.id,
                candidate_id=candidate.id
            ).count()
            
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
                'percentage': round(percentage, 2),
                'image_url': candidate_images.get(candidate.id, f'/static/candidates/{candidate.id}.jpg')
            })
        
        # Trier par nombre de votes (décroissant)
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        # Ajouter le rang
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return jsonify({
            'election': {
                'title': election.titre,
                'total_votes': total_votes,
                'date_fin': election.date_fin.isoformat() if election.date_fin else None,
                'statut': election.statut,
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
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        # Récupérer tous les votes de cette élection
        votes = Vote.query.filter_by(election_id=election.id)\
                         .order_by(Vote.date_vote.desc())\
                         .limit(50).all()
        
        # Derniers votants
        recent_voters = []
        for vote in votes:
            candidate = Candidate.query.get(vote.candidate_id)
            # Masquer partiellement l'email pour la confidentialité
            email = vote.professeur_email
            if '@' in email:
                parts = email.split('@')
                masked_email = parts[0][:3] + '***@' + parts[1]
            else:
                masked_email = email
            
            recent_voters.append({
                'email': masked_email,
                'date_vote': vote.date_vote.isoformat() if vote.date_vote else None,
                'candidate_id': vote.candidate_id,
                'candidate_nom': candidate.nom_complet if candidate else 'N/A',
                'candidate_classe': candidate.classe if candidate else 'N/A'
            })
        
        # Votes par heure (dernières 24h)
        votes_by_hour = {}
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        recent_votes = Vote.query.filter(
            Vote.election_id == election.id,
            Vote.date_vote >= twenty_four_hours_ago
        ).all()
        
        for vote in recent_votes:
            if vote.date_vote:
                hour = vote.date_vote.strftime('%H:00')
                votes_by_hour[hour] = votes_by_hour.get(hour, 0) + 1
        
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        total_candidates = Candidate.query.filter_by(election_id=election.id).count()
        
        return jsonify({
            'election': election.titre,
            'total_votes': total_votes,
            'total_candidates': total_candidates,
            'votes_last_hour': len([v for v in votes if v.date_vote and 
                                   (datetime.now(timezone.utc) - v.date_vote).total_seconds() < 3600]),
            'votes_by_hour': votes_by_hour,
            'recent_voters': recent_voters,
            'last_update': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        print(f"❌ Erreur stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/extend-election', methods=['POST'])
def extend_election():
    """Prolonge la durée de l'élection - ADMIN SEULEMENT"""
    admin_secret = request.args.get('admin_secret') or (request.json.get('admin_secret') if request.json else None)
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        data = request.json
        days_to_add = data.get('days', 7)
        
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        # Prolonger la date de fin
        if election.date_fin:
            new_end_date = election.date_fin + timedelta(days=days_to_add)
        else:
            new_end_date = datetime.now(timezone.utc) + timedelta(days=days_to_add)
        
        election.date_fin = new_end_date
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Élection prolongée de {days_to_add} jours',
            'new_end_date': new_end_date.isoformat(),
            'days_added': days_to_add
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/db-status', methods=['GET'])
def db_status():
    """Statut de la base de données - ADMIN SEULEMENT"""
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        # Test de connexion
        db.session.execute('SELECT 1')
        
        # Infos détaillées
        candidates = Candidate.query.all()
        votes = Vote.query.all()
        
        # Derniers votes (masqués)
        recent_votes = []
        for vote in votes[-10:]:
            candidate = Candidate.query.get(vote.candidate_id)
            email = vote.professeur_email
            if '@' in email:
                parts = email.split('@')
                masked_email = parts[0][:3] + '***@' + parts[1]
            else:
                masked_email = email
            
            recent_votes.append({
                'email': masked_email,
                'candidate': candidate.nom_complet if candidate else 'N/A',
                'date': vote.date_vote.isoformat() if vote.date_vote else None
            })
        
        return jsonify({
            'status': 'healthy',
            'database': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'persistent': bool(DATABASE_URL),
            'stats': {
                'candidates': len(candidates),
                'votes': len(votes),
                'last_vote': votes[-1].date_vote.isoformat() if votes else None
            },
            'recent_votes': recent_votes,
            'database_url_exists': 'DATABASE_URL' in os.environ,
            'tables': ['election', 'candidate', 'vote']
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database': 'Unknown',
            'database_url_exists': 'DATABASE_URL' in os.environ
        }), 500

# ==================== ROUTES DE DEBUG ====================

@app.route('/api/test-db', methods=['GET'])
def test_db():
    """Test de connexion à la base de données"""
    try:
        # Test simple
        result = db.session.execute('SELECT version()').fetchone()
        version = result[0] if result else 'Unknown'
        
        # Compter
        candidates = Candidate.query.count()
        votes = Vote.query.count()
        elections = Election.query.count()
        
        return jsonify({
            'status': 'OK',
            'database': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'version': version[:100],
            'elections': elections,
            'candidates': candidates,
            'votes': votes,
            'persistent': bool(DATABASE_URL),
            'message': '✅ Base de données fonctionne correctement !'
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'database_url_exists': 'DATABASE_URL' in os.environ,
            'database_url': 'Present' if DATABASE_URL else 'Missing'
        }), 500

@app.route('/api/debug/routes', methods=['GET'])
def debug_routes():
    """Affiche toutes les routes disponibles"""
    routes = []
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith('/static/'):
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods - {'OPTIONS', 'HEAD'}),
                'rule': str(rule)
            })
    return jsonify({'routes': routes})

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
        .api-link { display: block; padding: 10px; background: #e9ecef; margin: 10px 0; border-radius: 5px; text-decoration: none; color: #333; }
        .api-link:hover { background: #dee2e6; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status-ok { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗳️ Système de Vote Scolaire 2026</h1>
        <div id="status" class="status">Chargement...</div>
        <p>Backend Flask fonctionnel. API disponibles :</p>
        <a href="/api/status" class="api-link">/api/status - Statut du système</a>
        <a href="/api/election" class="api-link">/api/election - Candidates</a>
        <a href="/api/test-db" class="api-link">/api/test-db - Test base de données</a>
        <a href="/admin-login" class="api-link">/admin-login - Administration</a>
        <a href="/api/debug/routes" class="api-link">/api/debug/routes - Toutes les routes</a>
    </div>
    <script>
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusDiv = document.getElementById('status');
                if (data.system && data.system.status === 'online') {
                    statusDiv.className = 'status status-ok';
                    statusDiv.innerHTML = `✅ Système en ligne | ${data.statistics.votes} votes | ${data.election.temps_restant} restants`;
                } else {
                    statusDiv.className = 'status status-warning';
                    statusDiv.innerHTML = '⚠️ Système hors ligne';
                }
            } catch (error) {
                document.getElementById('status').className = 'status status-warning';
                document.getElementById('status').innerHTML = '⚠️ Impossible de contacter le serveur';
            }
        }
        
        checkStatus();
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
'''

def fallback_admin_dashboard():
    # (Gardez votre code existant pour fallback_admin_dashboard)
    # C'est trop long à inclure ici, mais vous l'avez déjà dans votre code
    pass

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    # Initialiser la base de données
    print("🔧 Initialisation de la base de données...")
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
    print(f"📊 Test DB: http://localhost:{port}/api/test-db")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)