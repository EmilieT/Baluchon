from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

STATUTS_PROJET = ['en cours', 'en attente', 'archivé', 'abandonné']
PRIORITES_TACHE = ['urgent_important', 'important', 'urgent', 'a_planifier']
PRIORITES_LABELS = {
    'urgent_important': 'Urgent & important',
    'important': 'Important',
    'urgent': 'Urgent',
    'a_planifier': 'À planifier',
}
TYPES_LIEN = ['dossier', 'fichier_local', 'web', 'upload']
TYPES_LIEN_LABELS = {
    'dossier': 'Dossier',
    'fichier_local': 'Fichier local',
    'web': 'Lien web',
    'upload': 'Fichier uploadé',
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Projet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    chemin_rproj = db.Column(db.String(500))
    statut = db.Column(db.String(50), default='en cours')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    evenements = db.relationship('Evenement', backref='projet', lazy=True, cascade="all, delete-orphan")
    taches = db.relationship('Tache', backref='projet', lazy=True, cascade="all, delete-orphan")
    liens = db.relationship('LienProjet', backref='projet', lazy=True, cascade="all, delete-orphan",
                             order_by="LienProjet.ordre")

    @property
    def nb_evenements_a_venir(self):
        return sum(1 for e in self.evenements if e.date >= datetime.utcnow())

    @property
    def nb_taches_ouvertes(self):
        return sum(1 for t in self.taches if t.statut in ('en cours', 'en attente', 'à faire'))

    @property
    def periode_gantt(self):
        """Retourne (date_debut, date_fin) pour l'affichage en diagramme de Gantt.
        Fin = aujourd'hui si le projet est actif, ou la date du dernier événement/tâche s'il est clos."""
        debut = self.date_creation or datetime.utcnow()

        if self.statut in ('archivé', 'abandonné'):
            dates_activite = [e.date for e in self.evenements] + \
                              [t.date_creation for t in self.taches] + \
                              [t.date_cloture for t in self.taches if t.date_cloture]
            fin = max(dates_activite) if dates_activite else debut
            if fin < debut:
                fin = debut
        else:
            fin = datetime.utcnow()

        return debut, fin


class LienProjet(db.Model):
    """Lien associé à un projet (et éventuellement à un événement) :
    dossier, fichier local, lien web, ou fichier uploadé. Fusionne l'ancien
    modèle Fichier (pièces jointes d'événement) et l'ancien LienProjet
    (raccourcis épinglés sur le projet)."""
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, default='web')  # dossier / fichier_local / web / upload
    intitule = db.Column(db.String(150), nullable=False)
    nom_fichier_upload = db.Column(db.String(255))  # nom d'origine si type == upload, distinct de intitule
    commentaire = db.Column(db.Text)
    valeur = db.Column(db.String(1000))  # chemin local OU url OU chemin de stockage si upload
    taille = db.Column(db.Integer)  # taille en octets, pour les uploads
    type_mime = db.Column(db.String(100))
    est_epingle = db.Column(db.Boolean, default=False)  # visible dans les raccourcis "Infos" du projet
    ordre = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'), nullable=True)


class Evenement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    liens = db.relationship('LienProjet', backref='evenement', lazy=True, cascade="all, delete-orphan")
    taches = db.relationship('Tache', backref='evenement', lazy=True, cascade="all, delete-orphan")


class Tache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(50), default="à faire")
    priorite = db.Column(db.String(30), default='a_planifier')
    date_limite = db.Column(db.DateTime)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_cloture = db.Column(db.DateTime)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False, index=True)
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'), nullable=False)

    @property
    def urgence_deadline(self):
        if not self.date_limite or self.statut == 'terminé':
            return None
        jours = (self.date_limite.date() - datetime.utcnow().date()).days
        if jours < 0:
            return 'depassee'
        elif jours <= 2:
            return 'imminente'
        return None
