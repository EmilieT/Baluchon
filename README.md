# Baluchon

# Baluchon

**Baluchon** is a Flask application designed to facilitate the management of projects, events, and tasks.  
It is designed for bioinformatics projects.

---

## Main Features
- Project management (add, edit, delete).
- Tracking of events and tasks.
- Visualization of dependencies between files.
- Intuitive and responsive interface.

---

## Prerequisites
- Python 3.8 or higher.
- A virtual environment (recommended).
- The dependencies listed in `requirements.txt`.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/EmilieT/baluchon.git
   cd baluchon
   ```
   
2. Create your virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Sur macOS/Linux
   ```
3. Install the dependencies:
   ```bash
   pip install-r requirements.txt
   ```
4. Create your environment variables:
   ```bash
   SECRET_KEY=ta_cle_secrete_ici
   DATABASE_URI=sqlite:///baluchon.db
   ```

## Project Structure

baluchon/
├── app.py                  # Point d'entrée de l'application

├── config.py               # Configuration de l'application

├── models.py               # Modèles de la base de données

├── requirements.txt        # Dépendances Python

├── static/                 # Fichiers statiques (CSS, JS, images)

├── templates/              # Templates HTML

├── migrations/             # Migrations de la base de données

├── scripts/                # Scripts utilitaires

└── README.md               # Ce fichier


