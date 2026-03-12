from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, abort, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from models import RoleEnum, db, Projet, Fichier, Evenement, Tache, ProjetUser, User, VisibiliteEnum
from datetime import datetime
import os
import subprocess
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload
from scripts.lister_dependances import lister_dependances_par_fichier, lister_fichiers_par_dependance
from flask_login import UserMixin, current_user
from flask_login import LoginManager, login_required, logout_user   
from flask_login import login_user, current_user, logout_user   
from werkzeug.security import check_password_hash
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.exc import IntegrityError

from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import db, Projet, ProjetUser, Tache, Evenement, VisibiliteEnum  # Assure-toi d'importer VisibiliteEnum
from datetime import datetime

load_dotenv()  # Charge les variables d'environnement depuis le fichier .env

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv('SECRET_KEY')   
db.init_app(app)
migrate = Migrate(app, db)

### variables fichiers
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'r', 'rdata', 'rds'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Crée le dossier s'il n'existe pas
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite la taille des uploads à 16 Mo

# Initialisation des extensions
login_manager = LoginManager(app)  # Initialise Flask-Login


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Charge l'utilisateur pour Flask-Login


def get_unique_filename(upload_folder, filename):
    """Génère un nom de fichier unique en ajoutant un suffixe si nécessaire."""
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename

    while os.path.exists(os.path.join(upload_folder, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1

    return unique_filename
    
#
########### user management (inscription, connexion, déconnexion)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.')
    return render_template('login.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

################# Projets

# Accueil (Index des projets)
@app.route('/')
def index():
    if current_user.is_authenticated:
        # Récupère uniquement les projets associés à l'utilisateur via ProjetUser
        projets = [pu.projet for pu in current_user.projets if pu.projet and pu.projet.id]
    else:
        # Filtre uniquement les projets publics
        projets = Projet.query.filter_by(visibilite=VisibiliteEnum.PUBLIC).all()

    return render_template('index.html', projets=projets)



# Ajouter projet
@app.route('/ajouter_projet', methods=['GET', 'POST'])
@login_required
def ajouter_projet():
    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form.get('description', '')
        chemin_proj = request.form['chemin_proj']
        visibilite = request.form.get('visibilite', VisibiliteEnum.PRIVE.name)  # Utilise .name pour obtenir la valeur correcte

        # 1. Crée le projet avec le createur_id de l'utilisateur connecté
        projet = Projet(
            nom=nom,
            description=description,
            visibilite=VisibiliteEnum[visibilite],  # Convertit la chaîne en valeur d'énumération
            createur_id=current_user.id
        )
        db.session.add(projet)
        db.session.commit()

        # 2. Associe le projet à l'utilisateur connecté via ProjetUser
        env = ProjetUser(
            user_id=current_user.id,
            projet_id=projet.id,
            chemin_proj=chemin_proj,
            role=RoleEnum.ADMIN
        )
        db.session.add(env)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('ajouter_projet.html')

## erreur 401

@login_manager.unauthorized_handler
def unauthorized():
    # Redirige vers la page personnalisée 401
    return render_template('401.html'), 401


## éditer projet
from models import VisibiliteEnum  # Assure-toi d'importer VisibiliteEnum

@app.route('/projet/<int:projet_id>/editer', methods=['GET', 'POST'])
@login_required
def editer_projet(projet_id):
    # Vérifie que l'utilisateur est membre du projet
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()

    # Vérifie que l'utilisateur a le rôle MEMBRE ou ADMIN
    if projet_user.role not in [RoleEnum.ADMIN, RoleEnum.MEMBRE]:
        flash("Vous n'avez pas les droits pour éditer ce projet.", "danger")
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    projet = projet_user.projet

    if request.method == 'POST':
        projet.nom = request.form['nom']
        projet.description = request.form['description']

        # Seuls les ADMIN peuvent modifier la visibilité
        if projet_user.role == RoleEnum.ADMIN:
            visibilite = request.form.get('visibilite')
            if visibilite:
                projet.visibilite = VisibiliteEnum[visibilite]

        db.session.commit()
        flash('Les informations du projet ont été mises à jour.', 'success')
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    return render_template('editer_projet.html', projet=projet, projet_user=projet_user, VisibiliteEnum=VisibiliteEnum)


# editer environnement projet
@app.route('/projet/<int:projet_id>/changer-environnement', methods=['GET', 'POST'])
def changer_environnement(projet_id):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()

    if request.method == 'POST':
        projet_user.chemin_proj = request.form['chemin_proj']
        db.session.commit()

        flash('L\'environnement du projet a été mis à jour.', 'success')
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    return render_template('changer_environnement.html', projet_user=projet_user)

# Supprimer projet
@app.route('/projet/<int:projet_id>/supprimer', methods=['POST'])
@login_required
def supprimer_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()

    if projet_user.role != RoleEnum.ADMIN:
        flash("Vous n'avez pas les droits pour supprimer ce projet.", "danger")
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    try:
        db.session.delete(projet)
        db.session.commit()
        flash('Le projet a été supprimé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {e}', 'danger')

    return redirect(url_for('index'))


# Projet dashboard


@app.route('/projet/<int:projet_id>/dashboard')
@login_required
def projet_dashboard(projet_id):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet

    taches_non_terminees = Tache.query.filter(
        Tache.projet_id == projet_id,
        Tache.statut == 'à faire',
        db.or_(
            Tache.visibilite == VisibiliteEnum.PUBLIC,
            Tache.createur_id == current_user.id
        )
    ).all()

    evenements_a_venir = Evenement.query.filter(
        Evenement.projet_id == projet_id,
        Evenement.date >= datetime.utcnow(),
        db.or_(
            Evenement.visibilite == VisibiliteEnum.PUBLIC,
            Evenement.createur_id == current_user.id
        )
    ).order_by(Evenement.date).all()

    return render_template('projet_dashboard.html',
                           projet=projet,
                           projet_user=projet_user,
                           taches_non_terminees=taches_non_terminees,
                           evenements_a_venir=evenements_a_venir)

# dirname
@app.template_filter('dirname')
def dirname(path):
    return os.path.dirname(path)

# basenames
@app.template_filter('basename')
def basename(path):
    return os.path.basename(path)

# ouvrir projet
@app.route('/ouvrir_projet/<int:projet_id>')
@login_required
def ouvrir_projet(projet_id):
    # Vérifie que l'utilisateur est membre du projet
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    chemin_proj = os.path.abspath(projet_user.chemin_proj)

    # Ouvrir le fichier projet avec l'application par défaut
    try:
        if os.name == 'posix':  # macOS ou Linux
            subprocess.run(['open', chemin_proj], check=True)
        elif os.name == 'nt':   # Windows
            subprocess.run(['start', '', chemin_proj], shell=True, check=True)
        flash("Le projet a été ouvert avec succès.", "success")
    except subprocess.CalledProcessError as e:
        flash(f"Erreur lors de l'ouverture du projet : {e}", "danger")

    return redirect(url_for('projet_dashboard', projet_id=projet_id))


# ouvrir dossier
@app.route('/ouvrir_dossier/<int:projet_id>')
@login_required
def ouvrir_dossier(projet_id):
    # Récupère l'association ProjetUser pour obtenir le chemin
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))

    # Ouvrir le dossier avec le navigateur de fichiers
    if os.name == 'posix':  # macOS ou Linux
        subprocess.run(['open', dossier_projet])
    elif os.name == 'nt':   # Windows
        subprocess.run(['explorer', dossier_projet])

    return redirect(url_for('projet_dashboard', projet_id=projet_id))


# rapports html

@app.route('/projet/<int:projet_id>/rapports')
@login_required
def rapports_html(projet_id):
    # Vérifie que l'utilisateur est membre du projet
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet

    # Utilise le chemin du projet depuis ProjetUser
    fichiers_html = lister_fichiers_html_par_date(projet_user.chemin_proj)

    return render_template('rapports_html.html',
                          projet=projet,
                          fichiers_html=fichiers_html,
                          datetime=datetime)


## formater les dates
@app.template_filter('date')
def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

@app.template_filter('format_datetime')
def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """Format a datetime object."""
    if value is None:
        return ""
    return value.strftime(format)


# dépendances du projet (fichiers)
# scripts
@app.route('/projet/<int:projet_id>/dependances-par-fichier')
@login_required
def lister_dependances_par_fichier_route(projet_id):
    # Vérifie que l'utilisateur est membre du projet
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet

    # Utilise le chemin du projet depuis ProjetUser
    dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))

    fichiers_et_dependances = lister_dependances_par_fichier(dossier_projet)

    return render_template('dependances_par_fichier.html',
                          projet=projet,
                          fichiers_et_dependances=fichiers_et_dependances)

