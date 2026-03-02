from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, abort, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from models import db, Projet, Fichier, Evenement, Tache
from datetime import datetime
import os
import subprocess
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from scripts.lister_dependances import lister_dependances_par_fichier, lister_fichiers_par_dependance



app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)

### variables fichiers
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'r', 'rdata', 'rds'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Crée le dossier s'il n'existe pas
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite la taille des uploads à 16 Mo

def get_unique_filename(upload_folder, filename):
    """Génère un nom de fichier unique en ajoutant un suffixe si nécessaire."""
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename

    while os.path.exists(os.path.join(upload_folder, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1

    return unique_filename
    
################# Projets

# Accueil (Index des projets)
@app.route('/')
def index():
    projets = Projet.query.all()
    return render_template('index.html', projets=projets)

# Ajouter projet
@app.route('/ajouter_projet', methods=['GET', 'POST'])
def ajouter_projet():
    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form['description']
        chemin_rproj = request.form['chemin_rproj']
        projet = Projet(
            nom=nom,
            description=description,
            chemin_rproj=chemin_rproj
        )
        db.session.add(projet)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('ajouter_projet.html')


# editer projet    
@app.route('/projet/<int:projet_id>/editer', methods=['GET', 'POST'])
def editer_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)

    if request.method == 'POST':
        projet.nom = request.form['nom']
        projet.description = request.form['description']
        projet.chemin_rproj = request.form['chemin_rproj']

        db.session.commit()

        flash('Les informations du projet ont été mises à jour dans Baluchon.', 'success')
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    return render_template('editer_projet.html', projet=projet)


# Supprimer projet
@app.route('/projet/<int:projet_id>/supprimer', methods=['POST'])
def supprimer_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)

    # Supprimer le projet de la base de données
    db.session.delete(projet)
    db.session.commit()

    flash('Le projet a été supprimé de Baluchon.', 'success')
    return redirect(url_for('index'))

# Projet dashboard
@app.route('/projet/<int:projet_id>/dashboard')
def projet_dashboard(projet_id):
    projet = Projet.query.get_or_404(projet_id)

    # Récupérer les tâches non terminées pour le projet
    taches_non_terminees = Tache.query.filter_by(projet_id=projet_id).filter(Tache.statut != 'terminé').order_by(Tache.date_limite.asc()).all()

    # Récupérer les événements à venir pour le projet
    evenements_a_venir = Evenement.query.filter_by(projet_id=projet_id).filter(Evenement.date >= datetime.utcnow()).order_by(Evenement.date.asc()).limit(5).all()

    return render_template(
        'projet_dashboard.html',
        projet=projet,
        taches_non_terminees=taches_non_terminees,
        evenements_a_venir=evenements_a_venir
    )

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
def ouvrir_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    chemin_rproj = os.path.abspath(projet.chemin_rproj)

    # Ouvrir le fichier projet avec l'application par défaut
    if os.name == 'posix':  # macOS ou Linux
        subprocess.run(['open', chemin_rproj])
    elif os.name == 'nt':   # Windows
        subprocess.run(['start', '', chemin_rproj])

    return redirect(url_for('projet_dashboard', projet_id=projet_id))



# ouvrir dossier
@app.route('/ouvrir_dossier/<int:projet_id>')
def ouvrir_dossier(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))

    # Ouvrir le dossier avec le navigateur de fichiers
    if os.name == 'posix':  # macOS ou Linux
        subprocess.run(['open', dossier_projet])
    elif os.name == 'nt':   # Windows
        subprocess.run(['explorer', dossier_projet])

    return redirect(url_for('projet_dashboard', projet_id=projet_id))



# rapports html

@app.route('/projet/<int:projet_id>/rapports')
def rapports_html(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    fichiers_html = lister_fichiers_html_par_date(projet.chemin_rproj)
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
@app.route('/scripts/<path:filename>')
def download_script(filename):
    return send_from_directory('scripts', filename, as_attachment=True)
 
@app.route('/projet/<int:projet_id>/dependances-par-fichier')
def lister_dependances_par_fichier_route(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))

    fichiers_et_dependances = lister_dependances_par_fichier(dossier_projet)

    return render_template('dependances_par_fichier.html', projet=projet, fichiers_et_dependances=fichiers_et_dependances)

