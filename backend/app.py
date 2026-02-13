from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
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
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app, supports_credentials=True)

# ==================== CONFIGURATION BASE DE DONNÉES ====================

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
    'pool_size': 5,
    'max_overflow': 10
}

db = SQLAlchemy(app)

# ==================== FORCE LA CRÉATION DES TABLES ====================
with app.app_context():
    try:
        print("=" * 50)
        print("🔧 CRÉATION FORCÉE DES TABLES POSTGRESQL")
        print("=" * 50)
        
        # Supprimer les tables existantes (optionnel - à utiliser avec précaution)
        # db.drop_all()
        # print("✅ Tables existantes supprimées")
        
        # Créer les tables
        db.create_all()
        print("✅ Tables créées avec succès !")
        
        # Vérifier que les tables existent
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Tables dans la base : {tables}")
        
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE : {e}")
        import traceback
        traceback.print_exc()

# ==================== MODÈLES DE BASE DE DONNÉES ====================

class Election(db.Model):
    __tablename__ = 'election'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    date_debut = db.Column(db.DateTime(timezone=True))
    date_fin = db.Column(db.DateTime(timezone=True))
    statut = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    candidates = db.relationship('Candidate', backref='election', lazy=True)
    votes = db.relationship('Vote', backref='election', lazy=True)

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
            election = db.session.get(Election, 1)
            if not election:
                election = Election.query.first()
            
            if not election:
                print("📝 Création de l'élection par défaut...")
                election = Election(
                    titre="Élection des Délégués Élèves 2026",
                    date_debut=datetime(2026, 2, 10, 0, 0, 0, tzinfo=timezone.utc),
                    date_fin=datetime(2026, 3, 15, 23, 59, 59, tzinfo=timezone.utc),
                    statut='active'
                )
                db.session.add(election)
                db.session.flush()
                
                # Créer les candidates
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
                print(f"✅ Élection et {len(candidates_data)} candidates créées")
            else:
                print(f"✅ Élection existante: {election.titre}")
                
                # Vérifier s'il y a des candidates
                if Candidate.query.filter_by(election_id=election.id).count() == 0:
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
    try:
        return send_from_directory(FRONTEND_PATH, 'index.html')
    except:
        return fallback_index()

@app.route('/admin')
def admin_redirect():
    return redirect('/admin-login')

@app.route('/admin-login')
def admin_login():
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
    try:
        return send_from_directory(FRONTEND_PATH, 'admin-dashboard.html')
    except:
        return "Tableau de bord admin - Interface non trouvée"

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(FRONTEND_PATH, path)
    except:
        return jsonify({'error': 'Fichier non trouvé'}), 404

# ==================== API PUBLIQUE ====================

