from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

    
class Projet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    chemin_rproj = db.Column(db.String(500))
    evenements = db.relationship('Evenement', backref='projet', lazy=True, cascade="all, delete-orphan")
    taches = db.relationship('Tache', backref='projet', lazy=True, cascade="all, delete-orphan")
    fichiers = db.relationship('Fichier', backref='projet', lazy=True, cascade="all, delete-orphan")
    
class Fichier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chemin = db.Column(db.String(500), nullable=False)
    nom = db.Column(db.String(255))
    taille = db.Column(db.Integer)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'))
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'))
        
class Evenement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False)
    fichiers = db.relationship('Fichier', backref='evenement', lazy=True, cascade="all, delete-orphan")
    taches = db.relationship('Tache', backref='evenement', lazy=True, cascade="all, delete-orphan")

class Tache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(50), default="à faire")
    date_limite = db.Column(db.DateTime)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_cloture = db.Column(db.DateTime)
    projet_id = db.Column(db.Integer, db.ForeignKey('projet.id'), nullable=False, index=True)
    evenement_id = db.Column(db.Integer, db.ForeignKey('evenement.id'), nullable=False)