@app.route('/projet/<int:projet_id>/fichiers-par-dependance')
def lister_fichiers_par_dependance_route(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))

    dependances_et_fichiers = lister_fichiers_par_dependance(dossier_projet)

    return render_template('fichiers_par_dependance.html', projet=projet, dependances_et_fichiers=dependances_et_fichiers)
   
######### Evenements

# liste évènements
@app.route('/projet/<int:projet_id>/evenements')
def evenements(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    evenements = Evenement.query.filter_by(projet_id=projet_id).order_by(Evenement.date.desc()).all()
    return render_template('evenements.html', projet=projet, evenements=evenements, datetime=datetime)

# creer evenement
@app.route('/projet/<int:projet_id>/ajouter_evenement', methods=['GET', 'POST'])
def ajouter_evenement(projet_id):
    projet = Projet.query.get_or_404(projet_id)

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
            projet_id=projet.id
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
    # Récupérer l'événement ou retourner 404
    evenement = Evenement.query.get_or_404(evenement_id)

    if request.method == 'POST':
        try:
            # Mettre à jour les informations de base de l'événement
            evenement.type = request.form['type']
            evenement.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
            evenement.contenu = request.form['contenu']

            # Mettre à jour le lien vers un fichier (optionnel)
            if 'lien_fichier' in request.form:
                evenement.lien_fichier = request.form['lien_fichier'] if request.form['lien_fichier'] else None

            # Gérer les tâches existantes et nouvelles
            tache_ids = request.form.getlist('tache_ids[]')
            taches = request.form.getlist('taches[]')
            date_limites = request.form.getlist('date_limite[]')

            # Supprimer toutes les tâches existantes (pour les recréer)
            # Cette approche est simple mais pas optimale pour de gros volumes de données
            Tache.query.filter_by(evenement_id=evenement.id).delete()

            # Recréer toutes les tâches (existantes et nouvelles)
            for i in range(len(taches)):
                if taches[i]:  # Vérifier que la description n'est pas vide
                    date_limite = None
                    if date_limites[i]:
                        date_limite = datetime.strptime(date_limites[i], '%Y-%m-%d').date()

                    nouvelle_tache = Tache(
                        description=taches[i],
                        date_limite=date_limite,
                        statut="à faire",  # Statut par défaut
                        projet_id=evenement.projet_id,
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

    # Affichage initial du formulaire (méthode GET)
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
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))
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
                taille=os.path.getsize(chemin_fichier),
                projet_id=projet_id,
                evenement_id=evenement.id
            )
            db.session.add(nouveau_fichier)

    db.session.commit()
    flash('Fichiers ajoutés avec succès!', 'success')
    return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

# Tous les fichiers
@app.route('/projet/<int:projet_id>/fichiers')
def tous_les_fichiers(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    # Charge les fichiers avec leur événement associé
    fichiers = Fichier.query.options(joinedload(Fichier.evenement)).filter_by(projet_id=projet_id).all()
    return render_template('tous_les_fichiers.html', projet=projet, tous_les_fichiers=fichiers)
    
######################## Tâches

STATUTS_TACHE = ['à faire', 'en cours', 'en attente', 'terminé']

# Ajouter une tâche
@app.route('/projet/<int:projet_id>/ajouter_tache', methods=['POST'])
def ajouter_tache(projet_id):
    description = request.form['description']
    date_limite_str = request.form.get('date_limite')
    evenement_id = request.form.get('evenement_id')  # Récupérer l'ID de l'événement si présent

    date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d') if date_limite_str else None

    if not evenement_id:
        # Si aucun événement n'est spécifié, créer un événement par défaut
        evenement = Evenement(
            type="création_tâche",
            date=datetime.utcnow(),
            contenu=f"Création de la tâche: {description}",
            projet_id=projet_id
        )
        db.session.add(evenement)
        db.session.commit()
        evenement_id = evenement.id

    # Créer la tâche
    tache = Tache(
        description=description,
        statut="à faire",
        date_limite=date_limite,
        projet_id=projet_id,
        evenement_id=evenement_id
    )
    db.session.add(tache)
    db.session.commit()

    flash('Tâche ajoutée avec succès.', 'success')

    # Rediriger vers la page appropriée
    return redirect(request.referrer or url_for('projet_dashboard', projet_id=projet_id))
          
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
   



# fonction lister fichiers

def lister_fichiers_html_par_date(chemin_rproj):
    dossier_projet = os.path.dirname(os.path.abspath(chemin_rproj))
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