@app.route('/api/status', methods=['GET'])
def api_status():
    try:
        election = Election.query.first()
        votes_count = Vote.query.count()
        candidates_count = Candidate.query.count()
        
        now = datetime.now(timezone.utc)
        
        # Calcul du temps restant
        temps_restant = "En cours"
        can_vote = False
        election_status = "inactive"
        election_title = "Non configurée"
        
        if election:
            election_status = election.statut
            election_title = election.titre
            
            if election.date_fin:
                fin = election.date_fin
                if fin.tzinfo is None:
                    fin = fin.replace(tzinfo=timezone.utc)
                diff = fin - now
                if diff.total_seconds() > 0:
                    jours = diff.days
                    heures = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    temps_restant = f"{jours}j {heures:02d}h {minutes:02d}m"
                    can_vote = election.statut == 'active'
                else:
                    temps_restant = "Terminé"
                    can_vote = False
                    if election.statut == 'active':
                        election.statut = 'closed'
                        db.session.commit()
        
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
                'status': election_status,
                'titre': election_title,
                'temps_restant': temps_restant,
                'can_vote': can_vote
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
    try:
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection configurée'}), 404
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        
        avatar_colors = ['#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0']
        
        candidates_list = []
        for candidate in candidates:
            initials = f"{candidate.prenom[0]}{candidate.nom[0]}"
            color = avatar_colors[candidate.id % len(avatar_colors)]
            
            candidates_list.append({
                'id': candidate.id,
                'nom': candidate.nom,
                'prenom': candidate.prenom,
                'nom_complet': candidate.nom_complet,
                'classe': candidate.classe,
                'description': candidate.description or f"Candidate pour la classe de {candidate.classe}",
                'votes_count': candidate.votes_count,
                'avatar_color': color,
                'initials': initials
            })
        
        return jsonify({
            'status': election.statut,
            'title': election.titre,
            'candidates': candidates_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
def api_verify_email():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({'error': 'Email valide requis'}), 400
        
        election = Election.query.first()
        if not election or election.statut != 'active':
            return jsonify({
                'has_voted': False,
                'can_vote': False,
                'message': 'L\'élection n\'est pas active'
            })
        
        existing_vote = Vote.query.filter_by(
            professeur_email=email,
            election_id=election.id
        ).first()
        
        if existing_vote:
            return jsonify({
                'has_voted': True,
                'can_vote': False,
                'message': 'Vous avez déjà voté'
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
        
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection configurée'}), 404
            
        if election.statut != 'active':
            return jsonify({'error': 'L\'élection n\'est plus active'}), 400
        
        existing_vote = Vote.query.filter_by(
            professeur_email=email,
            election_id=election.id
        ).first()
        
        if existing_vote:
            return jsonify({'error': 'Vous avez déjà voté'}), 400
        
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate non trouvée'}), 404
        
        if candidate.election_id != election.id:
            return jsonify({'error': 'Candidate ne fait pas partie de cette élection'}), 400
        
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id,
            professeur_email=email,
            ip_address=request.remote_addr
        )
        
        candidate.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Votre vote a été enregistré avec succès',
            'confirmation_id': f'VOTE-{vote.id:06d}',
            'candidate': candidate.nom_complet,
            'classe': candidate.classe
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== API ADMIN ====================

@app.route('/api/results', methods=['GET'])
def api_results():
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        
        results = []
        for candidate in candidates:
            candidate_votes = Vote.query.filter_by(
                election_id=election.id,
                candidate_id=candidate.id
            ).count()
            
            percentage = (candidate_votes / total_votes * 100) if total_votes > 0 else 0
            
            results.append({
                'id': candidate.id,
                'nom_complet': candidate.nom_complet,
                'classe': candidate.classe,
                'votes': candidate_votes,
                'percentage': round(percentage, 2)
            })
        
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return jsonify({
            'election': election.titre,
            'total_votes': total_votes,
            'candidates_count': len(candidates),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        votes = Vote.query.filter_by(election_id=election.id)\
                         .order_by(Vote.date_vote.desc())\
                         .limit(50).all()
        
        recent_voters = []
        for vote in votes:
            candidate = db.session.get(Candidate, vote.candidate_id)
            email = vote.professeur_email
            if '@' in email:
                parts = email.split('@')
                masked_email = parts[0][:3] + '***@' + parts[1]
            else:
                masked_email = email[:3] + '***'
            
            recent_voters.append({
                'email': masked_email,
                'date_vote': vote.date_vote.isoformat() if vote.date_vote else None,
                'candidate_nom': candidate.nom_complet if candidate else 'N/A'
            })
        
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        total_candidates = Candidate.query.filter_by(election_id=election.id).count()
        
        return jsonify({
            'election': election.titre,
            'total_votes': total_votes,
            'total_candidates': total_candidates,
            'recent_voters': recent_voters,
            'last_update': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-votes', methods=['POST'])
def reset_votes():
    admin_secret = request.args.get('admin_secret') or (request.json.get('admin_secret') if request.json else None)
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        votes_count = Vote.query.filter_by(election_id=election.id).count()
        Vote.query.filter_by(election_id=election.id).delete()
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        for candidate in candidates:
            candidate.votes_count = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{votes_count} votes réinitialisés'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-user', methods=['POST'])
def reset_user_vote():
    admin_secret = request.args.get('admin_secret') or (request.json.get('admin_secret') if request.json else None)
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        vote = Vote.query.filter_by(
            election_id=election.id,
            professeur_email=email
        ).first()
        
        if not vote:
            return jsonify({'error': 'Vote non trouvé'}), 404
        
        candidate = db.session.get(Candidate, vote.candidate_id)
        if candidate and candidate.votes_count > 0:
            candidate.votes_count -= 1
        
        db.session.delete(vote)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Vote de {email} réinitialisé'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/extend-election', methods=['POST'])
def extend_election():
    admin_secret = request.args.get('admin_secret') or (request.json.get('admin_secret') if request.json else None)
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        data = request.json
        days_to_add = data.get('days', 7)
        
        election = Election.query.first()
        if not election:
            return jsonify({'error': 'Aucune élection trouvée'}), 404
        
        if election.date_fin:
            new_end_date = election.date_fin + timedelta(days=days_to_add)
        else:
            new_end_date = datetime.now(timezone.utc) + timedelta(days=days_to_add)
        
        election.date_fin = new_end_date
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Élection prolongée de {days_to_add} jours',
            'new_end_date': new_end_date.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== ROUTES DE TEST ====================

@app.route('/api/test-db', methods=['GET'])
def test_db():
    """Test de connexion à la base de données"""
    try:
        result = db.session.execute('SELECT version()').fetchone()
        version = result[0] if result else 'Unknown'
        
        candidates = Candidate.query.count()
        votes = Vote.query.count()
        
        return jsonify({
            'status': 'OK',
            'database': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'version': version[:100],
            'candidates': candidates,
            'votes': votes,
            'persistent': bool(DATABASE_URL),
            'message': '✅ Base de données fonctionne correctement !'
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'database_url_exists': 'DATABASE_URL' in os.environ
        }), 500

@app.route('/api/admin/db-status', methods=['GET'])
def db_status():
    admin_secret = request.args.get('admin_secret')
    
    if admin_secret != 'admin2026':
        return jsonify({'error': 'Accès refusé'}), 403
    
    try:
        db.session.execute('SELECT 1')
        
        candidates = Candidate.query.count()
        votes = Vote.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'persistent': bool(DATABASE_URL),
            'stats': {
                'candidates': candidates,
                'votes': votes
            },
            'database_url_exists': 'DATABASE_URL' in os.environ
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# ==================== FALLBACK ====================

def fallback_index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Système de Vote 2026</title>
    <style>
        body { font-family: Arial; padding: 20px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 20px; color: #333; }
        h1 { color: #4361ee; }
        .api-link { display: block; padding: 10px; background: #e9ecef; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗳️ Système de Vote Scolaire 2026</h1>
        <p>Backend Flask - Statut: ✅ En ligne</p>
        <a href="/api/test-db" class="api-link">🔍 Tester la base de données</a>
        <a href="/api/status" class="api-link">📊 Statut du système</a>
        <a href="/admin-login" class="api-link">🔐 Administration</a>
    </div>
</body>
</html>
'''

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    with app.app_context():
        # Vérifier la connexion DB
        if DATABASE_URL:
            try:
                db.session.execute('SELECT 1')
                print("✅ Connexion PostgreSQL vérifiée")
            except Exception as e:
                print(f"❌ Erreur connexion PostgreSQL: {e}")
        
        # Initialiser la base
        init_database()
    
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Serveur démarré sur le port {port}")
    print(f"🌐 http://localhost:{port}")
    print(f"🔐 Admin: http://localhost:{port}/admin-login")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)