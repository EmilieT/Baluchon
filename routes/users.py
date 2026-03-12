# routes/users.py
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User, Projet, ProjetUser, RoleEnum, db

def register_user_routes(app):
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

    # Profil utilisateur
    @app.route('/utilisateur/<int:user_id>')
    @login_required
    def voir_profil(user_id):
        utilisateur = User.query.get_or_404(user_id)
        return render_template('profil.html', utilisateur=utilisateur)

    # Liste des utilisateurs
    @app.route('/utilisateurs')
    @login_required
    def liste_utilisateurs():
        utilisateurs = User.query.all()
        return render_template('utilisateurs.html', utilisateurs=utilisateurs)

    # Inviter un utilisateur à un projet
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
            username = request.form.get('username')
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
