from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import Evenement, Tache, ProjetUser, Projet, db
from datetime import datetime
import os

def register_evenement_routes(app):
    # Liste des événements
    @app.route('/projet/<int:projet_id>/evenements')
    def evenements(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        evenements = Evenement.query.filter_by(projet_id=projet_id).order_by(Evenement.date.desc()).all()
        return render_template('evenements.html', projet=projet, evenements=evenements, datetime=datetime)

    # Créer un événement
    @app.route('/projet/<int:projet_id>/ajouter_evenement', methods=['GET', 'POST'])
    @login_required
    def ajouter_evenement(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet

        if request.method == 'POST':
            type_evenement = request.form['type']
            date_evenement_str = request.form['date']
            contenu = request.form['contenu']
            date_evenement = datetime.strptime(date_evenement_str, '%Y-%m-%dT%H:%M')

            evenement = Evenement(
                type=type_evenement,
                date=date_evenement,
                contenu=contenu,
                projet_id=projet.id,
                createur_id=current_user.id
            )
            db.session.add(evenement)
            db.session.commit()

            # Gestion des tâches
            taches = request.form.getlist('taches[]')
            date_limites = request.form.getlist('date_limite[]')
            statuts = request.form.getlist('statuts[]')

            for i in range(len(taches)):
                if taches[i]:
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

            action = request.form.get('action')
            if action == 'ajouter_fichiers':
                return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))
            else:
                return redirect(url_for('evenements', projet_id=projet.id))

        return render_template('ajouter_evenement.html', projet=projet, datetime=datetime)

    # Détails d'un événement
    @app.route('/evenement/<int:evenement_id>')
    def evenement_detail(evenement_id):
        evenement = Evenement.query.get_or_404(evenement_id)
        projet_id = evenement.projet_id
        return render_template('evenement_detail.html', evenement=evenement, projet_id=projet_id)

    # Modifier un événement
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

    # Supprimer un événement
    @app.route('/evenement/<int:evenement_id>/supprimer', methods=['POST'])
    def supprimer_evenement(evenement_id):
        evenement = Evenement.query.get_or_404(evenement_id)
        projet_id = evenement.projet_id

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
