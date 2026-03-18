from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from flask_login import UserMixin
from enum import Enum

db = SQLAlchemy()

# ==============================
# Énumération des rôles (sans ADMIN)
# ==============================
class RoleEnum(Enum):
    ADMIN = "admin"      # Accès administrateur
    MEMBRE = "membre"    # Accès standard
    LECTURE = "lecture"  # Accès en lecture seule

# ==============================
# Énumération de la visibilité
# ==============================
from enum import Enum

class VisibiliteEnum(Enum):
    PRIVE = "prive"      # Visible seulement par le créateur
    PUBLIC = "public"   # Visible par tous les membres du projet


# ==============================
# Table ProjetUser (fusion de ProjetUser + Environnement)
# ==============================
class ProjetUser(db.Model):
    """Associe un utilisateur à un projet avec un rôle et un chemin local."""
    __tablename__ = 'projet_user'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.MEMBRE, nullable=False)  # Rôle par défaut : MEMBRE
    chemin_proj = db.Column(db.String(500), nullable=False)  # Chemin local du projet
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'projet_id', name='unique_user_projet'),
    )

    # Relations
    user = db.relationship("User", back_populates="projets")
    projet = db.relationship("Projet", back_populates="membres")

# ==============================
# Table User (utilisateurs)
# ==============================
class User(UserMixin, db.Model):
    """Représente un utilisateur de l'application."""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Relations
    projets = db.relationship("ProjetUser", back_populates="user", cascade="all, delete-orphan")
    evenements = db.relationship("Evenement", back_populates="createur", cascade="all, delete-orphan")
    taches = db.relationship("Tache", back_populates="createur", cascade="all, delete-orphan")
    fichiers = db.relationship("Fichier", back_populates="uploader", cascade="all, delete-orphan")

# ==============================
# Table Projet (projets)
# ==============================
class Projet(db.Model):
    """Représente un projet avec ses membres, événements, tâches et fichiers."""
    __tablename__ = 'projet'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    visibilite = db.Column(db.Enum(VisibiliteEnum), default=VisibiliteEnum.PRIVE, nullable=False)  # Ajout du champ visibilite
    createur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Créateur du projet

    # Relations
    membres = db.relationship("ProjetUser", back_populates="projet", cascade="all, delete-orphan")
    evenements = db.relationship("Evenement", back_populates="projet", cascade="all, delete-orphan")
    taches = db.relationship("Tache", back_populates="projet", cascade="all, delete-orphan")
    fichiers = db.relationship("Fichier", back_populates="projet", cascade="all, delete-orphan")

    createur = db.relationship("User")  # Créateur du projet

# ==============================
# Table Evenement (événements liés aux projets)
# ==============================
class Evenement(db.Model):
    """Représente un événement lié à un projet."""
    __tablename__ = 'evenement'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    visibilite = db.Column(db.Enum(VisibiliteEnum), default=VisibiliteEnum.PUBLIC, nullable=False)

    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    createur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relations
    projet = db.relationship("Projet", back_populates="evenements")
    createur = db.relationship("User", back_populates="evenements")
    taches = db.relationship("Tache", back_populates="evenement", lazy=True)  # Relation avec Tache
    fichiers = db.relationship("Fichier", back_populates="evenement", lazy=True)  # Relation avec Fichier

# ==============================
# Table Tache (tâches liées aux projets)
# ==============================
class Tache(db.Model):
    """Représente une tâche liée à un projet."""
    __tablename__ = 'tache'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(50), default="à faire")
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_limite = db.Column(db.DateTime)
    date_cloture = db.Column(db.DateTime) 
    visibilite = db.Column(db.Enum(VisibiliteEnum), default=VisibiliteEnum.PRIVE, nullable=False)

    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    createur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'), nullable=True)  
    # Relations
    projet = db.relationship("Projet", back_populates="taches")
    createur = db.relationship("User", back_populates="taches")
    evenement = db.relationship("Evenement", back_populates="taches")  # Relation avec Evenement

# ==============================
# Table Fichier (fichiers liés aux projets)
# ==============================
class Fichier(db.Model):
    """Représente un fichier lié à un projet."""
    __tablename__ = 'fichier'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    chemin = db.Column(db.String(500), nullable=False)
    taille = db.Column(db.Integer, nullable=False)  # Ajoute cette colonne
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    visibilite = db.Column(db.Enum(VisibiliteEnum), default=VisibiliteEnum.PUBLIC, nullable=False)

    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'), nullable=True)

    # Relations
    projet = db.relationship("Projet", back_populates="fichiers")
    uploader = db.relationship("User", back_populates="fichiers")
    evenement = db.relationship("Evenement", back_populates="fichiers")
