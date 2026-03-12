# routes/dependances.py
from flask import render_template
from flask_login import login_required, current_user
from models import ProjetUser, Projet
from scripts.lister_dependances import lister_dependances_par_fichier, lister_fichiers_par_dependance
import os

def register_dependances_routes(app):
    @app.route('/projet/<int:projet_id>/dependances-par-fichier')
    @login_required
    def lister_dependances_par_fichier_route(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))
        fichiers_et_dependances = lister_dependances_par_fichier(dossier_projet)
        return render_template('dependances_par_fichier.html',
                              projet=projet,
                              fichiers_et_dependances=fichiers_et_dependances)

    @app.route('/projet/<int:projet_id>/fichiers-par-dependance')
    @login_required
    def lister_fichiers_par_dependance_route(projet_id):
        projet_user = ProjetUser.query.filter_by(user_id=current_user.id, projet_id=projet_id).first_or_404()
        projet = projet_user.projet
        dossier_projet = os.path.dirname(os.path.abspath(projet_user.chemin_proj))
        dependances_et_fichiers = lister_fichiers_par_dependance(dossier_projet)
        return render_template('fichiers_par_dependance.html',
                              projet=projet,
                              dependances_et_fichiers=dependances_et_fichiers)
