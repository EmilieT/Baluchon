# 🎒 Baluchon

**Baluchon** est une application web (Flask) pour suivre ses projets, événements, tâches, fichiers et informations associées — pensée à l'origine pour des projets de bio-informatique, mais utilisable pour tout suivi de projets.

## Fonctionnalités principales

- **Projets** avec statut (en cours, en attente, archivé, abandonné), description et raccourcis épinglés (liens web, dossiers, fichiers locaux, fichiers uploadés).
- **Événements** datés et typés, avec pièces jointes et tâches associées. Vue liste ou calendrier.
- **Tâches** avec statut, priorité (matrice d'Eisenhower) et date butoir. Vue liste ou matrice.
- **Infos** : centralisez liens et fichiers utiles à chaque projet, avec vérification des liens.
- **Statistiques** : diagramme de Gantt et bilan d'activité sur une période (utile pour un bilan annuel).
- **Connexion sécurisée** par identifiant / mot de passe.

## Installation

Voir le **[GUIDE_INSTALLATION.md](GUIDE_INSTALLATION.md)** pour la procédure pas à pas.

En résumé (Mac / Linux) :

```bash
./install.sh   # installe tout et crée votre compte
./start.sh     # démarre l'application sur http://localhost:8000
```

## Prérequis

- Python 3.8 ou plus
- macOS ou Linux

## Licence

Voir le fichier `LICENSE`.