@app.route('/projet/<int:projet_id>/fichiers-par-dependance')
@login_required
def lister_fichiers_par_dependance_route(projet_id):
    # Vérifie que l'utilisateur est membre du projet
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet

    # Utilise le chemin du projet depuis ProjetUser
    dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))

    dependances_et_fichiers = lister_fichiers_par_dependance(dossier_projet)

    return render_template('fichiers_par_dependance.html',
                          projet=projet,
                          dependances_et_fichiers=dependances_et_fichiers)  
######### Evenements

# liste évènements
@app.route('/projet/<int:projet_id>/evenements')
def evenements(projet_id):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet  
    evenements = Evenement.query.filter_by(projet_id=projet_id).order_by(Evenement.date.desc()).all()
    return render_template('evenements.html', projet=projet, evenements=evenements, datetime=datetime)

# creer evenement
@app.route('/projet/<int:projet_id>/ajouter_evenement', methods=['GET', 'POST'])
@login_required
def ajouter_evenement(projet_id):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet

    if request.method == 'POST':
        # Logique pour ajouter l'événement
        type_evenement = request.form['type']
        date_evenement_str = request.form['date']
        contenu = request.form['contenu']
        date_evenement = datetime.strptime(date_evenement_str, '%Y-%m-%dT%H:%M')

        evenement = Evenement(
            type=type_evenement,
            date=date_evenement,
            contenu=contenu,
            projet_id=projet.id,
            createur_id=current_user.id  # Ajoute le createur_id
        )
        db.session.add(evenement)
        db.session.commit()

        # Gestion des tâches
        taches = request.form.getlist('taches[]')
        date_limites = request.form.getlist('date_limite[]')
        statuts = request.form.getlist('statuts[]')

        for i in range(len(taches)):
            if taches[i]:  # Vérifier que la description n'est pas vide
                date_limite = None
                if date_limites[i]:
                    date_limite = datetime.strptime(date_limites[i], '%Y-%m-%d').date()

                nouvelle_tache = Tache(
                    description=taches[i],
                    date_limite=date_limite,
                    statut=statuts[i],
                    projet_id=projet.id,
                    createur_id=current_user.id, 
                    evenement_id=evenement.id
                )
                db.session.add(nouvelle_tache)

        db.session.commit()

        # Redirection selon l'action choisie
        action = request.form.get('action')
        if action == 'ajouter_fichiers':
            return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))
        else:
            return redirect(url_for('evenements', projet_id=projet.id))

    return render_template('ajouter_evenement.html', projet=projet, datetime=datetime)


