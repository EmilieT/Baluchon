"""
Crée (ou met à jour) le compte unique de connexion à Baluchon.
À exécuter après la migration, avant le premier lancement avec gunicorn.

Usage :
    python create_admin.py
"""
import getpass
from app import app
from models import db, User

def main():
    with app.app_context():
        username = input("Identifiant souhaité : ").strip()
        if not username:
            print("Identifiant vide, abandon.")
            return

        password = getpass.getpass("Mot de passe : ")
        password2 = getpass.getpass("Confirmer le mot de passe : ")
        if password != password2:
            print("Les mots de passe ne correspondent pas. Abandon.")
            return
        if len(password) < 6:
            print("Le mot de passe doit faire au moins 6 caractères.")
            return

        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(password)
            db.session.commit()
            print(f"✓ Mot de passe mis à jour pour '{username}'.")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"✓ Compte '{username}' créé avec succès.")

if __name__ == '__main__':
    main()
