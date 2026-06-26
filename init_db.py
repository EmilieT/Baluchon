"""
Initialise une base de données Baluchon vierge avec toutes les tables.
À lancer une seule fois, à la première installation.

Usage :
    python init_db.py
"""
from app import app
from models import db

def main():
    with app.app_context():
        db.create_all()
        print("✅ Base de données initialisée : toutes les tables ont été créées.")
        print("   Vous pouvez maintenant créer votre compte avec : python create_admin.py")

if __name__ == '__main__':
    main()
