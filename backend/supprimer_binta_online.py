import psycopg2
import os

# Connexion à la base Render
conn = psycopg2.connect(
    host="dpg-d64t7q24d50c73eo9nn0-a.frankfurt-postgres.render.com",
    database="vote_vq45",
    user="vote_user",
    password="sVZxXHKa3RfuRfS2SkcSJUuIJ8C0KMpF",
    port=5432
)

cur = conn.cursor()

# Supprimer les votes de Binta d'abord
cur.execute("DELETE FROM vote WHERE candidate_id = (SELECT id FROM candidate WHERE nom = 'Diallo' AND prenom = 'Binta');")

# Supprimer Binta
cur.execute("DELETE FROM candidate WHERE nom = 'Diallo' AND prenom = 'Binta';")

conn.commit()
print("✅ Binta Diallo supprimée de la base en ligne !")

# Vérification
cur.execute("SELECT * FROM candidate;")
rows = cur.fetchall()
print("\n📊 Candidates restantes :")
for row in rows:
    print(f"   - {row[2]} {row[1]} ({row[3]})")  # prénom, nom, classe

cur.close()
conn.close()