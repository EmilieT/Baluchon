# Guide des fonctionnalités de Baluchon

Ce guide explique comment utiliser Baluchon au quotidien, une fois l'application installée et lancée. Pour l'installation, voir `GUIDE_INSTALLATION.md`.

---

## Connexion

Baluchon est protégé par un identifiant et un mot de passe (créés à l'installation). À l'ouverture, vous arrivez sur la page de connexion. Une fois connecté·e, vous le restez jusqu'à la déconnexion (icône en haut à droite).

---

## La page d'accueil

C'est votre tableau de bord. Elle réunit en un coup d'œil :

- **Compteurs cliquables** : projets en cours, projets en attente, tâches ouvertes, événements à venir. Chaque compteur mène à la liste correspondante.
- **Projets en cours** : les projets actifs les plus récents.
- **Tâches ouvertes** : vos tâches non terminées, avec leur statut en couleur et leur échéance.
- **Prochains événements** : ce qui arrive, affichable en liste ou en **vue calendrier** (bouton en haut du bloc).

Le menu en haut donne accès à tout moment aux grandes sections : Projets, Événements, Tâches, Matrice, Fichiers, Stats.

---

## Les projets

### Créer et organiser
Un projet a un **nom**, une **description**, un **chemin** vers un fichier principal (optionnel, par ex. un fichier RStudio), et un **statut** :
- **En cours** — projet actif
- **En attente** — mis en pause
- **Archivé** — terminé
- **Abandonné** — arrêté

Le statut se change depuis la page « Éditer le projet ».

### La page d'un projet (tableau de bord)
Elle rassemble tout ce qui concerne ce projet :

- **Infos** : raccourcis épinglés vers ce qui est utile (lien web, dossier, fichier local, ou fichier uploadé), chacun avec un intitulé et un commentaire. Le fichier principal du projet s'ouvre directement depuis ici.
- **Tâches en cours** : avec ajout rapide (description + date butoir).
- **Aujourd'hui et à venir** : les événements du jour et futurs.
- **Fichiers uploadés** : accès à tous les fichiers importés pour ce projet.

### La liste de tous les projets
Triés du plus récent au plus ancien, filtrables par statut, paginés (10 par page). Chaque projet affiche son statut, sa date de création, son nombre d'événements à venir et de tâches ouvertes.

---

## Les infos

Les « infos » centralisent tout ce qui est utile à un projet sans encombrer. Chaque info peut être :
- un **lien web** (ex : dépôt GitHub, documentation en ligne),
- un **dossier** local,
- un **fichier local** (chemin sur votre disque),
- un **fichier uploadé** (importé dans Baluchon, jusqu'à 16 Mo).

Chaque ajout ou suppression d'info crée automatiquement un **événement** de type « information » qui en garde la trace.

### Épingler / désépingler
Les infos épinglées apparaissent sur le tableau de bord du projet. Pour éviter d'en avoir trop sous les yeux, vous pouvez **désépingler** une info (elle reste accessible, mais disparaît du tableau de bord).

### La page « Toutes les infos »
Accessible depuis le projet, elle liste toutes les infos (épinglées ou non) sous forme de tableau. Vous pouvez :
- **vérifier** si un lien est encore fonctionnel (bouton par ligne, ou « Vérifier tous les liens ») — une pastille verte ou rouge indique l'état,
- **éditer** l'intitulé, le commentaire ou la valeur,
- épingler/désépingler, ou supprimer.

---

## Les événements

Un événement représente quelque chose qui s'est passé ou qui va se passer sur un projet : une note, une communication, une réunion, un envoi, etc. Il a une **date**, un **type**, un **contenu**, et peut porter des **fichiers** et des **tâches**.

### Consulter
- **Par projet** : la page événements d'un projet, filtrable par type, par période (passés / à venir) et par dates.
- **Tous les événements** : la vue globale, tous projets confondus.
- **Vue calendrier** : sur ces pages comme sur l'accueil, basculez en calendrier mensuel ; les jours avec événements sont marqués d'un point, cliquez sur un jour pour voir le détail.

Les événements à venir et passés sont séparés visuellement.

### Créer
Depuis un projet, ou depuis la vue globale (en choisissant le projet concerné). À la création, vous pouvez déjà associer des tâches, puis ajouter des fichiers.

---

## Les tâches

Une tâche a une **description**, un **statut**, une **priorité** et une **date butoir** (optionnelle).

### Statuts (modifiables d'un clic, en couleur)
À faire · En cours · En attente · Terminé

### Priorités — la matrice d'Eisenhower
Chaque tâche reçoit une priorité :
- **Urgent & important**
- **Important**
- **Urgent**
- **À planifier**

La priorité se change directement dans la liste ou la matrice, comme le statut.

### Indicateur d'échéance
Indépendamment de la priorité, une tâche dont la date butoir approche (≤ 2 jours) ou est dépassée est signalée par un liseré et une pastille « Bientôt » ou « Dépassée ».

### Les vues
- **Liste** : par projet ou globale, avec filtres (statut, priorité, dates) et ajout rapide.
- **Matrice** : les tâches réparties dans les 4 quadrants d'Eisenhower, pour les classer visuellement. On peut changer la priorité d'une tâche directement dans la matrice pour la déplacer d'un quadrant à l'autre.

---

## Les fichiers

Tous les fichiers importés (pièces jointes d'événements, fichiers d'infos) sont consultables :
- **Par projet** : la page « Fichiers » d'un projet.
- **Globalement** : la vue tous fichiers, filtrable par projet.

Formats acceptés : txt, pdf, html, images (png, jpg, gif), doc(x), xls(x), csv, r, rmd, rdata, rds — jusqu'à 16 Mo. Au-delà, mieux vaut référencer le fichier par un lien plutôt que de l'importer.

---

## Les statistiques

La page Stats est un **bilan d'activité sur une période** (par défaut, du 1ᵉʳ janvier de l'année en cours à aujourd'hui — dates ajustables).

- **Compteurs** : projets actifs sur la période, en cours actuellement, terminés, et nombre d'événements.
- **Diagramme de Gantt** : chaque projet est une barre allant de sa création à aujourd'hui (s'il est actif) ou à sa dernière activité (s'il est archivé/abandonné). Des repères marquent les événements (bleu) et les créations de tâches (marron), et le nom des mois sert d'échelle.
- **Tableau récapitulatif** : pour chaque projet de la période — son état (nouveau, toujours en cours, terminé, abandonné), sa durée d'activité, et son nombre d'événements et de tâches, trié du plus actif au moins actif.

C'est l'outil adapté pour préparer un bilan d'activité (par ex. un entretien annuel) : savoir sur quoi vous avez travaillé, ce qui a démarré, ce qui s'est terminé.

---

## Sauvegarder vos données

Vos données vivent dans deux endroits du dossier de l'application :
- `instance/baluchon.db` (projets, événements, tâches, infos)
- `uploads/` (fichiers importés)

Copiez-les régulièrement ailleurs pour les sauvegarder (voir la section correspondante du guide d'installation).

---

Bonne utilisation ! 🎒
