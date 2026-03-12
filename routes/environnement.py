from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import ProjetUser, Projet
import os
import subprocess
from datetime import datetime
from scripts.lister_dependances import lister_fichiers_html_par_date

def register_environnement_routes(app):
    # Filtres de template
    @app.template_filter('dirname')
    def dirname_filter(path):
        return os.path.dirname(path)

    @app.template_filter('basename')
    def basename_filter(path):
        return os.path.basename(path)

    # Ouvrir projet
    @app.route('/ouvrir_projet/<int:projet_id>')
    @login_required
    def ouvrir_projet(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        chemin_proj = os.path.abspath(projet_user.chemin_proj)

        try:
            if os.name == 'posix':  # macOS ou Linux
                subprocess.run(['open', chemin_proj], check=True)
            elif os.name == 'nt':   # Windows
                subprocess.run(['start', '', chemin_proj], shell=True, check=True)
            flash("Le projet a été ouvert avec succès.", "success")
        except subprocess.CalledProcessError as e:
            flash(f"Erreur lors de l'ouverture du projet : {e}", "danger")

        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    # Ouvrir dossier
    @app.route('/ouvrir_dossier/<int:projet_id>')
    @login_required
    def ouvrir_dossier(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))

        if os.name == 'posix':  # macOS ou Linux
            subprocess.run(['open', dossier_projet])
        elif os.name == 'nt':   # Windows
            subprocess.run(['explorer', dossier_projet])

        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    # Rapports HTML
    @app.route('/projet/<int:projet_id>/rapports')
    @login_required
    def rapports_html(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        fichiers_html = lister_fichiers_html_par_date(projet_user.chemin_proj)

        return render_template('rapports_html.html',
                              projet=projet,
                              fichiers_html=fichiers_html,
                              datetime=datetime)
