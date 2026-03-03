# Baluchon

# Baluchon

**Baluchon** is a Flask application designed to facilitate the management of projects, events, and tasks for bioinformatics projects.

---

## Main Features
- Quick project management (add, edit, delete).
- Visualization of project dependencies within your local desktop environment.
- Simple tracking of events, tasks, and files associated with each project.
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
   source venv/bin/activate  # macOS/Linux
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initiate your database
   ```bash
   mkdir -p instance
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```   

---
## **Launch the Project**

1. **Activate the virtual environment** (if not already active):
   ```bash
   source venv/bin/activate  # On macOS/Linux
   ```
   
2. **Run the Flask application:**
   ```bash
   python app.py
   ```
(The application will start and be available at http://127.0.0.1:5000.)
