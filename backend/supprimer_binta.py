from app import app, db, Candidate, Vote

with app.app_context():
    # Trouver Binta
    binta = Candidate.query.filter_by(nom='Diallo', prenom='Binta').first()
    
    if binta:
        # Supprimer ses votes d'abord
        Vote.query.filter_by(candidate_id=binta.id).delete()
        # Supprimer Binta
        db.session.delete(binta)
        db.session.commit()
        print("✅ Binta Diallo supprimée !")
    else:
        print("ℹ️ Binta n'existe pas dans la base")
    
    # Afficher les candidates restantes
    candidates = Candidate.query.all()
    for c in candidates:
        print(f"✅ {c.nom_complet} - {c.classe}")