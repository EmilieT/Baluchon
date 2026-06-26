from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, abort, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import (db, Projet, Evenement, Tache, LienProjet, User,
                     STATUTS_PROJET, PRIORITES_TACHE, PRIORITES_LABELS,
                     TYPES_LIEN, TYPES_LIEN_LABELS)
from datetime import datetime, timedelta
import os
import subprocess
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ── Auth ─────────────────────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à Baluchon."
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        flash('Identifiant ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('login'))

# ── Variables fichiers ───────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'r', 'rdata', 'rds', 'html', 'htm', 'rmd'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
TAILLE_MAX_UPLOAD_LIEN = 16 * 1024 * 1024  # seuil au-delà duquel on suggère un lien plutôt qu'un upload

def get_unique_filename(upload_folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(upload_folder, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1
    return unique_filename

# ── Filtres Jinja ────────────────────────────────────────────────────────────

@app.template_filter('dirname')
def dirname(path):
    return os.path.dirname(path)

@app.template_filter('basename')
def basename(path):
    return os.path.basename(path)

@app.template_filter('date')
def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

@app.template_filter('format_datetime')
def format_datetime(value, format='%d/%m/%Y %H:%M'):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('filesizeformat')
def filesizeformat(value):
    if value is None:
        return "0 octets"
    size = int(value)
    for unit in ['octets', 'Ko', 'Mo', 'Go']:
        if size < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} To"

# ── Contexte global ──────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return dict(
        datetime=datetime,
        STATUTS_PROJET=STATUTS_PROJET,
        PRIORITES_TACHE=PRIORITES_TACHE,
        PRIORITES_LABELS=PRIORITES_LABELS,
        TYPES_LIEN=TYPES_LIEN,
        TYPES_LIEN_LABELS=TYPES_LIEN_LABELS,
    )

# ── Page d'accueil ───────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    projets_actifs = Projet.query.filter_by(statut='en cours')\
        .order_by(Projet.date_creation.desc()).limit(5).all()

    evenements_a_venir = Evenement.query.filter(
        Evenement.date >= datetime.utcnow()
    ).order_by(Evenement.date.asc()).limit(5).all()

    taches_a_venir = Tache.query.filter(
        Tache.statut != 'terminé'
    ).order_by(Tache.date_limite.asc().nullslast()).limit(5).all()

    nb_projets_en_cours = Projet.query.filter_by(statut='en cours').count()
    nb_projets_en_attente = Projet.query.filter_by(statut='en attente').count()
    nb_taches_ouvertes = Tache.query.filter(Tache.statut != 'terminé').count()
    nb_evenements_a_venir = Evenement.query.filter(Evenement.date >= datetime.utcnow()).count()
    nb_fichiers = LienProjet.query.filter_by(type='upload').count()

    return render_template('index.html',
        projets_actifs=projets_actifs,
        evenements_a_venir=evenements_a_venir,
        taches_a_venir=taches_a_venir,
        nb_projets_en_cours=nb_projets_en_cours,
        nb_projets_en_attente=nb_projets_en_attente,
        nb_taches_ouvertes=nb_taches_ouvertes,
        nb_evenements_a_venir=nb_evenements_a_venir,
        nb_fichiers=nb_fichiers,
    )

# ── Calendrier (mini-calendrier sur la page d'accueil) ───────────────────────

@app.route('/calendrier')
@login_required
def calendrier():
    """Retourne les événements d'un mois donné, pour affichage en mini-calendrier
    (page d'accueil, ou page événements filtrée sur un projet via ?projet_id=)."""
    import calendar as cal_module
    annee = request.args.get('annee', datetime.utcnow().year, type=int)
    mois = request.args.get('mois', datetime.utcnow().month, type=int)
    projet_id = request.args.get('projet_id', type=int)

    premier_jour = datetime(annee, mois, 1)
    dernier_jour_num = cal_module.monthrange(annee, mois)[1]
    dernier_jour = datetime(annee, mois, dernier_jour_num, 23, 59, 59)

    query = Evenement.query.options(joinedload(Evenement.projet))\
        .filter(Evenement.date >= premier_jour, Evenement.date <= dernier_jour)
    if projet_id:
        query = query.filter_by(projet_id=projet_id)
    evenements = query.order_by(Evenement.date.asc()).all()

    jours_evenements = {}
    for evt in evenements:
        jour = evt.date.day
        jours_evenements.setdefault(jour, []).append(evt)

    # Navigation mois précédent/suivant
    if mois == 1:
        mois_prec, annee_prec = 12, annee - 1
    else:
        mois_prec, annee_prec = mois - 1, annee
    if mois == 12:
        mois_suiv, annee_suiv = 1, annee + 1
    else:
        mois_suiv, annee_suiv = mois + 1, annee

    # Construire la grille du calendrier (lundi = 0)
    cal_module.setfirstweekday(cal_module.MONDAY)
    semaines = cal_module.monthcalendar(annee, mois)

    noms_mois = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

    return render_template('_calendrier_widget.html',
        annee=annee, mois=mois, nom_mois=noms_mois[mois],
        semaines=semaines, jours_evenements=jours_evenements,
        mois_prec=mois_prec, annee_prec=annee_prec,
        mois_suiv=mois_suiv, annee_suiv=annee_suiv,
        aujourdhui=datetime.utcnow().date(),
        projet_id=projet_id,
    )

@app.route('/calendrier/jour/<int:annee>/<int:mois>/<int:jour>')
@login_required
def calendrier_jour(annee, mois, jour):
    projet_id = request.args.get('projet_id', type=int)
    debut = datetime(annee, mois, jour)
    fin = debut.replace(hour=23, minute=59, second=59)
    query = Evenement.query.options(joinedload(Evenement.projet))\
        .filter(Evenement.date >= debut, Evenement.date <= fin)
    if projet_id:
        query = query.filter_by(projet_id=projet_id)
    evenements = query.order_by(Evenement.date.asc()).all()
    return render_template('_jour_detail.html', evenements=evenements, date_jour=debut)

# ── Statistiques / Gantt ─────────────────────────────────────────────────────

def _graduations_mois(date_debut, date_fin):
    """Retourne une liste de (date, position_pct, label) pour les débuts de mois dans l'intervalle."""
    duree_totale = (date_fin - date_debut).total_seconds()
    if duree_totale <= 0:
        return []
    noms_mois_court = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
                        'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    graduations = []
    courant = datetime(date_debut.year, date_debut.month, 1)
    if courant < date_debut:
        # premier 1er du mois suivant
        if courant.month == 12:
            courant = datetime(courant.year + 1, 1, 1)
        else:
            courant = datetime(courant.year, courant.month + 1, 1)
    while courant <= date_fin:
        pos_pct = (courant - date_debut).total_seconds() / duree_totale * 100
        label = f"{noms_mois_court[courant.month]} {courant.year}"
        graduations.append((courant, pos_pct, label))
        if courant.month == 12:
            courant = datetime(courant.year + 1, 1, 1)
        else:
            courant = datetime(courant.year, courant.month + 1, 1)
    return graduations

@app.route('/stats')
@login_required
def stats():
    date_debut_str = request.args.get('date_debut', '')
    date_fin_str = request.args.get('date_fin', '')

    if date_debut_str:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
    else:
        date_debut = datetime(datetime.utcnow().year, 1, 1)
        date_debut_str = date_debut.strftime('%Y-%m-%d')

    if date_fin_str:
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        date_fin = datetime.utcnow()
        date_fin_str = date_fin.strftime('%Y-%m-%d')

    nb_jours_periode = max((date_fin.date() - date_debut.date()).days, 1)

    # Tous les projets sauf "abandonné", pour le Gantt
    projets = Projet.query.filter(Projet.statut != 'abandonné').order_by(Projet.date_creation.asc()).all()

    # Compteurs globaux (état actuel, indépendant de la période)
    nb_projets_termines = Projet.query.filter_by(statut='archivé').count()
    nb_projets_en_cours_actuellement = Projet.query.filter(Projet.statut.in_(['en cours', 'en attente'])).count()

    # Construire les barres de Gantt, en bornant l'affichage à la fenêtre choisie
    gantt_projets = []
    for p in projets:
        debut_p, fin_p = p.periode_gantt
        if fin_p < date_debut or debut_p > date_fin:
            continue

        marqueurs_evt = [e.date for e in p.evenements if date_debut <= e.date <= date_fin]
        marqueurs_tache = [t.date_creation for t in p.taches if date_debut <= t.date_creation <= date_fin]

        gantt_projets.append({
            'projet': p,
            'debut': max(debut_p, date_debut),
            'fin': min(fin_p, date_fin),
            'debut_reel': debut_p,
            'fin_reel': fin_p,
            'nb_evenements': len(marqueurs_evt),
            'nb_taches': len(marqueurs_tache),
            'nb_activite': len(marqueurs_evt) + len(marqueurs_tache),
            'marqueurs_evt': sorted(marqueurs_evt),
            'marqueurs_tache': sorted(marqueurs_tache),
        })

    # Tri par activité décroissante pour le tableau d'indicateur
    activite_triee = sorted(gantt_projets, key=lambda x: -x['nb_activite'])

    evenements_periode_count = Evenement.query.filter(
        Evenement.date >= date_debut, Evenement.date <= date_fin
    ).count()

    # Tableau récapitulatif : pour chaque projet actif sur la période, son statut "au sens du bilan"
    bilan_projets = []
    for item in gantt_projets:
        p = item['projet']
        est_nouveau = date_debut <= p.date_creation <= date_fin

        if p.statut == 'archivé':
            etat_periode = 'Terminé'
        elif p.statut == 'abandonné':
            etat_periode = 'Abandonné'
        elif est_nouveau:
            etat_periode = 'Nouveau'
        else:
            etat_periode = 'Toujours en cours'

        # Durée affichée = la portion du projet visible dans la fenêtre choisie (item['debut']/item['fin']),
        # pas la durée totale réelle du projet (qui peut dépasser la période).
        duree_jours = max((item['fin'] - item['debut']).days, 1)

        bilan_projets.append({
            'projet': p,
            'etat_periode': etat_periode,
            'est_nouveau': est_nouveau,
            'nb_evenements': item['nb_evenements'],
            'nb_taches': item['nb_taches'],
            'nb_activite': item['nb_activite'],
            'debut_reel': item['debut_reel'],
            'fin_reel': item['fin_reel'],
            'duree_jours': duree_jours,
        })

    bilan_projets.sort(key=lambda x: -x['nb_activite'])

    graduations_mois = _graduations_mois(date_debut, date_fin)

    return render_template('stats.html',
        date_debut=date_debut_str,
        date_fin=date_fin_str,
        date_debut_dt=date_debut,
        date_fin_dt=date_fin,
        nb_jours_periode=nb_jours_periode,
        gantt_projets=gantt_projets,
        graduations_mois=graduations_mois,
        nb_projets_termines=nb_projets_termines,
        nb_projets_en_cours_actuellement=nb_projets_en_cours_actuellement,
        nb_evenements_periode=evenements_periode_count,
        bilan_projets=bilan_projets,
    )

# ── Projets ──────────────────────────────────────────────────────────────────

@app.route('/projets')
@login_required
def tous_les_projets():
    page = request.args.get('page', 1, type=int)
    statut_filtre = request.args.get('statut', 'en cours')
    per_page = 10

    query = Projet.query.order_by(Projet.date_creation.desc())
    if statut_filtre and statut_filtre != 'tous':
        query = query.filter_by(statut=statut_filtre)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    projets = pagination.items

    return render_template('tous_les_projets.html',
        projets=projets,
        pagination=pagination,
        statut_filtre=statut_filtre,
    )

@app.route('/ajouter_projet', methods=['GET', 'POST'])
@login_required
def ajouter_projet():
    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form['description']
        chemin_rproj = request.form['chemin_rproj']
        statut = request.form.get('statut', 'en cours')
        projet = Projet(nom=nom, description=description, chemin_rproj=chemin_rproj, statut=statut)
        db.session.add(projet)
        db.session.commit()
        flash('Projet ajouté avec succès.', 'success')
        return redirect(url_for('projet_dashboard', projet_id=projet.id))
    return render_template('ajouter_projet.html')

@app.route('/projet/<int:projet_id>/editer', methods=['GET', 'POST'])
@login_required
def editer_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    if request.method == 'POST':
        projet.nom = request.form['nom']
        projet.description = request.form['description']
        projet.chemin_rproj = request.form['chemin_rproj']
        projet.statut = request.form.get('statut', projet.statut)
        db.session.commit()
        flash('Les informations du projet ont été mises à jour.', 'success')
        return redirect(url_for('projet_dashboard', projet_id=projet_id))
    return render_template('editer_projet.html', projet=projet)

@app.route('/projet/<int:projet_id>/supprimer', methods=['POST'])
@login_required
def supprimer_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    db.session.delete(projet)
    db.session.commit()
    flash('Le projet a été supprimé de Baluchon.', 'success')
    return redirect(url_for('index'))

@app.route('/projet/<int:projet_id>/dashboard')
@login_required
def projet_dashboard(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    taches_non_terminees = Tache.query.filter_by(projet_id=projet_id)\
        .filter(Tache.statut != 'terminé')\
        .order_by(Tache.date_limite.asc().nullslast()).all()
    debut_jour = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    evenements_a_venir = Evenement.query.filter_by(projet_id=projet_id)\
        .filter(Evenement.date >= debut_jour)\
        .order_by(Evenement.date.asc()).limit(5).all()
    return render_template('projet_dashboard.html',
        projet=projet,
        taches_non_terminees=taches_non_terminees,
        evenements_a_venir=evenements_a_venir,
    )

@app.route('/ouvrir_projet/<int:projet_id>')
@login_required
def ouvrir_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    chemin_rproj = os.path.abspath(projet.chemin_rproj)
    if os.name == 'posix':
        subprocess.run(['open', chemin_rproj])
    elif os.name == 'nt':
        subprocess.run(['start', '', chemin_rproj], shell=True)
    return redirect(url_for('projet_dashboard', projet_id=projet_id))

@app.route('/ouvrir_dossier/<int:projet_id>')
@login_required
def ouvrir_dossier(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))
    if os.name == 'posix':
        subprocess.run(['open', dossier_projet])
    elif os.name == 'nt':
        subprocess.run(['explorer', dossier_projet])
    return redirect(url_for('projet_dashboard', projet_id=projet_id))

# ── Liens / Infos du projet ──────────────────────────────────────────────────

@app.route('/projet/<int:projet_id>/lien/ajouter', methods=['POST'])
@login_required
def ajouter_lien(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    type_lien = request.form.get('type')
    intitule = request.form.get('intitule', '').strip()
    commentaire = request.form.get('commentaire', '').strip()

    if type_lien not in TYPES_LIEN or not intitule:
        flash('Champs invalides pour l\'info.', 'danger')
        return redirect(url_for('projet_dashboard', projet_id=projet_id))

    lien = LienProjet(type=type_lien, intitule=intitule, commentaire=commentaire,
                       projet_id=projet_id, est_epingle=True)

    if type_lien == 'upload':
        fichier_upload = request.files.get('fichier')
        if not fichier_upload or fichier_upload.filename == '':
            flash('Aucun fichier sélectionné.', 'warning')
            return redirect(url_for('projet_dashboard', projet_id=projet_id))

        # Vérifier la taille avant d'écrire sur le disque
        fichier_upload.seek(0, os.SEEK_END)
        taille = fichier_upload.tell()
        fichier_upload.seek(0)
        if taille > TAILLE_MAX_UPLOAD_LIEN:
            flash(
                f"Ce fichier dépasse {TAILLE_MAX_UPLOAD_LIEN // (1024*1024)} Mo. "
                "Préférez un lien vers son emplacement (dossier ou web) plutôt qu'un upload.",
                'warning'
            )
            return redirect(url_for('projet_dashboard', projet_id=projet_id))

        if not allowed_file(fichier_upload.filename):
            flash('Type de fichier non autorisé.', 'danger')
            return redirect(url_for('projet_dashboard', projet_id=projet_id))

        dossier_projet = os.path.join(app.config['UPLOAD_FOLDER'], f"projet_{projet_id}", "liens")
        os.makedirs(dossier_projet, exist_ok=True)
        filename = secure_filename(fichier_upload.filename)
        filename = get_unique_filename(dossier_projet, filename)
        chemin_complet = os.path.join(dossier_projet, filename)
        fichier_upload.save(chemin_complet)

        lien.valeur = chemin_complet
        lien.nom_fichier_upload = fichier_upload.filename
        lien.taille = os.path.getsize(chemin_complet)
    else:
        valeur = request.form.get('valeur', '').strip()
        if not valeur:
            flash('Veuillez renseigner une valeur pour cette info.', 'danger')
            return redirect(url_for('projet_dashboard', projet_id=projet_id))
        lien.valeur = valeur

    # 1. Créer d'abord l'événement "information"
    evt = Evenement(
        type='information',
        date=datetime.utcnow(),
        contenu=f"Ajout d'une info : {intitule}" + (f" — {commentaire}" if commentaire else ""),
        projet_id=projet_id,
    )
    db.session.add(evt)
    db.session.commit()

    # 2. Relier l'info à cet événement, puis l'enregistrer
    lien.evenement_id = evt.id
    db.session.add(lien)
    db.session.commit()

    flash('Info ajoutée avec succès.', 'success')
    return redirect(url_for('projet_dashboard', projet_id=projet_id))

@app.route('/lien/<int:lien_id>/supprimer', methods=['POST'])
@login_required
def supprimer_lien(lien_id):
    lien = LienProjet.query.get_or_404(lien_id)
    projet_id = lien.projet_id
    intitule = lien.intitule
    if lien.type == 'upload' and lien.valeur and os.path.exists(lien.valeur):
        try:
            os.remove(lien.valeur)
        except OSError:
            pass
    db.session.delete(lien)
    db.session.commit()

    # Événement tracant la suppression
    evt = Evenement(
        type='information',
        date=datetime.utcnow(),
        contenu=f"Suppression d'une info : {intitule}",
        projet_id=projet_id,
    )
    db.session.add(evt)
    db.session.commit()

    flash('Info supprimée.', 'success')
    # Revenir à la page d'origine (dashboard ou page toutes les infos)
    retour = request.form.get('retour')
    if retour:
        return redirect(retour)
    return redirect(url_for('projet_dashboard', projet_id=projet_id))

@app.route('/lien/<int:lien_id>/epingler', methods=['POST'])
@login_required
def basculer_epingle(lien_id):
    """Épingle ou désépingle une info (sans la supprimer)."""
    lien = LienProjet.query.get_or_404(lien_id)
    lien.est_epingle = not lien.est_epingle
    db.session.commit()
    flash('Info désépinglée.' if not lien.est_epingle else 'Info épinglée.', 'success')
    retour = request.form.get('retour')
    if retour:
        return redirect(retour)
    return redirect(url_for('projet_dashboard', projet_id=lien.projet_id))

@app.route('/lien/<int:lien_id>/editer', methods=['GET', 'POST'])
@login_required
def editer_lien(lien_id):
    lien = LienProjet.query.get_or_404(lien_id)
    if request.method == 'POST':
        lien.intitule = request.form.get('intitule', lien.intitule).strip()
        lien.commentaire = request.form.get('commentaire', '').strip()
        # On ne change pas le type ni un fichier uploadé, seulement l'intitulé/commentaire/valeur (si non-upload)
        if lien.type != 'upload':
            nouvelle_valeur = request.form.get('valeur', '').strip()
            if nouvelle_valeur:
                lien.valeur = nouvelle_valeur
        db.session.commit()
        flash('Info mise à jour.', 'success')
        retour = request.form.get('retour')
        if retour:
            return redirect(retour)
        return redirect(url_for('toutes_les_infos', projet_id=lien.projet_id))
    retour = request.args.get('retour', request.referrer or '')
    return render_template('editer_lien.html', lien=lien, retour=retour)

@app.route('/projet/<int:projet_id>/infos')
@login_required
def toutes_les_infos(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    infos = LienProjet.query.filter_by(projet_id=projet_id)\
        .order_by(LienProjet.est_epingle.desc(), LienProjet.date_creation.desc()).all()
    return render_template('toutes_les_infos.html', projet=projet, infos=infos)

@app.route('/lien/<int:lien_id>/verifier', methods=['POST'])
@login_required
def verifier_lien(lien_id):
    """Vérifie si un lien est encore fonctionnel (web : requête HEAD ; local : os.path.exists)."""
    lien = LienProjet.query.get_or_404(lien_id)
    resultat = {'ok': False, 'message': ''}

    if lien.type == 'web':
        import urllib.request
        try:
            req = urllib.request.Request(lien.valeur, method='HEAD')
            urllib.request.urlopen(req, timeout=5)
            resultat = {'ok': True, 'message': 'Lien accessible'}
        except Exception as e:
            resultat = {'ok': False, 'message': f'Inaccessible'}
    elif lien.type in ('dossier', 'fichier_local'):
        if lien.valeur and os.path.exists(lien.valeur):
            resultat = {'ok': True, 'message': 'Chemin existant'}
        else:
            resultat = {'ok': False, 'message': 'Chemin introuvable'}
    elif lien.type == 'upload':
        if lien.valeur and os.path.exists(lien.valeur):
            resultat = {'ok': True, 'message': 'Fichier présent'}
        else:
            resultat = {'ok': False, 'message': 'Fichier manquant'}

    from flask import jsonify
    return jsonify(resultat)

@app.route('/lien/<int:lien_id>/fichier')
@login_required
def servir_lien_upload(lien_id):
    lien = LienProjet.query.get_or_404(lien_id)
    if lien.type != 'upload' or not lien.valeur or not os.path.exists(lien.valeur):
        abort(404)
    return send_file(lien.valeur, as_attachment=False, download_name=lien.nom_fichier_upload or lien.intitule)

# ── Événements ───────────────────────────────────────────────────────────────

TYPES_EVENEMENT = ['note', 'communication', 'envoyé', 'reçu', 'réunion', 'information', 'autre']
PER_PAGE_EVT = 15

@app.route('/projet/<int:projet_id>/evenements')
@login_required
def evenements(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    return _vue_evenements(projet_id=projet_id, projet=projet)

@app.route('/evenements')
@login_required
def tous_les_evenements():
    return _vue_evenements()

def _vue_evenements(projet_id=None, projet=None):
    page = request.args.get('page', 1, type=int)
    type_filtre = request.args.get('type', '')
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')
    periode = request.args.get('periode', '')

    query = Evenement.query.options(joinedload(Evenement.projet))
    if projet_id:
        query = query.filter_by(projet_id=projet_id)
    if type_filtre:
        query = query.filter(Evenement.type == type_filtre)
    if date_debut:
        try:
            query = query.filter(Evenement.date >= datetime.strptime(date_debut, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_fin:
        try:
            query = query.filter(Evenement.date <= datetime.strptime(date_fin, '%Y-%m-%d').replace(hour=23, minute=59))
        except ValueError:
            pass
    if periode == 'avenir':
        query = query.filter(Evenement.date >= datetime.utcnow())
    elif periode == 'passe':
        query = query.filter(Evenement.date < datetime.utcnow())

    query = query.order_by(Evenement.date.desc())
    pagination = query.paginate(page=page, per_page=PER_PAGE_EVT, error_out=False)

    if projet_id:
        types_disponibles = [r[0] for r in db.session.query(Evenement.type).filter_by(projet_id=projet_id).distinct().all()]
    else:
        types_disponibles = [r[0] for r in db.session.query(Evenement.type).distinct().all()]

    # Pour le formulaire d'ajout rapide en vue globale
    tous_projets = None
    if not projet_id:
        tous_projets = Projet.query.order_by(Projet.nom).all()

    return render_template('evenements.html',
        projet=projet,
        evenements=pagination.items,
        pagination=pagination,
        type_filtre=type_filtre,
        date_debut=date_debut,
        date_fin=date_fin,
        periode=periode,
        types_disponibles=types_disponibles,
        tous_projets=tous_projets,
    )

@app.route('/projet/<int:projet_id>/ajouter_evenement', methods=['GET', 'POST'])
@login_required
def ajouter_evenement(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    if request.method == 'POST':
        type_evenement = request.form['type']
        date_evenement_str = request.form['date']
        contenu = request.form['contenu']
        date_evenement = datetime.strptime(date_evenement_str, '%Y-%m-%dT%H:%M')
        evenement = Evenement(type=type_evenement, date=date_evenement, contenu=contenu, projet_id=projet.id)
        db.session.add(evenement)
        db.session.commit()

        taches = request.form.getlist('taches[]')
        date_limites = request.form.getlist('date_limite[]')
        statuts = request.form.getlist('statuts[]')
        for i in range(len(taches)):
            if taches[i]:
                date_limite = None
                if i < len(date_limites) and date_limites[i]:
                    try:
                        date_limite = datetime.strptime(date_limites[i], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                statut_tache = statuts[i] if i < len(statuts) else 'à faire'
                nouvelle_tache = Tache(
                    description=taches[i],
                    date_limite=date_limite,
                    statut=statut_tache,
                    projet_id=projet.id,
                    evenement_id=evenement.id
                )
                db.session.add(nouvelle_tache)
        db.session.commit()

        action = request.form.get('action')
        if action == 'ajouter_fichiers':
            return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))
        flash('Événement ajouté avec succès.', 'success')

        retour = request.form.get('retour')
        if retour == 'global':
            return redirect(url_for('tous_les_evenements'))
        return redirect(url_for('evenements', projet_id=projet.id))
    return render_template('ajouter_evenement.html', projet=projet)

@app.route('/evenement/<int:evenement_id>')
@login_required
def evenement_detail(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    return render_template('evenement_detail.html', evenement=evenement, projet_id=evenement.projet_id)

@app.route('/evenement/<int:evenement_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_evenement(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    if request.method == 'POST':
        try:
            evenement.type = request.form['type']
            evenement.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
            evenement.contenu = request.form['contenu']
            if 'lien_fichier' in request.form:
                evenement.lien_fichier = request.form['lien_fichier'] if request.form['lien_fichier'] else None

            Tache.query.filter_by(evenement_id=evenement.id).delete()
            taches = request.form.getlist('taches[]')
            date_limites = request.form.getlist('date_limite[]')
            for i in range(len(taches)):
                if taches[i]:
                    date_limite = None
                    if i < len(date_limites) and date_limites[i]:
                        try:
                            date_limite = datetime.strptime(date_limites[i], '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    nouvelle_tache = Tache(
                        description=taches[i],
                        date_limite=date_limite,
                        statut="à faire",
                        projet_id=evenement.projet_id,
                        evenement_id=evenement.id
                    )
                    db.session.add(nouvelle_tache)
            db.session.commit()
            flash("L'événement a été modifié avec succès.", 'success')
            return redirect(url_for('evenement_detail', evenement_id=evenement.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue : {str(e)}', 'danger')
    return render_template('modifier_evenement.html', evenement=evenement)

@app.route('/evenement/<int:evenement_id>/supprimer', methods=['POST'])
@login_required
def supprimer_evenement(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    projet_id = evenement.projet_id
    for lien in evenement.liens:
        if lien.type == 'upload' and lien.valeur and os.path.exists(lien.valeur):
            try:
                os.remove(lien.valeur)
            except OSError as e:
                flash(f"Erreur lors de la suppression du fichier {lien.intitule} : {e}", "warning")
    db.session.delete(evenement)
    db.session.commit()
    flash("L'événement a été supprimé avec succès.", 'success')
    return redirect(url_for('evenements', projet_id=projet_id))

# ── Pièces jointes (événements) — stockées comme LienProjet de type 'upload' ──

@app.route('/projet/<int:projet_id>/fichiers/<path:filename>')
@login_required
def fichier(projet_id, filename):
    projet = Projet.query.get_or_404(projet_id)
    dossier_projet = os.path.dirname(os.path.abspath(projet.chemin_rproj))
    return send_from_directory(dossier_projet, filename)

@app.route('/fichier/<int:fichier_id>')
@app.route('/fichier/<int:fichier_id>/<action>')
@login_required
def servir_fichier(fichier_id, action=None):
    lien = LienProjet.query.get_or_404(fichier_id)
    if lien.type != 'upload' or not lien.valeur:
        abort(404)
    if not os.path.exists(lien.valeur):
        abort(404)
    if not os.path.abspath(lien.valeur).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
        abort(403)
    as_attachment = action == 'telecharger'
    mimetypes = {
        'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif',
        'pdf': 'application/pdf', 'txt': 'text/plain', 'csv': 'text/csv',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'r': 'text/plain', 'rdata': 'application/octet-stream', 'rds': 'application/octet-stream'
    }
    nom_affiche = lien.nom_fichier_upload or lien.intitule
    extension = nom_affiche.rsplit('.', 1)[1].lower() if '.' in nom_affiche else ''
    mimetype = lien.type_mime or mimetypes.get(extension, 'application/octet-stream')
    return send_file(lien.valeur, as_attachment=as_attachment, download_name=nom_affiche, mimetype=mimetype)

@app.route('/fichier/<int:fichier_id>/supprimer', methods=['POST'])
@login_required
def supprimer_fichier(fichier_id):
    lien = LienProjet.query.get_or_404(fichier_id)
    if lien.type == 'upload' and lien.valeur and os.path.exists(lien.valeur):
        try:
            os.remove(lien.valeur)
        except OSError as e:
            flash(f"Erreur lors de la suppression du fichier : {e}", 'danger')
            return redirect(url_for('modifier_evenement', evenement_id=lien.evenement_id))
    evenement_id = lien.evenement_id
    db.session.delete(lien)
    db.session.commit()
    flash('Le fichier a été supprimé avec succès.', 'success')
    return redirect(url_for('modifier_evenement', evenement_id=evenement_id))

@app.route('/evenement/<int:evenement_id>/fichiers')
@login_required
def gerer_fichiers(evenement_id):
    evenement = Evenement.query.get_or_404(evenement_id)
    return render_template('gerer_fichiers.html', evenement=evenement)

@app.route('/evenement/<int:evenement_id>/ajouter-fichiers', methods=['POST'])
@login_required
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
    dossier_projet = os.path.join(app.config['UPLOAD_FOLDER'], f"projet_{projet_id}")
    os.makedirs(dossier_projet, exist_ok=True)
    for fichier_upload in fichiers:
        if fichier_upload.filename != '' and allowed_file(fichier_upload.filename):
            filename = secure_filename(fichier_upload.filename)
            filename = get_unique_filename(dossier_projet, filename)
            chemin_fichier = os.path.join(dossier_projet, filename)
            fichier_upload.save(chemin_fichier)
            nouveau_lien = LienProjet(
                type='upload',
                intitule=filename,
                nom_fichier_upload=filename,
                valeur=chemin_fichier,
                taille=os.path.getsize(chemin_fichier),
                projet_id=projet_id,
                evenement_id=evenement.id,
                est_epingle=False,
            )
            db.session.add(nouveau_lien)
    db.session.commit()
    flash('Fichiers ajoutés avec succès.', 'success')
    return redirect(url_for('gerer_fichiers', evenement_id=evenement.id))

@app.route('/projet/<int:projet_id>/tous-les-fichiers')
@login_required
def tous_les_fichiers(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    fichiers = LienProjet.query.options(joinedload(LienProjet.evenement))\
        .filter_by(projet_id=projet_id, type='upload').all()
    return render_template('tous_les_fichiers.html', projet=projet, tous_les_fichiers=fichiers)

@app.route('/fichiers')
@login_required
def vue_globale_fichiers():
    page = request.args.get('page', 1, type=int)
    projet_id_filtre = request.args.get('projet_id', 0, type=int)
    query = LienProjet.query.options(joinedload(LienProjet.evenement), joinedload(LienProjet.projet))\
        .filter_by(type='upload')
    if projet_id_filtre:
        query = query.filter_by(projet_id=projet_id_filtre)
    query = query.order_by(LienProjet.date_creation.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    projets = Projet.query.order_by(Projet.nom).all()
    return render_template('vue_globale_fichiers.html',
        fichiers=pagination.items,
        pagination=pagination,
        projets=projets,
        projet_id_filtre=projet_id_filtre,
    )

# ── Tâches ───────────────────────────────────────────────────────────────────

STATUTS_TACHE = ['à faire', 'en cours', 'en attente', 'terminé']
PER_PAGE_TACHE = 15

@app.route('/projet/<int:projet_id>/taches')
@login_required
def toutes_les_taches(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    return _vue_taches(projet_id=projet_id, projet=projet)

@app.route('/taches')
@login_required
def vue_globale_taches():
    return _vue_taches()

def _vue_taches(projet_id=None, projet=None):
    page = request.args.get('page', 1, type=int)
    statut_filtre = request.args.get('statut', '')
    priorite_filtre = request.args.get('priorite', '')
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')

    query = Tache.query.options(joinedload(Tache.projet))
    if projet_id:
        query = query.filter_by(projet_id=projet_id)
    if statut_filtre:
        query = query.filter(Tache.statut == statut_filtre)
    if priorite_filtre:
        query = query.filter(Tache.priorite == priorite_filtre)
    if date_debut:
        try:
            query = query.filter(Tache.date_limite >= datetime.strptime(date_debut, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_fin:
        try:
            query = query.filter(Tache.date_limite <= datetime.strptime(date_fin, '%Y-%m-%d'))
        except ValueError:
            pass

    query = query.order_by(Tache.date_creation.desc())
    pagination = query.paginate(page=page, per_page=PER_PAGE_TACHE, error_out=False)

    tous_projets = None
    if not projet_id:
        tous_projets = Projet.query.order_by(Projet.nom).all()

    return render_template('taches.html',
        projet=projet,
        taches=pagination.items,
        pagination=pagination,
        statut_filtre=statut_filtre,
        priorite_filtre=priorite_filtre,
        date_debut=date_debut,
        date_fin=date_fin,
        statuts=STATUTS_TACHE,
        tous_projets=tous_projets,
    )

@app.route('/projet/<int:projet_id>/taches/matrice')
@login_required
def matrice_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    return _vue_matrice(projet_id=projet_id, projet=projet)

@app.route('/taches/matrice')
@login_required
def matrice_globale():
    return _vue_matrice()

def _vue_matrice(projet_id=None, projet=None):
    query = Tache.query.options(joinedload(Tache.projet)).filter(Tache.statut != 'terminé')
    if projet_id:
        query = query.filter_by(projet_id=projet_id)
    taches = query.order_by(Tache.date_limite.asc().nullslast()).all()

    quadrants = {p: [] for p in PRIORITES_TACHE}
    for t in taches:
        quadrants.setdefault(t.priorite or 'a_planifier', []).append(t)

    return render_template('matrice.html', projet=projet, quadrants=quadrants)

@app.route('/projet/<int:projet_id>/ajouter_tache', methods=['POST'])
@login_required
def ajouter_tache(projet_id):
    description = request.form['description']
    date_limite_str = request.form.get('date_limite')
    evenement_id = request.form.get('evenement_id')
    priorite = request.form.get('priorite', 'a_planifier')
    if priorite not in PRIORITES_TACHE:
        priorite = 'a_planifier'
    date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d') if date_limite_str else None

    if not evenement_id:
        evenement = Evenement(
            type="création_tâche", date=datetime.utcnow(),
            contenu=f"Création de la tâche : {description}", projet_id=projet_id
        )
        db.session.add(evenement)
        db.session.commit()
        evenement_id = evenement.id

    tache = Tache(description=description, statut="à faire", date_limite=date_limite,
                  priorite=priorite, projet_id=projet_id, evenement_id=evenement_id)
    db.session.add(tache)
    db.session.commit()
    flash('Tâche ajoutée avec succès.', 'success')
    return redirect(request.referrer or url_for('projet_dashboard', projet_id=projet_id))

@app.route('/ajouter_tache_globale', methods=['POST'])
@login_required
def ajouter_tache_globale():
    """Ajout de tâche depuis la vue globale des tâches, avec choix du projet."""
    projet_id = request.form.get('projet_id', type=int)
    if not projet_id:
        flash('Veuillez choisir un projet.', 'danger')
        return redirect(url_for('vue_globale_taches'))
    return ajouter_tache(projet_id)

@app.route('/tache/<int:tache_id>/changer_statut', methods=['POST'])
@login_required
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
    return redirect(request.referrer or url_for('projet_dashboard', projet_id=tache.projet_id))

@app.route('/tache/<int:tache_id>/changer_priorite', methods=['POST'])
@login_required
def changer_priorite(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    nouvelle_priorite = request.form.get('priorite')
    if nouvelle_priorite in PRIORITES_TACHE:
        tache.priorite = nouvelle_priorite
        db.session.commit()
        flash('Priorité mise à jour.', 'success')
    else:
        flash('Priorité invalide.', 'danger')
    return redirect(request.referrer or url_for('vue_globale_taches'))

@app.route('/tache/<int:tache_id>/supprimer', methods=['POST'])
@login_required
def supprimer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    projet_id = tache.projet_id
    db.session.delete(tache)
    db.session.commit()
    flash('Tâche supprimée avec succès.', 'success')
    return redirect(request.referrer or url_for('toutes_les_taches', projet_id=projet_id))

@app.route('/tache/<int:tache_id>/editer', methods=['GET', 'POST'])
@login_required
def editer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    if request.method == 'POST':
        tache.description = request.form['description']
        date_limite_str = request.form.get('date_limite')
        tache.date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d') if date_limite_str else None
        tache.statut = request.form['statut']
        priorite = request.form.get('priorite', 'a_planifier')
        tache.priorite = priorite if priorite in PRIORITES_TACHE else 'a_planifier'
        if tache.statut == 'terminé' and not tache.date_cloture:
            tache.date_cloture = datetime.utcnow()
        elif tache.statut != 'terminé':
            tache.date_cloture = None
        db.session.commit()
        flash('Tâche modifiée avec succès.', 'success')
        retour = request.form.get('retour')
        if retour:
            return redirect(retour)
        return redirect(url_for('toutes_les_taches', projet_id=tache.projet_id))
    retour = request.args.get('retour', request.referrer or '')
    return render_template('editer_tache.html', tache=tache, retour=retour)

# ── Scripts ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
