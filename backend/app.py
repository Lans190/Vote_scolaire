from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import socket
import sys

# Charger les variables d'environnement
load_dotenv()

# Chemins - ADAPTÉ POUR RENDER
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_DIR, '..', 'front')

print(f"📁 Chemin frontend: {FRONTEND_PATH}")
print(f"📁 Existe: {os.path.exists(FRONTEND_PATH)}")

# Liste les fichiers si le dossier existe
if os.path.exists(FRONTEND_PATH):
    files = os.listdir(FRONTEND_PATH)
    print(f"📄 Fichiers dans front/: {files[:5]}...")
    if len(files) > 5:
        print(f"   + {len(files) - 5} autres fichiers")

app = Flask(__name__, static_folder=FRONTEND_PATH if os.path.exists(FRONTEND_PATH) else None)
CORS(app)

# ==================== CONFIGURATION BASE DE DONNÉES ====================

def fix_database_url_for_render(db_url):
    """Corrige l'URL de base de données pour Render"""
    if not db_url:
        return None
    
    print(f"🔍 Analyse URL DB: {db_url[:60]}...")
    
    # Conversion postgres:// → postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # CORRECTION SPÉCIFIQUE POUR RENDER : Ajout du domaine .render.com
    # Cherche le pattern dpg-xxxxxxx-a
    if 'dpg-' in db_url and '-a' in db_url and 'render.com' not in db_url:
        parts = db_url.split('@')
        if len(parts) == 2:
            host_part = parts[1].split('/')[0]
            if host_part.endswith('-a') and ':' not in host_part:
                # Ajouter .render.com et le port
                corrected_host = f"{host_part}.render.com:5432"
                db_url = db_url.replace(f"@{host_part}", f"@{corrected_host}")
                print(f"✅ URL corrigée pour Render: {db_url[:70]}...")
    
    # Vérifier qu'il y a bien un port
    if '@' in db_url and ':' not in db_url.split('@')[1].split('/')[0]:
        # Ajouter le port par défaut
        host_part = db_url.split('@')[1].split('/')[0]
        db_url = db_url.replace(f"@{host_part}", f"@{host_part}:5432")
        print(f"✅ Port 5432 ajouté: {db_url[:70]}...")
    
    return db_url

def test_database_connection(db_url):
    """Teste la connexion à la base de données"""
    if not db_url:
        return False
    
    try:
        # Extraire le hostname de l'URL
        if '@' in db_url:
            host_part = db_url.split('@')[1].split(':')[0].split('/')[0]
            
            print(f"🔍 Test de résolution DNS pour: {host_part}")
            try:
                ip_address = socket.gethostbyname(host_part)
                print(f"✅ DNS résolu: {host_part} → {ip_address}")
                return True
            except socket.gaierror as dns_error:
                print(f"❌ Échec DNS: {host_part}")
                print(f"   Erreur: {dns_error}")
                
                # Essayer avec différentes variations
                variations = [
                    host_part,
                    f"{host_part}.render.com",
                    host_part.replace('-a.', '-a.'),
                ]
                
                for variation in variations:
                    try:
                        ip = socket.gethostbyname(variation)
                        print(f"✅ Variation réussie: {variation} → {ip}")
                        return True
                    except:
                        continue
                
                return False
    except Exception as e:
        print(f"❌ Erreur lors du test de connexion: {e}")
        return False

# Obtenir et corriger l'URL de la base de données
database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/vote')

# URL spécifique fournie - À UTILISER SI LA VARIABLE D'ENVIRONNEMENT N'EST PAS DÉFINIE
if 'postgresql://' not in database_url or 'localhost' in database_url:
    # Utiliser l'URL fournie
    provided_url = "postgresql://vote_user:sVZxXHKa3RfuRfS2SkcSJUuIJ8C0KMpF@dpg-d64t7q24d50c73eo9nn0-a.render.com/vote_vq45"
    print(f"⚠️  Utilisation de l'URL fournie car DATABASE_URL n'est pas configurée")
    database_url = provided_url

