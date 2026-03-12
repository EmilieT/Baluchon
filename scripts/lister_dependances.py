import os
import re

def lister_dependances_par_fichier(dossier_racine):
    # Extensions à analyser
    extensions = ('.r', '.rmd', '.qmd', '.py', '.pl', '.rb', '.sh')

    # Dictionnaire pour stocker les fichiers et leurs dépendances
    fichiers_et_dependances = {}

    # Parcourir récursivement le dossier
    for racine, _, fichiers in os.walk(dossier_racine):
        for fichier in fichiers:
            # Vérifier si le fichier a une extension valide (insensible à la casse)
            fichier_lower = fichier.lower()
            if any(fichier_lower.endswith(ext) for ext in extensions) and not fichier.startswith('._'):
                chemin_complet = os.path.join(racine, fichier)
                try:
                    with open(chemin_complet, 'r', encoding='utf-8', errors='ignore') as f:
                        contenu = f.read()
                except UnicodeDecodeError:
                    continue  # Ignorer les fichiers qui ne peuvent pas être lus en UTF-8

                # Rechercher les dépendances
                dependances = []

                # Pour les fichiers R, Rmd, Qmd
                if any(fichier_lower.endswith(ext) for ext in ('.r', '.rmd', '.qmd')):
                    dependances += re.findall(r'(?:source|include|read_\w+)\(\s*["\']([^"\']+[/][^"\']+\.(?:r|rmd|qmd|rds|csv|txt))["\']\s*\)', contenu, re.IGNORECASE)
                    dependances += re.findall(r'[\'"]([~/a-zA-Z0-9_\-/]+\/[a-zA-Z0-9_\-.]+(?:\.[a-zA-Z]+)?)[\'"]', contenu, re.IGNORECASE)

                # Pour les fichiers Python
                elif fichier_lower.endswith('.py'):
                    dependances += re.findall(r'(?:from|import)\s+([a-zA-Z0-9_]+)', contenu)
                    dependances += re.findall(r'[\'"]([~/a-zA-Z0-9_\-/]+\/[a-zA-Z0-9_\-.]+(?:\.py)?)[\'"]', contenu, re.IGNORECASE)

                # Pour les fichiers Shell
                elif fichier_lower.endswith('.sh'):
                    dependances += re.findall(r'source\s+([^;\s\/]+[\/][^;\s]+)', contenu)

                # Pour les fichiers Perl
                elif fichier_lower.endswith('.pl'):
                    dependances += re.findall(r'(?:use|require)\s+([a-zA-Z0-9_:]+)', contenu)
                    dependances += re.findall(r'[\'"]([~/a-zA-Z0-9_\-/]+\/[a-zA-Z0-9_\-.]+)[\'"]', contenu, re.IGNORECASE)

                # Pour les fichiers Ruby
                elif fichier_lower.endswith('.rb'):
                    dependances += re.findall(r'(?:require|load)\s+[\'"]([^"\']+[/][^"\']+)[\'"]', contenu)

                # Filtrer les dépendances qui contiennent au moins un `/`
                dependances = [dep for dep in dependances if '/' in dep]

                # Supprimer les doublons
                dependances = list(set(dependances))

                # Filtrer les dépendances qui commencent par `._`
                dependances = [dep for dep in dependances if not os.path.basename(dep).startswith('._')]

                fichiers_et_dependances[chemin_complet] = dependances

    return fichiers_et_dependances

def lister_fichiers_par_dependance(dossier_racine):
    fichiers_et_dependances = lister_dependances_par_fichier(dossier_racine)
    dependances_et_fichiers = {}

    for fichier, deps in fichiers_et_dependances.items():
        for dep in deps:
            if dep not in dependances_et_fichiers:
                dependances_et_fichiers[dep] = []
            dependances_et_fichiers[dep].append(fichier)

    return dependances_et_fichiers

def lister_fichiers_html_par_date(chemin_proj):
    dossier_projet = os.path.dirname(os.path.abspath(chemin_proj))
    fichiers_html = []

    for racine, dirs, fichiers_dans_dossier in os.walk(dossier_projet):
        # Ignorer les dossiers cachés ou spécifiques comme .Rproj.user
        if '.Rproj.user' in racine:
            continue

        for fichier in fichiers_dans_dossier:
            if fichier.endswith('.html') and not fichier.startswith('._') and not fichier.startswith('.'):
                chemin_complet = os.path.join(racine, fichier)
                chemin_relatif = os.path.relpath(chemin_complet, start=dossier_projet)
                date_modification = os.path.getmtime(chemin_complet)
                fichiers_html.append((fichier, chemin_relatif, date_modification))

    # Trier les fichiers par date de modification (du plus récent au plus ancien)
    fichiers_html.sort(key=lambda x: x[2], reverse=True)

    return fichiers_html
    