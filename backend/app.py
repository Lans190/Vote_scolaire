from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv


# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration PostgreSQL - Base : vote
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/vote')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2024')

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
            db.create_all()
            print("✅ Tables créées dans la base PostgreSQL 'vote'")
            
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
                print("✅ NOUVELLE ÉLECTION 2026 créée dans la base 'vote'")
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
                        photo_url=f"https://ui-avatars.com/api/?name={cand_data['prenom']}+{cand_data['nom']}&background=4361ee&color=fff"
                    )
                    db.session.add(candidate)
                
                db.session.commit()
                print(f"✅ {len(candidates_data)} candidates créées dans la base 'vote'")
            else:
                print(f"✅ Base 'vote' initialisée avec {candidates_count} candidates")
                print(f"📅 Date de début: {election.date_debut}")
                print(f"📅 Date de fin: {election.date_fin}")
            
            total_votes = Vote.query.count()
            print(f"📊 Total votes enregistrés : {total_votes}")
            
            # Afficher le statut actuel
            check_election_status(election)
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {str(e)}")
            import traceback
            traceback.print_exc()

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

@app.route('/')
def home():
    try:
        db_status = "connecté"
        election = Election.query.filter_by(statut='active').first()
        candidates_count = Candidate.query.count() if Candidate else 0
        votes_count = Vote.query.count() if Vote else 0
        
        if election:
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            election_info = f"{election.titre} - {election.get_temps_restant()}"
        else:
            election_info = "Aucune élection active"
            debut = fin = None
            
    except:
        db_status = "non connecté"
        election_info = "Erreur connexion"
        candidates_count = 0
        votes_count = 0
        debut = fin = None
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Vote Scolaire 2026</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.95);
                color: #333;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            }}
            h1 {{ 
                color: #4361ee; 
                margin-top: 0;
                border-bottom: 3px solid #4361ee;
                padding-bottom: 15px;
            }}
            .info-card {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 25px;
                border-radius: 12px;
                margin: 25px 0;
                border-left: 5px solid #7209b7;
            }}
            .time-info {{
                background: #e7f3ff;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                border: 2px dashed #4cc9f0;
            }}
            .endpoint {{
                background: white;
                padding: 20px;
                margin: 15px 0;
                border-radius: 10px;
                border-left: 5px solid #4361ee;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                transition: transform 0.2s;
            }}
            .endpoint:hover {{ transform: translateX(5px); }}
            code {{
                background: #e9ecef;
                padding: 4px 10px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }}
            a {{
                color: #4361ee;
                text-decoration: none;
                font-weight: bold;
            }}
            a:hover {{ text-decoration: underline; }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 25px 0;
            }}
            .stat-item {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            .stat-value {{
                font-size: 2em;
                font-weight: bold;
                color: #4361ee;
                display: block;
            }}
            .year-badge {{
                background: #f72585;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                display: inline-block;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 API Vote Scolaire <span class="year-badge">2026</span></h1>
            <div class="info-card">
                <h3>🗄️ Base de données : PostgreSQL • vote</h3>
                <p><strong>Statut :</strong> {db_status}</p>
                <p><strong>Élection :</strong> {election_info}</p>
            </div>
            
            <div class="time-info">
                <h3>⏰ Période de vote 2026 :</h3>
                <p><strong>Début :</strong> 8 février 2026, 00h00 GMT</p>
                <p><strong>Fin :</strong> 10 février 2026, 23h59 GMT</p>
                <p><strong>⚠️ Un seul vote par professeur</strong></p>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-value">{candidates_count}</span>
                    <span>Candidates</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{votes_count}</span>
                    <span>Votes</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">5</span>
                    <span>Classes</span>
                </div>
            </div>
            
            <h2>📡 Endpoints API :</h2>
            
            <div class="endpoint">
                <h3>GET <code>/api/election</code></h3>
                <p>Récupère l'élection active avec les 5 candidates</p>
                <a href="/api/election" target="_blank">Tester →</a>
            </div>
            
            <div class="endpoint">
                <h3>POST <code>/api/vote</code></h3>
                <p>Enregistre un vote (JSON requis)</p>
                <small><code>{{"professeur_email": "email@ecole.fr", "candidate_id": 1}}</code></small>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/results</code></h3>
                <p>Résultats en temps réel</p>
                <a href="/api/results" target="_blank">Tester →</a>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/stats</code></h3>
                <p>Statistiques détaillées</p>
                <a href="/api/stats" target="_blank">Tester →</a>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/status</code></h3>
                <p>Statut complet du système</p>
                <a href="/api/status" target="_blank">Tester →</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Retourne le statut complet du système"""
    try:
        election = Election.query.filter_by(statut='active').first()
        candidates_count = Candidate.query.count()
        votes_count = Vote.query.count()
        
        now = datetime.now(timezone.utc)
        status = "inactive"
        can_vote = False
        
        if election:
            debut = ensure_timezone(election.date_debut)
            fin = ensure_timezone(election.date_fin)
            
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
                'database': 'PostgreSQL • vote',
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
        if now < debut:
            return jsonify({'error': f'L\'élection n\'a pas encore commencé. Début: {debut.strftime("%d/%m/%Y %H:%M")} GMT'}), 400
        
        # Vérifier si l'élection est terminée
        if now > fin:
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
        candidate.votes_count += 1
        
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
        is_finished = now > fin
        
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
    """Statistiques détaillées - CORRIGÉ POUR LES TIMEZONES"""
    try:
        election = Election.query.filter_by(statut='active').first()
        if not election:
            return jsonify({'error': 'Aucune élection active'}), 404
        
        total_votes = Vote.query.filter_by(election_id=election.id).count()
        total_candidates = Candidate.query.filter_by(election_id=election.id).count()
        
        # CORRECTION : Utiliser timezone dans les requêtes
        now_utc = datetime.now(timezone.utc)
        today_utc = now_utc.date()
        
        # Votes par heure aujourd'hui - Version corrigée
        votes_by_hour = db.session.query(
            db.func.extract('hour', Vote.date_vote).label('hour'),
            db.func.count().label('count')
        ).filter(
            db.func.date(Vote.date_vote) == today_utc,
            Vote.election_id == election.id
        ).group_by('hour').order_by('hour').all()
        
        # Votes par candidate
        votes_by_candidate = db.session.query(
            Candidate.nom,
            Candidate.prenom,
            Candidate.classe,
            Candidate.votes_count
        ).filter(
            Candidate.election_id == election.id
        ).order_by(Candidate.votes_count.desc()).all()
        
        # Dernières 24 heures - Version corrigée
        yesterday_utc = now_utc - timedelta(hours=24)
        last_24h = db.session.query(
            db.func.count().label('count')
        ).filter(
            Vote.date_vote >= yesterday_utc,
            Vote.election_id == election.id
        ).scalar() or 0
        
        # Temps restant
        fin = ensure_timezone(election.date_fin)
        temps_restant = fin - now_utc if fin > now_utc else timedelta(0)
        
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
                'vote_actif': election.date_debut <= now_utc <= election.date_fin if election.date_debut and election.date_fin else False
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
        
        can_vote = debut <= now <= fin
        
        return jsonify({
            'has_voted': vote is not None,
            'email': email,
            'election_id': election.id,
            'election_title': election.titre,
            'can_vote': can_vote,
            'vote_period': f"{debut.strftime('%d/%m/%Y %H:%M')} GMT - {fin.strftime('%d/%m/%Y %H:%M')} GMT",
            'year': 2026
        })
    except Exception as e:
        print(f"❌ Erreur vérification email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-test', methods=['POST'])
def reset_test_data():
    """Réinitialise les données de test (uniquement pour le développement)"""
    try:
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
    print("🗄️  BASE DE DONNÉES : PostgreSQL • vote")
    print("=" * 80)
    
    # Initialiser la base de données
    init_database()
    
    print("=" * 80)
    print("📡 SERVEUR FLASK DÉMARRÉ")
    print("🌐 URL : http://localhost:5000")
    print("📋 API Élection  : http://localhost:5000/api/election")
    print("📊 API Résultats : http://localhost:5000/api/results")
    print("📈 API Statistiques : http://localhost:5000/api/stats")
    print("⚙️  API Status    : http://localhost:5000/api/status")
    print("=" * 80)
    print("⏰ PÉRIODE DE VOTE 2026 :")
    print("   Début : 8 février 2026, 00h00 GMT")
    print("   Fin   : 10 février 2026, 23h59 GMT")
    print("=" * 80)
    print("👨‍🏫 PRÊT POUR LES VOTES DES PROFESSEURS !")
    print("=" * 80)
    
    app.run(debug=True, port=5000, host='0.0.0.0')