#!/bin/bash
# Installation automatique de Baluchon (Mac / Linux).
# Crée l'environnement virtuel, installe les dépendances, génère la configuration,
# initialise la base de données et crée le compte de connexion.

cd "$(dirname "$0")" || exit 1

echo "🎒 Installation de Baluchon"
echo "=========================="
echo ""

# 1. Vérifier Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Installez-le d'abord (https://www.python.org/downloads/)."
    exit 1
fi
echo "✓ Python 3 détecté : $(python3 --version)"

# 2. Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "→ Création de l'environnement virtuel..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✓ Environnement virtuel prêt"

# 3. Installer les dépendances
echo "→ Installation des dépendances..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "✓ Dépendances installées"

# 4. Générer le fichier .env si absent
if [ ! -f ".env" ]; then
    echo "→ Génération de la configuration (.env)..."
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > .env << ENVEOF
SECRET_KEY=$SECRET
DATABASE_URI=sqlite:///baluchon.db
ENVEOF
    echo "✓ Fichier .env créé avec une clé secrète unique"
else
    echo "· Fichier .env déjà présent, conservé tel quel"
fi

# 5. Initialiser la base de données
echo "→ Initialisation de la base de données..."
python init_db.py

# 6. Créer le compte de connexion
echo ""
echo "→ Création de votre compte de connexion :"
python create_admin.py

echo ""
echo "=========================="
echo "✅ Installation terminée !"
echo ""
echo "Pour démarrer Baluchon :"
echo "    ./start.sh"
echo ""
echo "Puis ouvrez http://localhost:8000 dans votre navigateur."
