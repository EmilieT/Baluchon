from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from models import Projet, ProjetUser, Tache, Evenement, VisibiliteEnum, RoleEnum, db
from datetime import datetime


def register_projet_routes(app):
    # Accueil (Index des projets)
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            projets = [pu.projet for pu in current_user.projets if pu.projet and pu.projet.id]
        else:
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
            visibilite = request.form.get('visibilite', VisibiliteEnum.PRIVE.name)

            projet = Projet(
                nom=nom,
                description=description,
                visibilite=VisibiliteEnum[visibilite],
                createur_id=current_user.id
            )
            db.session.add(projet)
            db.session.commit()

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

    # Éditer projet
    @app.route('/projet/<int:projet_id>/editer', methods=['GET', 'POST'])
    @login_required
    def editer_projet(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        if projet_user.role not in [RoleEnum.ADMIN, RoleEnum.MEMBRE]:
            flash("Vous n'avez pas les droits pour éditer ce projet.", "danger")
            return redirect(url_for('projet_dashboard', projet_id=projet_id))

        projet = projet_user.projet
        if request.method == 'POST':
            projet.nom = request.form['nom']
            projet.description = request.form['description']
            if projet_user.role == RoleEnum.ADMIN:
                visibilite = request.form.get('visibilite')
                if visibilite:
                    projet.visibilite = VisibiliteEnum[visibilite]
            db.session.commit()
            flash('Les informations du projet ont été mises à jour.', 'success')
            return redirect(url_for('projet_dashboard', projet_id=projet_id))
        return render_template('editer_projet.html', projet=projet, projet_user=projet_user, VisibiliteEnum=VisibiliteEnum)

    # Changer environnement projet
    @app.route('/projet/<int:projet_id>/changer-environnement', methods=['GET', 'POST'])
    @login_required
    def changer_environnement(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        if request.method == 'POST':
            projet_user.chemin_proj = request.form['chemin_proj']
            db.session.commit()
            flash("L'environnement du projet a été mis à jour.", 'success')
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