# afficher détail évènement
@app.route('/evenement/<int:evenement_id>')
def evenement_detail(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    projet_id = evenement.projet_id  # Récupérer l'ID du projet associé à cet événement
    return render_template('evenement_detail.html', evenement=evenement, projet_id=projet_id)

# Modifier évènement
@app.route('/evenement/<int:evenement_id>/modifier', methods=['GET', 'POST'])
def modifier_evenement(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)

    if request.method == 'POST':
        try:
            evenement.type = request.form['type']
            evenement.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
            evenement.contenu = request.form['contenu']

            if 'lien_fichier' in request.form:
                evenement.lien_fichier = request.form['lien_fichier'] if request.form['lien_fichier'] else None

            # Récupérer les tâches existantes
            taches_existantes = Tache.query.filter_by(evenement_id=evenement.id).all()

            # Mettre à jour ou ajouter les tâches
            tache_ids = request.form.getlist('tache_ids[]')
            taches = request.form.getlist('taches[]')
            date_limites = request.form.getlist('date_limite[]')

            for i in range(len(taches)):
                if taches[i]:
                    date_limite = None
                    if date_limites[i]:
                        date_limite = datetime.strptime(date_limites[i], '%Y-%m-%d').date()

                    if i < len(tache_ids) and tache_ids[i]:
                        # Mettre à jour une tâche existante
                        tache = Tache.query.get(tache_ids[i])
                        tache.description = taches[i]
                        tache.date_limite = date_limite
                    else:
                        # Ajouter une nouvelle tâche
                        nouvelle_tache = Tache(
                            description=taches[i],
                            date_limite=date_limite,
                            statut="à faire",
                            projet_id=evenement.projet_id,
                            createur_id=current_user.id,
                            evenement_id=evenement.id
                        )
                        db.session.add(nouvelle_tache)

            db.session.commit()
            flash('L\'événement a été modifié avec succès.', 'success')
            return redirect(url_for('evenement_detail', evenement_id=evenement.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
            app.logger.error(f"Erreur lors de la modification de l'événement {evenement_id}: {str(e)}")

    return render_template('modifier_evenement.html', evenement=evenement)

# supprimer évènement
@app.route('/evenement/<int:evenement_id>/supprimer', methods=['POST'])
def supprimer_evenement(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    projet_id = evenement.projet_id  # Conserve l'ID du projet pour la redirection

    # Supprime les fichiers associés sur le disque (optionnel)
    for fichier in evenement.fichiers:
        if os.path.exists(fichier.chemin):
            try:
                os.remove(fichier.chemin)
            except OSError as e:
                flash(f"Erreur lors de la suppression du fichier {fichier.nom} : {e}", "warning")

    # Supprime l'événement de la base de données
    db.session.delete(evenement)
    db.session.commit()

    flash('L\'événement a été supprimé avec succès.', 'success')
    return redirect(url_for('evenements', projet_id=projet_id))

###################################### Fichiers
# route fichiers
@app.route('/projet/<int:projet_id>/fichiers/<path:filename>')
def fichier(projet_id, filename):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_proj))
    return send_from_directory(dossier_projet, filename)

# servir fichier
@app.route('/fichier/<int:fichier_id>')
@app.route('/fichier/<int:fichier_id>/<action>')
def servir_fichier(fichier_id, action=None):
    fichier = Fichier.query.get_or_404(fichier_id)

    # Vérifie que le fichier existe
    if not os.path.exists(fichier.chemin):
        abort(404)

    # Vérifie que le fichier est bien dans le dossier uploads
    if not os.path.abspath(fichier.chemin).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
        abort(403)

    as_attachment = action == 'telecharger'

    # Détection du type MIME
    mimetypes = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'r': 'text/plain',
        'rdata': 'application/octet-stream',
        'rds': 'application/octet-stream'
    }

    extension = fichier.nom.rsplit('.', 1)[1].lower() if '.' in fichier.nom else ''
    mimetype = mimetypes.get(extension, 'application/octet-stream')

    return send_file(
        fichier.chemin,
        as_attachment=as_attachment,
        download_name=fichier.nom,
        mimetype=mimetype
    )

# taille fichier
@app.template_filter('filesizeformat')
def filesizeformat(value):
    """Format file size in human-readable format."""
    if value is None:
        return "0 octets"
    size = int(value)
    for unit in ['octets', 'Ko', 'Mo', 'Go']:
        if size < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} To"