# Corriger l'URL pour Render
original_url = database_url
database_url = fix_database_url_for_render(database_url)

if database_url != original_url:
    print(f"📝 URL originale: {original_url[:60]}...")
    print(f"🔧 URL corrigée: {database_url[:60]}...")

# Tester la connexion avant de configurer Flask
print("🔍 Test de connexion à la base de données...")
if test_database_connection(database_url):
    print("✅ Test de connexion réussi")
else:
    print("❌ Test de connexion échoué")
    print("💡 Vérifiez que:")
    print("   1. La base de données PostgreSQL existe sur Render")
    print("   2. Le nom d'hôte est correct (doit finir par .render.com)")
    print("   3. Les identifiants sont valides")

# Configuration Flask
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2026_vote_scolaire')

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
        db.Index('idx_votes_prof_email', 'professeur_email'),
        db.Index('idx_votes_date', 'date_vote'),
        db.Index('idx_votes_election_candidate', 'election_id', 'candidate_id')
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

# ==================== ROUTES POUR LE FRONTEND ====================

@app.route('/')
def index():
    """Page d'accueil - Redirige vers le frontend"""
    if os.path.exists(FRONTEND_PATH):
        return send_from_directory(FRONTEND_PATH, 'index.html')
    else:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Système de Vote Scolaire 2026</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                h1 { color: #4361ee; }
                .status { padding: 20px; margin: 20px; border-radius: 10px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .info { background: #d1ecf1; color: #0c5460; }
            </style>
        </head>
        <body>
            <h1>🚀 Système de Vote Scolaire 2026</h1>
            <div class="status info">
                <h2>API Backend Opérationnelle</h2>
                <p>Le serveur Flask fonctionne correctement.</p>
                <p>Frontend non trouvé dans le dossier /front</p>
            </div>
            <div class="status success">
                <h3>📡 API Disponible</h3>
                <p><a href="/api/status">/api/status</a> - Statut du système</p>
                <p><a href="/api/election">/api/election</a> - Élection active</p>
                <p><a href="/api/results">/api/results</a> - Résultats</p>
            </div>
            <p>© 2026 - Système de Vote Scolaire</p>
        </body>
        </html>
        '''

@app.route('/<path:path>')
def serve_frontend(path):
    """Sert les fichiers statiques du frontend"""
    if os.path.exists(FRONTEND_PATH):
        return send_from_directory(FRONTEND_PATH, path)
    else:
        return jsonify({'error': 'Frontend non disponible'}), 404

@app.route('/api/')
def api_docs():
    """Documentation de l'API"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Vote Scolaire 2026 - Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            code { background: #eee; padding: 2px 5px; }
            a { color: #4361ee; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>🗳️ API Vote Scolaire 2026</h1>
        <p><a href="/">← Retour à l'application</a></p>
        
        <div class="endpoint">
            <h3>GET <code>/api/status</code></h3>
            <p>Statut complet du système</p>
        </div>
        
        <div class="endpoint">
            <h3>GET <code>/api/election</code></h3>
            <p>Récupère l'élection active avec les candidats</p>
        </div>
        
        <div class="endpoint">
            <h3>POST <code>/api/vote</code></h3>
            <p>Enregistre un vote</p>
            <p>Body JSON: {"professeur_email": "email@ecole.fr", "candidate_id": 1}</p>
        </div>
        
        <div class="endpoint">
            <h3>GET <code>/api/results</code></h3>
            <p>Résultats en temps réel</p>
        </div>
        
        <div class="endpoint">
            <h3>GET <code>/api/stats</code></h3>
            <p>Statistiques détaillées</p>
        </div>
        
        <div class="endpoint">
            <h3>POST <code>/api/verify-email</code></h3>
            <p>Vérifie si un email a déjà voté</p>
            <p>Body JSON: {"email": "email@ecole.fr"}</p>
        </div>
        
        <div class="endpoint">
            <h3>POST <code>/api/reset-test</code></h3>
            <p>Réinitialise les données de test (développement seulement)</p>
        </div>
    </body>
    </html>
    '''

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
            print(f"🔗 Tentative de connexion à la base de données...")
            print(f"📊 URL: {database_url[:50]}...")  # Afficher partiellement pour sécurité
            
            # Créer les tables si elles n'existent pas
            db.create_all()
            print("✅ Tables créées/vérifiées avec succès")
            
            # Vérifier si une élection existe
            election = Election.query.filter_by(statut='active').first()
            
            if not election:
                # DATES EXACTES POUR 2026
                # Début : 8 février 2026, 00h00 GMT
                date_debut = datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
                
                # Fin : 10 février 2026, 23h59 GMT
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
                print("✅ NOUVELLE ÉLECTION 2026 créée")
                print(f"📅 Date de début: {date_debut}")
                print(f"📅 Date de fin: {date_fin}")
            
            # SI ÉLECTION EXISTE MAIS AVEC MAUVAISES DATES, CORRIGEZ-LA
            elif election.date_fin and election.date_fin.year == 2024:
                print("⚠️  Correction des dates de l'élection (2024 → 2026)...")
                
                # CORRECTION DES DATES POUR 2026
                date_debut = datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
                date_fin = datetime(2026, 2, 10, 23, 59, 59, tzinfo=timezone.utc)
                
                election.date_debut = date_debut
                election.date_fin = date_fin
                db.session.commit()
                
                print(f"✅ Dates corrigées pour 2026")
                print(f"📅 Nouvelle date de début: {date_debut}")
                print(f"📅 Nouvelle date de fin: {date_fin}")
            
            candidates_count = Candidate.query.filter_by(election_id=election.id).count()
            
            if candidates_count == 0:
                candidates_data = [
                    {'nom': 'Martin', 'prenom': 'Léa', 'classe': '6ème',
                     'description': 'Sérieuse, à l\'écoute, toujours prête à aider ses camarades. Projet : organiser des séances de tutorat entre élèves.'},
                    {'nom': 'Dubois', 'prenom': 'Thomas', 'classe': '5ème',
                     'description': 'Dynamique, créatif, bon communicateur. Projet : créer un journal scolaire numérique.'},
                    {'nom': 'Bernard', 'prenom': 'Emma', 'classe': '4ème',
                     'description': 'Organisée, impliquée dans la vie scolaire. Projet : améliorer l\'ambiance dans les couloirs.'},
                    {'nom': 'Petit', 'prenom': 'Lucas', 'classe': '3ème',
                     'description': 'Responsable, expérimenté. Projet : organiser des sessions de révision pour le brevet.'},
                    {'nom': 'Durand', 'prenom': 'Chloé', 'classe': '2nde',
                     'description': 'Mature, motivée. Projet : créer des activités inter-niveaux entre collège et lycée.'}
                ]
                
                for cand_data in candidates_data:
                    candidate = Candidate(
                        nom=cand_data['nom'],
                        prenom=cand_data['prenom'],
                        classe=cand_data['classe'],
                        description=cand_data['description'],
                        election_id=election.id,
                        photo_url=f"https://ui-avatars.com/api/?name={cand_data['prenom']}+{cand_data['nom']}&background=4361ee&color=fff&size=128"
                    )
                    db.session.add(candidate)
                
                db.session.commit()
                print(f"✅ {len(candidates_data)} candidates créées")
            else:
                print(f"✅ Base initialisée avec {candidates_count} candidates")
                print(f"📅 Date de début: {election.date_debut}")
                print(f"📅 Date de fin: {election.date_fin}")
            
            total_votes = Vote.query.count()
            print(f"📊 Total votes enregistrés : {total_votes}")
            
            # Afficher le statut actuel
            check_election_status(election)
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            print(f"💡 Vérifiez que:")
            print(f"   1. La base de données est accessible")
            print(f"   2. L'URL est correcte: {database_url[:60]}...")
            print(f"   3. Les identifiants sont valides")
            
            import traceback
            traceback.print_exc()
            
            # Retourner False pour indiquer l'échec
            return False

def check_election_status(election):
    """Vérifie et affiche le statut actuel de l'élection"""
    now = datetime.now(timezone.utc)
    
    debut = ensure_timezone(election.date_debut)
    fin = ensure_timezone(election.date_fin)
    
    if debut:
        if now < debut:
            diff = debut - now
            heures = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            print(f"⏳ L'élection débutera le: {debut.strftime('%d/%m/%Y %H:%M')} GMT")
            print(f"   Début dans: {diff.days}j {heures}h {minutes}m")
        else:
            print(f"✅ L'élection a commencé le: {debut.strftime('%d/%m/%Y %H:%M')} GMT")
    
    if fin:
        if now < fin:
            diff = fin - now
            jours = diff.days
            heures = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            print(f"⏰ Temps restant: {jours}j {heures}h {minutes}m")
            print(f"   Fin prévue: {fin.strftime('%d/%m/%Y %H:%M')} GMT")
        else:
            print(f"⏰ L'élection est terminée depuis: {fin.strftime('%d/%m/%Y %H:%M')} GMT")

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
        
        # Tester la connexion à la base de données
        db_status = "connected"
        try:
            db.session.execute("SELECT 1")
        except Exception as e:
            db_status = f"error: {str(e)[:50]}..."
        
        return jsonify({
            'system': {
                'status': 'online',
                'timestamp': now.isoformat(),
                'database': db_status,
                'environment': os.getenv('RENDER', 'development'),
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
            },
            'urls': {
                'frontend': '/',
                'api_docs': '/api/',
                'election': '/api/election',
                'results': '/api/results',
                'stats': '/api/stats'
            }
        })
    except Exception as e:
        print(f"❌ Erreur status: {str(e)}")
        return jsonify({
            'system': {
                'status': 'error',
                'error': str(e)[:100],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }), 500

@app.route('/api/election', methods=['GET'])
def get_election():
    """Récupère l'élection active avec vérification des dates"""
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        # Assurer les timezones
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        now = datetime.now(timezone.utc)
        
        # Vérifier si l'élection est en cours
        election_status = "active" if (debut and fin and debut <= now <= fin) else "pending" if (debut and now < debut) else "finished"
        
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        
        result = election.to_dict()
        result['candidates'] = [c.to_dict() for c in candidates]
        result['status'] = election_status
        result['can_vote'] = (debut and fin and debut <= now <= fin)
        
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur récupération élection: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    """Enregistre un nouveau vote avec vérification complète"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        print(f"📥 Données reçues: {data}")
        
        professeur_email = data.get('professeur_email')
        candidate_id = data.get('candidate_id')
        
        if not professeur_email:
            return jsonify({'error': 'professeur_email est requis'}), 400
        
        if not candidate_id:
            return jsonify({'error': 'candidate_id est requis'}), 400
        
        # Validation email
        if '@' not in professeur_email or '.' not in professeur_email:
            return jsonify({'error': 'Email invalide'}), 400
        
        # Convertir candidate_id en int
        try:
            candidate_id = int(candidate_id)
        except ValueError:
            return jsonify({'error': 'candidate_id doit être un nombre valide'}), 400
        
        # Vérifier si l'élection est active
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 400
        
        # Vérifier les dates de l'élection (avec timezones)
        now = datetime.now(timezone.utc)
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        
        print(f"🔍 Vérification dates 2026: Début={debut}, Maintenant={now}, Fin={fin}")
        
        # Vérifier si l'élection a commencé
        if debut and now < debut:
            return jsonify({'error': f'L\'élection n\'a pas encore commencé. Début: {debut.strftime("%d/%m/%Y %H:%M")} GMT'}), 400
        
        # Vérifier si l'élection est terminée
        if fin and now > fin:
            return jsonify({'error': f'L\'élection est terminée depuis le {fin.strftime("%d/%m/%Y %H:%M")} GMT'}), 400
        
        # Vérifier si le professeur a déjà voté
        print(f"🔍 Vérification vote existant pour: {professeur_email}")
        existing_vote = Vote.query.filter_by(
            election_id=election.id,
            professeur_email=professeur_email
        ).first()
        
        if existing_vote:
            print(f"❌ Email a déjà voté: {professeur_email}")
            return jsonify({'error': 'Ce professeur a déjà voté'}), 400
        
        # Vérifier si la candidate existe
        candidate = Candidate.query.filter_by(id=candidate_id, election_id=election.id).first()
        if not candidate:
            return jsonify({'error': 'Candidat non trouvé'}), 404
        
        # Créer le vote
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id,
            professeur_email=professeur_email,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        # Mettre à jour le compteur de votes
        candidate.votes_count = candidate.votes_count + 1
        
        db.session.add(vote)
        db.session.commit()
        
        print(f"✅ Vote 2026 enregistré pour {professeur_email} - Candidat: {candidate.prenom} {candidate.nom}")
        
        return jsonify({
            'success': True,
            'message': 'Vote enregistré avec succès',
            'vote': vote.to_dict(),
            'candidate': candidate.to_dict(),
            'election_status': 'Vote accepté',
            'votes_count': candidate.votes_count,
            'year': 2026
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors du vote: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Récupère les résultats du vote"""
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
                'percentage': round(percentage, 2),
                'rank': None
            })
        
        results.sort(key=lambda x: x['votes'], reverse=True)
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        # Vérifier si l'élection est terminée
        now = datetime.now(timezone.utc)
        fin = ensure_timezone(election.date_fin)
        is_finished = fin and now > fin
        
        return jsonify({
            'election': election.to_dict(),
            'total_votes': total_votes,
            'results': results,
            'is_finished': is_finished,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'year': 2026
        })
    except Exception as e:
        print(f"❌ Erreur résultats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Statistiques détaillées"""
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        total_candidates = Candidate.query.filter_by(election_id=election.id).count()
        
        now_utc = datetime.now(timezone.utc)
        today_utc = now_utc.date()
        
        # Votes par heure aujourd'hui
        votes_by_hour = []
        try:
            votes_by_hour = db.session.query(
                db.func.extract('hour', Vote.date_vote).label('hour'),
                db.func.count().label('count')
            ).filter(
                db.func.date(Vote.date_vote) == today_utc,
                Vote.election_id == election.id
            ).group_by('hour').order_by('hour').all()
        except:
            pass  # Ignorer si la requête échoue
        
        # Votes par candidate
        votes_by_candidate = []
        try:
            votes_by_candidate = db.session.query(
                Candidate.nom,
                Candidate.prenom,
                Candidate.classe,
                Candidate.votes_count
            ).filter(
                Candidate.election_id == election.id
            ).order_by(Candidate.votes_count.desc()).all()
        except:
            pass
        
        # Dernières 24 heures
        last_24h = 0
        try:
            yesterday_utc = now_utc - timedelta(hours=24)
            last_24h = db.session.query(
                db.func.count().label('count')
            ).filter(
                Vote.date_vote >= yesterday_utc,
                Vote.election_id == election.id
            ).scalar() or 0
        except:
            pass
        
        # Temps restant
        fin = ensure_timezone(election.date_fin)
        temps_restant = fin - now_utc if fin and fin > now_utc else timedelta(0)
        
        return jsonify({
            'election': election.to_dict(),
            'statistics': {
                'total_votes': total_votes,
                'total_candidates': total_candidates,
                'votes_last_24h': last_24h,
                'participation_rate': round((total_votes / 50 * 100), 2) if total_votes > 0 else 0,
                'temps_restant_jours': temps_restant.days,
                'temps_restant_heures': int(temps_restant.seconds // 3600),
                'votes_by_hour': [{'hour': int(hour), 'votes': count} for hour, count in votes_by_hour],
                'votes_by_candidate': [
                    {
                        'nom': nom,
                        'prenom': prenom,
                        'classe': classe,
                        'votes': votes
                    } for nom, prenom, classe, votes in votes_by_candidate
                ]
            },
            'periode_vote': {
                'date_debut': election.date_debut.isoformat() if election.date_debut else None,
                'date_fin': election.date_fin.isoformat() if election.date_fin else None,
                'vote_actif': election.date_debut and election.date_fin and (election.date_debut <= now_utc <= election.date_fin)
            },
            'year': 2026,
            'updated_at': now_utc.isoformat()
        })
    except Exception as e:
        print(f"❌ Erreur statistiques: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Vérifie si un email a déjà voté"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        vote = Vote.query.filter_by(
            election_id=election.id,
            professeur_email=email
        ).first()
        
        # Vérifier aussi si l'élection est en cours
        now = datetime.now(timezone.utc)
        debut = ensure_timezone(election.date_debut)
        fin = ensure_timezone(election.date_fin)
        
        can_vote = debut and fin and (debut <= now <= fin)
        
        return jsonify({
            'has_voted': vote is not None,
            'email': email,
            'election_id': election.id,
            'election_title': election.titre,
            'can_vote': can_vote,
            'vote_period': f"{debut.strftime('%d/%m/%Y %H:%M') if debut else 'N/A'} GMT - {fin.strftime('%d/%m/%Y %H:%M') if fin else 'N/A'} GMT",
            'year': 2026
        })
    except Exception as e:
        print(f"❌ Erreur vérification email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-test', methods=['POST'])
def reset_test_data():
    """Réinitialise les données de test (uniquement pour le développement)"""
    try:
        # Vérifier que nous ne sommes pas en production
        if os.getenv('RENDER') and 'production' in os.getenv('RENDER', '').lower():
            return jsonify({'error': 'Cette action n\'est pas autorisée en production'}), 403
        
        # Supprimer tous les votes
        Vote.query.delete()
        
        # Réinitialiser les compteurs de votes
        candidates = Candidate.query.all()
        for candidate in candidates:
            candidate.votes_count = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Données de test réinitialisées',
            'votes_deleted': True,
            'candidates_reset': len(candidates),
            'year': 2026
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 DÉMARRAGE DU SYSTÈME DE VOTE SCOLAIRE 2026")
    print("=" * 80)
    print("🗄️  BASE DE DONNÉES : PostgreSQL")
    print("=" * 80)
    
    # Initialiser la base de données
    db_initialized = init_database()
    
    if not db_initialized:
        print("❌ ATTENTION: Base de données non initialisée correctement")
        print("💡 L'application démarrera mais certaines fonctionnalités pourraient ne pas fonctionner")
    
    print("=" * 80)
    print("📡 SERVEUR FLASK DÉMARRÉ")
    
    # Obtenir le port de Render ou utiliser 10000
    port = int(os.getenv('PORT', 10000))
    
    print(f"🌐 Port d'écoute: {port}")
    print(f"📋 API Élection  : http://localhost:{port}/api/election")
    print(f"📊 API Résultats : http://localhost:{port}/api/results")
    print(f"📈 API Statistiques : http://localhost:{port}/api/stats")
    print(f"⚙️  API Status    : http://localhost:{port}/api/status")
    print("=" * 80)
    print("⏰ PÉRIODE DE VOTE 2026 :")
    print("   Début : 8 février 2026, 00h00 GMT")
    print("   Fin   : 10 février 2026, 23h59 GMT")
    print("=" * 80)
    print("👨‍🏫 PRÊT POUR LES VOTES DES PROFESSEURS !")
    print("=" * 80)
    
    app.run(debug=False, port=port, host='0.0.0.0')