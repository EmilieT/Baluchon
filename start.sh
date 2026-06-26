#!/bin/bash
# Démarre Baluchon en local avec gunicorn.
# Le script fonctionne quel que soit l'emplacement du dossier.

cd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel introuvable. Lancez d'abord l'installation (voir GUIDE_INSTALLATION.md)."
    exit 1
fi

source venv/bin/activate

# Port par défaut : 8000. Modifiable en passant un argument : ./start.sh 8001
PORT="${1:-8000}"

echo "🎒 Baluchon démarre sur http://localhost:$PORT"
gunicorn -w 4 -b 0.0.0.0:"$PORT" app:app
