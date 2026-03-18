from flask import Blueprint, abort, flash, render_template
from flask_login import login_required, current_user
from flask import jsonify, request, redirect, url_for
from datetime import datetime
from models import ProjetUser, Tache, Evenement, Projet, VisibiliteEnum, db

mon_compte_bp = Blueprint('mon_compte', __name__)

@mon_compte_bp.route("/mon_dashboard")
@login_required
def mon_dashboard():
    # Récupérer les tâches de l'utilisateur
    taches = Tache.query.join(Projet).join(ProjetUser).filter(
    ProjetUser.user_id == current_user.id,
    Tache.createur_id == current_user.id
    ).order_by(Tache.date_creation.desc()).all()
 
    # Récupérer les événements liés à l'utilisateur
    evenements = Evenement.query.join(Projet).join(ProjetUser).filter(
    ProjetUser.user_id == current_user.id
    ).order_by(Evenement.date.desc()).limit(10).all()

    return render_template("mon_compte/dashboard.html", taches=taches, evenements=evenements)

@mon_compte_bp.route("/mes_taches")
@login_required
def mes_taches():
    taches = Tache.query.join(Projet).join(ProjetUser).filter(
        ProjetUser.user_id == current_user.id
    ).order_by(Tache.date_creation.desc()).all()
    # Récupérer les projets dont l'utilisateur est membre
    projets = Projet.query.join(Projet.membres).filter(Projet.membres.any(user_id=current_user.id)).all()
    return render_template("mon_compte/mes_taches.html", taches=taches, projets=projets) 

@mon_compte_bp.route("/mes_evenements")
@login_required
def mes_evenements():
    evenements = Evenement.query.join(Projet).filter(
        Projet.membres.any(id=current_user.id)
    ).order_by(Evenement.date.desc()).all()
    return render_template("mon_compte/mes_evenements.html", evenements=evenements)


@mon_compte_bp.route('/ajouter_tache_mes_taches', methods=['POST'])
@login_required
def ajouter_tache_mes_taches():
    projet_id = request.form.get('projet_id', type=int)
    projet = Projet.query.get_or_404(projet_id)

    # Vérifier que l'utilisateur est membre du projet ou le créateur
    is_member = any(membre.user_id == current_user.id for membre in projet.membres)
    if not is_member and projet.createur_id != current_user.id:
        abort(403)

    description = request.form['description']
    statut = request.form.get('statut', 'à faire')
    date_limite_str = request.form.get('date_limite')

    date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d').date() if date_limite_str else None

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

    # Créer la tâche
    tache = Tache(
        description=description,
        statut=statut,
        date_limite=date_limite,
        projet_id=projet_id,
        createur_id=current_user.id,
        visibilite=VisibiliteEnum.PRIVE,  # Par défaut, la tâche est privée
        evenement_id=evenement_id
    )
    db.session.add(tache)
    db.session.commit()

    flash('Tâche ajoutée avec succès.', 'success')
    return redirect(url_for('mon_compte.mes_taches'))

@mon_compte_bp.route("/editer_tache/<int:tache_id>", methods=["GET", "POST"])
@login_required
def editer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)

    if request.method == "POST":
        tache.description = request.form.get("description")
        tache.date_limite = request.form.get("date_limite")
        tache.statut = request.form.get("statut")

        db.session.commit()
        return redirect(url_for('mon_compte.mes_taches'))

    return render_template("mon_compte/editer_tache.html", tache=tache)

@mon_compte_bp.route("/supprimer_tache/<int:tache_id>")
@login_required
def supprimer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    db.session.delete(tache)
    db.session.commit()
    return redirect(url_for('mon_compte.mes_taches'))


