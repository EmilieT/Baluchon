from flask import send_from_directory, send_file, abort, render_template, request, redirect, url_for, flash
from flask_login import current_user
from models import ProjetUser, Projet, Fichier, Evenement, db
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
import os

### variables fichiers
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'r', 'rdata', 'rds'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
def register_fichiers_routes(app):
    # Servir un fichier spécifique d'un projet
    @app.route('/projet/<int:projet_id>/fichiers/<path:filename>')
    def fichier(projet_id, filename):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_proj))
        return send_from_directory(dossier_projet, filename)

    # Servir un fichier depuis la base de données
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

    # Filtre pour formater la taille des fichiers
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

    # Supprimer un fichier
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

    # Gérer les fichiers d'un événement
    @app.route('/evenement/<int:evenement_id>/fichiers')
    def gerer_fichiers(evenement_id):
        evenement = Evenement.query.get_or_404(evenement_id)
        return render_template('gerer_fichiers.html', evenement=evenement)

    # Ajouter des fichiers à un événement
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
                    chemin=chemin_fichier,
                    taille=os.path.getsize(chemin_fichier),
                    projet_id=projet_id,
                    uploader_id=current_user.id,
                    evenement_id=evenement.id
                )
                db.session.add(nouveau_fichier)

        db.session.commit()
        flash('Fichiers ajoutés avec succès!', 'success')
        return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

    # Lister tous les fichiers d'un projet
    @app.route('/projet/<int:projet_id>/fichiers')
    def tous_les_fichiers(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        # Charge les fichiers avec leur événement associé
        fichiers = Fichier.query.options(joinedload(Fichier.evenement)).filter_by(projet_id=projet_id).all()
        return render_template('tous_les_fichiers.html', projet=projet, tous_les_fichiers=fichiers)
