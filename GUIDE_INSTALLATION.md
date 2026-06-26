# Guide d'installation de Baluchon

Ce guide vous accompagne pas à pas pour installer Baluchon sur un Mac ou un ordinateur Linux, et démarrer avec une base de données vierge. Aucune connaissance technique avancée n'est requise — il suffit de recopier les commandes.

---

## 1. Ce dont vous avez besoin

- Un Mac ou un ordinateur Linux
- **Python 3.8 ou plus**. Pour vérifier s'il est installé, ouvrez le **Terminal** et tapez :
  ```bash
  python3 --version
  ```
  Si une version s'affiche (ex : `Python 3.11.5`), c'est bon. Sinon, installez Python depuis https://www.python.org/downloads/

---

## 2. Placer le dossier Baluchon

Décompressez l'archive `baluchon.tar.gz` que l'on vous a transmise. Vous obtenez un dossier `baluchon`. Placez-le où vous voulez, par exemple dans votre dossier personnel.

Ouvrez le **Terminal** et déplacez-vous dans ce dossier. Par exemple, s'il est dans votre dossier personnel :

```bash
cd ~/baluchon
```

> 💡 Astuce : vous pouvez taper `cd ` (avec un espace) puis glisser-déposer le dossier depuis le Finder dans la fenêtre du Terminal, et appuyer sur Entrée.

---

## 3. Installation automatique

Lancez le script d'installation :

```bash
./install.sh
```

Ce script fait tout automatiquement :
- crée un environnement isolé pour l'application,
- installe les composants nécessaires,
- génère une configuration sécurisée,
- crée une base de données vierge,
- vous demande de **choisir votre identifiant et votre mot de passe** de connexion.

> Si le terminal répond `permission denied`, donnez les droits d'exécution une fois pour toutes :
> ```bash
> chmod +x install.sh start.sh
> ```
> puis relancez `./install.sh`.

À la fin, vous verrez le message **« Installation terminée ! »**.

---

## 4. Démarrer Baluchon

```bash
./start.sh
```

Vous verrez s'afficher :
```
🎒 Baluchon démarre sur http://localhost:8000
```

Ouvrez votre navigateur et allez à l'adresse **http://localhost:8000**.

Connectez-vous avec l'identifiant et le mot de passe choisis à l'étape 3.

> Pour **arrêter** l'application, revenez dans le Terminal et appuyez sur `Ctrl + C`.

> Pour utiliser un autre port (par exemple si le 8000 est déjà pris) :
> ```bash
> ./start.sh 8001
> ```

---

## 5. Utilisation quotidienne

Chaque fois que vous voulez utiliser Baluchon :

1. Ouvrez le Terminal
2. Déplacez-vous dans le dossier : `cd ~/baluchon`
3. Lancez : `./start.sh`
4. Ouvrez http://localhost:8000 dans le navigateur

C'est tout. Vos données sont enregistrées localement dans le fichier `baluchon.db` à l'intérieur du dossier.

---

## 6. Sauvegarder ses données

Toutes vos données tiennent dans deux endroits, à l'intérieur du dossier `baluchon` :
- le fichier **`instance/baluchon.db`** (projets, événements, tâches, infos)
- le dossier **`uploads/`** (fichiers que vous avez importés)

Pour faire une sauvegarde, il suffit de copier ces deux éléments ailleurs (disque externe, cloud…). Par exemple :

```bash
cp instance/baluchon.db ~/Desktop/baluchon-sauvegarde.db
cp -r uploads ~/Desktop/baluchon-uploads-sauvegarde
```

---

## 7. En cas de souci

**« command not found: python3 »** → Python n'est pas installé. Voir l'étape 1.

**« permission denied » en lançant un script** → tapez `chmod +x install.sh start.sh` puis réessayez.

**« Address already in use »** → le port est déjà utilisé. Démarrez sur un autre port : `./start.sh 8001`.

**J'ai oublié mon mot de passe** → recréez un compte (ou changez le mot de passe d'un compte existant) :
```bash
source venv/bin/activate
python create_admin.py
```

**Réinitialiser complètement (effacer toutes les données)** → supprimez le fichier `instance/baluchon.db`, puis relancez :
```bash
source venv/bin/activate
python init_db.py
python create_admin.py
```

---

Bonne utilisation ! 🎒
