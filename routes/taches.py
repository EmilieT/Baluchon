from flask import request, flash, redirect, url_for, render_template, abort
from flask_login import login_required, current_user
from models import Tache, Projet, Evenement, VisibiliteEnum, RoleEnum, db
from datetime import datetime

STATUTS_TACHE = ['à faire', 'en cours', 'en attente', 'terminé']

def register_taches_routes(app):
    # Ajouter une tâche
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
        visibilite_str = request.form.get('visibilites[]', 'prive')

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
            visibilite=visibilite,
            evenement_id=evenement_id
        )
        db.session.add(tache)
        db.session.commit()

        flash('Tâche ajoutée avec succès.', 'success')
        return redirect(request.referrer or url_for('projet_dashboard', projet_id=projet_id))

    # Changer la visibilité d'une tâche
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

    # Changer le statut d'une tâche
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
        return redirect(request.referrer or url_for('toutes_les_taches', projet_id=tache.projet_id))

    # Supprimer une tâche
    @app.route('/tache/<int:tache_id>/supprimer', methods=['POST'])
    def supprimer_tache(tache_id):
        tache = Tache.query.get_or_404(tache_id)
        projet_id = tache.projet_id
        db.session.delete(tache)
        db.session.commit()
        flash('Tâche supprimée avec succès.', 'success')
        return redirect(url_for('toutes_les_taches', projet_id=projet_id))

    # Toutes les tâches d'un projet
    @app.route('/projet/<int:projet_id>/toutes_les_taches')
    def toutes_les_taches(projet_id):
        projet = Projet.query.get_or_404(projet_id)
        toutes_les_taches = Tache.query.filter_by(projet_id=projet_id).order_by(Tache.date_creation.desc()).all()
        return render_template('toutes_les_taches.html', projet=projet, toutes_les_taches=toutes_les_taches)

    # Éditer une tâche
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
