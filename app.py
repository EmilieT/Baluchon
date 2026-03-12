from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from config import Config
from models import db, User, Projet, Fichier, Evenement, Tache, ProjetUser, VisibiliteEnum, RoleEnum
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Initialisation de l'application Flask
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv('SECRET_KEY')

# Configuration de la base de données et des migrations
db.init_app(app)
migrate = Migrate(app, db)

# Configuration des uploads
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite à 16 Mo

# Initialisation de Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Gestion des erreurs
@login_manager.unauthorized_handler
def unauthorized():
    return render_template('401.html'), 401

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Enregistrement des routes
from routes.users import register_user_routes
register_user_routes(app)

from routes.projets import register_projet_routes
register_projet_routes(app)

from routes.environnement import register_environnement_routes
register_environnement_routes(app)

from scripts.dates import register_template_filters
register_template_filters(app)

from routes.dependances import register_dependances_routes
register_dependances_routes(app)

from routes.evenements import register_evenement_routes
register_evenement_routes(app)

from routes.fichiers import register_fichiers_routes
register_fichiers_routes(app)

from routes.taches import register_taches_routes
register_taches_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