# Supprimer fichier

@app.route('/fichier/<int:fichier_id>/supprimer', methods=['POST'])
def supprimer_fichier(fichier_id):
    fichier = Fichier.query.get_or_404(fichier_id)

    # Vérifie que le fichier existe sur le disque
    if os.path.exists(fichier.chemin):
        try:
            os.remove(fichier.chemin)  # Supprime le fichier du disque
        except OSError as e:
            flash(f"Erreur lors de la suppression du fichier : {e}", "danger")
            return redirect(url_for('modifier_evenement', evenement_id=fichier.evenement_id))

    # Supprime l'enregistrement de la base de données
    db.session.delete(fichier)
    db.session.commit()

    flash('Le fichier a été supprimé avec succès.', 'success')
    return redirect(url_for('modifier_evenement', evenement_id=fichier.evenement_id))

## fichiers
@app.route('/evenement/<int:evenement_id>/fichiers')
def gerer_fichiers(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    return render_template('gerer_fichiers.html', evenement=evenement)

## ajouter fichiers    
@app.route('/evenement/<int:evenement_id>/ajouter-fichiers', methods=['POST'])
def ajouter_fichiers(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    projet_id = evenement.projet_id

    if 'fichiers' not in request.files:
        flash('Aucun fichier sélectionné', 'warning')
        return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

    fichiers = request.files.getlist('fichiers')
    if not any(f.filename != '' for f in fichiers):
        flash('Aucun fichier valide sélectionné', 'warning')
        return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

    # Crée le sous-dossier du projet s'il n'existe pas
    dossier_projet = os.path.join(app.config['UPLOAD_FOLDER'], f"projet_{projet_id}")
    os.makedirs(dossier_projet, exist_ok=True)

    for fichier in fichiers:
        if fichier.filename != '' and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            filename = get_unique_filename(dossier_projet, filename)  # Utilise le dossier du projet

            # Sauvegarde le fichier dans le sous-dossier du projet
            chemin_fichier = os.path.join(dossier_projet, filename)
            fichier.save(chemin_fichier)

            # Crée l'enregistrement en base de données
            nouveau_fichier = Fichier(
                nom=filename,
                chemin=chemin_fichier,  # Stocke le chemin complet
                taille=os.path.getsize(chemin_fichier),  # Stocke la taille du fichier
                projet_id=projet_id,
                uploader_id=current_user.id,  # Assure-toi de passer l'uploader_id
                evenement_id=evenement.id
            )
            db.session.add(nouveau_fichier)

    db.session.commit()
    flash('Fichiers ajoutés avec succès!', 'success')
    return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

# Tous les fichiers
@app.route('/projet/<int:projet_id>/fichiers')
def tous_les_fichiers(projet_id):
    projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
    projet = projet_user.projet  
    # Charge les fichiers avec leur événement associé
    fichiers = Fichier.query.options(joinedload(Fichier.evenement)).filter_by(projet_id=projet_id).all()
    return render_template('tous_les_fichiers.html', projet=projet, tous_les_fichiers=fichiers)
    
######################## Tâches

STATUTS_TACHE = ['à faire', 'en cours', 'en attente', 'terminé']

# Ajouter une tâche
from flask import request, flash, redirect, url_for
from datetime import datetime

@app.route('/projet/<int:projet_id>/ajouter_tache', methods=['POST'])
@login_required
def ajouter_tache(projet_id):
    projet = Projet.query.get_or_404(projet_id)

    # Vérifier que l'utilisateur est membre du projet ou le créateur
    is_member = any(membre.user_id == current_user.id for membre in projet.membres)
    if not is_member and projet.createur_id != current_user.id:
        abort(403)

    description = request.form['description']
    date_limite_str = request.form.get('date_limite')
    evenement_id = request.form.get('evenement_id', type=int)

    date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d').date() if date_limite_str else None

    # Récupérer la visibilité depuis le formulaire
    visibilite_str = request.form.get('visibilites[]', 'prive')  # Valeur par défaut : 'prive'

    # Convertir la visibilité en enum
    visibilite = VisibiliteEnum(visibilite_str)

    if not evenement_id:
        # Créer un événement par défaut
        evenement = Evenement(
            type="création_tâche",
            date=datetime.utcnow(),
            contenu=f"Création de la tâche: {description}",
            projet_id=projet_id,
            createur_id=current_user.id
        )
        db.session.add(evenement)
        db.session.commit()
        evenement_id = evenement.id

    # Créer la tâche avec le createur_id et la visibilité
    tache = Tache(
        description=description,
        statut="à faire",
        date_limite=date_limite,
        projet_id=projet_id,
        createur_id=current_user.id,
        visibilite=visibilite,  # Utiliser l'enum de visibilité
        evenement_id=evenement_id
    )
    db.session.add(tache)
    db.session.commit()

    flash('Tâche ajoutée avec succès.', 'success')
    return redirect(request.referrer or url_for('projet_dashboard', projet_id=projet_id))

# changer visibilite tâche
@app.route('/tache/<int:tache_id>/changer_visibilite', methods=['POST'])
@login_required
def changer_visibilite(tache_id):
    tache = Tache.query.get_or_404(tache_id)

    # Vérifier que l'utilisateur est le créateur de la tâche ou un administrateur du projet
    projet = tache.projet
    is_admin_or_creator = (tache.createur_id == current_user.id) or any(
        membre.user_id == current_user.id and membre.role == RoleEnum.ADMIN
        for membre in projet.membres
    )
    if not is_admin_or_creator:
        abort(403)

    # Récupérer la nouvelle visibilité
    nouvelle_visibilite_str = request.form.get('visibilite')

    # Valider la nouvelle visibilité
    if nouvelle_visibilite_str not in [visibilite.value for visibilite in VisibiliteEnum]:
        flash('Visibilité invalide.', 'danger')
        return redirect(request.referrer)

    # Mettre à jour la visibilité
    tache.visibilite = VisibiliteEnum(nouvelle_visibilite_str)
    db.session.commit()

    flash('Visibilité mise à jour.', 'success')
    return redirect(request.referrer)

# Changer le statut tâche
@app.route('/tache/<int:tache_id>/changer_statut', methods=['POST'])
def changer_statut(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    nouveau_statut = request.form.get('statut')

    if nouveau_statut in STATUTS_TACHE:
        tache.statut = nouveau_statut
        tache.date_cloture = datetime.utcnow() if nouveau_statut == 'terminé' else None
        db.session.commit()
        flash('Statut de la tâche mis à jour.', 'success')
    else:
        flash('Statut invalide.', 'danger')

    # Rediriger vers la page précédente
    return redirect(request.referrer or url_for('toutes_les_taches', projet_id=projet_id))
         
# Supprimer une tâche
@app.route('/tache/<int:tache_id>/supprimer', methods=['POST'])
def supprimer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    projet_id = tache.projet_id
    db.session.delete(tache)
    db.session.commit()
    flash('Tâche supprimée avec succès.', 'success')
    return redirect(url_for('toutes_les_taches', projet_id=projet_id))
    
    
# Toutes les tâches → toutes les tâches du projet
@app.route('/projet/<int:projet_id>/toutes_les_taches')
def toutes_les_taches(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    toutes_les_taches = Tache.query.filter_by(projet_id=projet_id).order_by(Tache.date_creation.desc()).all()
    return render_template('toutes_les_taches.html', projet=projet, toutes_les_taches=toutes_les_taches)
     
# Editer une tâche
@app.route('/tache/<int:tache_id>/editer', methods=['GET', 'POST'])
def editer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)

    if request.method == 'POST':
        tache.description = request.form['description']
        date_limite_str = request.form.get('date_limite')
        tache.date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d') if date_limite_str else None
        tache.statut = request.form['statut']

        if tache.statut == 'terminé' and not tache.date_cloture:
            tache.date_cloture = datetime.utcnow()
        elif tache.statut != 'terminé' and tache.date_cloture:
            tache.date_cloture = None

        db.session.commit()
        flash('Tâche modifiée avec succès.', 'success')

        # Redirection vers la page précédente
        return redirect(request.referrer)

    return render_template('editer_tache.html', tache=tache)
   

################### Users

# profil utilisateur
@app.route('/utilisateur/<int:user_id>')
@login_required
def voir_profil(user_id):
    utilisateur = User.query.get_or_404(user_id)
    return render_template('profil.html', utilisateur=utilisateur)

# utilisateurs


@app.route('/utilisateurs')
@login_required
def liste_utilisateurs():
    # Récupérer tous les utilisateurs
    utilisateurs = User.query.all()
    return render_template('utilisateurs.html', utilisateurs=utilisateurs)


@app.route('/projet/<int:projet_id>/inviter', methods=['GET', 'POST'])
@login_required
def inviter_utilisateur(projet_id):
    projet = Projet.query.get_or_404(projet_id)

    # Vérifier que l'utilisateur actuel est membre du projet
    is_member = any(membre.user_id == current_user.id for membre in projet.membres)
    if not is_member and projet.createur_id != current_user.id:
        abort(403)

    # Récupérer tous les utilisateurs
    utilisateurs = User.query.all()

    if request.method == 'POST':
        username = request.form.get('username')  # Utiliser le username au lieu de l'email
        role = request.form.get('role', RoleEnum.MEMBRE.value)

        # Trouver l'utilisateur par username
        utilisateur = User.query.filter_by(username=username).first()

        if not utilisateur:
            flash('Aucun utilisateur trouvé avec ce nom.', 'danger')
            return redirect(url_for('inviter_utilisateur', projet_id=projet_id))

        # Vérifier que l'utilisateur n'est pas déjà membre du projet
        if any(membre.user_id == utilisateur.id for membre in projet.membres):
            flash('Cet utilisateur est déjà membre du projet.', 'warning')
            return redirect(url_for('inviter_utilisateur', projet_id=projet_id))

        # Ajouter l'utilisateur au projet avec le rôle
        membre = ProjetUser(
            user_id=utilisateur.id,
            projet_id=projet_id,
            role=RoleEnum(role),
            chemin_proj=f"/chemin/par/defaut/{projet.nom}/{utilisateur.username}"
        )
        db.session.add(membre)
        db.session.commit()

        flash(f'{utilisateur.username} a été ajouté au projet avec le rôle {role}.', 'success')
        return redirect(url_for('editer_projet', projet_id=projet_id))

    # Récupérer les rôles disponibles pour le formulaire
    roles = [(role.value, role.name) for role in RoleEnum]

    return render_template('inviter_utilisateur.html', projet=projet, roles=roles, utilisateurs=utilisateurs)


# fonction lister fichiers

def lister_fichiers_html_par_date(chemin_proj):
    dossier_projet = os.path.dirname(os.path.abspath(chemin_proj))
    fichiers_html = []

    for racine, dirs, fichiers_dans_dossier in os.walk(dossier_projet):
        # Ignorer les dossiers cachés ou spécifiques comme .Rproj.user
        if '.Rproj.user' in racine:
            continue

        for fichier in fichiers_dans_dossier:
            if fichier.endswith('.html') and not fichier.startswith('._') and not fichier.startswith('.'):
                chemin_complet = os.path.join(racine, fichier)
                chemin_relatif = os.path.relpath(chemin_complet, start=dossier_projet)
                date_modification = os.path.getmtime(chemin_complet)
                fichiers_html.append((fichier, chemin_relatif, date_modification))

    # Trier les fichiers par date de modification (du plus récent au plus ancien)
    fichiers_html.sort(key=lambda x: x[2], reverse=True)

    return fichiers_html
    


def migrer_fichiers():
    fichiers = Fichier.query.all()
    for fichier in fichiers:
        ancien_chemin = fichier.chemin
        projet_id = fichier.projet_id
        nouveau_dossier = os.path.join(app.config['UPLOAD_FOLDER'], f"projet_{projet_id}")
        os.makedirs(nouveau_dossier, exist_ok=True)
        nouveau_chemin = os.path.join(nouveau_dossier, fichier.nom)

        if os.path.exists(ancien_chemin):
            try:
                os.rename(ancien_chemin, nouveau_chemin)
                fichier.chemin = nouveau_chemin  # Met à jour le chemin en base de données
                db.session.commit()
            except Exception as e:
                print(f"Erreur lors de la migration du fichier {fichier.nom}: {e}")
                
if __name__ == '__main__':
    app.run(debug=True)
