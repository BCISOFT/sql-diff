# SQL-Diff

Un outil en ligne de commande pour comparer la structure de deux fichiers mysqldump.

## Fonctionnalités

Cet outil analyse et compare deux fichiers mysqldump et affiche uniquement les différences de structure, en ignorant les différences de données. Il détecte les différences suivantes :

- Tables manquantes ou supplémentaires
- Colonnes manquantes, supplémentaires ou modifiées
- Contraintes (clés primaires, clés étrangères, index, etc.) manquantes ou supplémentaires
- Différences de jeu de caractères ou de collation

## Prérequis

- Python 3.6 ou supérieur

## Installation

Clonez ce dépôt ou téléchargez les fichiers, puis rendez le script exécutable :

```bash
chmod +x sql_diff.py
```

## Utilisation

```bash
./sql_diff.py fichier1.sql fichier2.sql [options]
```

Où :
- `fichier1.sql` est le chemin vers le premier fichier mysqldump
- `fichier2.sql` est le chemin vers le second fichier mysqldump

### Options

- `-o, --output FICHIER` : Écrit le résultat dans un fichier au lieu de l'afficher sur la sortie standard
- `-v, --verbose` : Active le mode verbeux qui affiche des informations supplémentaires pendant l'exécution

### Exemples

Comparer deux fichiers et afficher le résultat :
```bash
./sql_diff.py db1.sql db2.sql
```

Comparer deux fichiers et enregistrer le résultat dans un fichier :
```bash
./sql_diff.py db1.sql db2.sql -o resultat.txt
```

Comparer deux fichiers en mode verbeux :
```bash
./sql_diff.py db1.sql db2.sql -v
```

## Exemple de sortie

```
Tables présentes dans le premier fichier mais absentes dans le second:
  - utilisateurs_archive

Tables présentes dans le second fichier mais absentes dans le premier:
  - utilisateurs_nouveaux
  - categories

Différences pour la table `utilisateurs`:
  Différence de collation: utf8mb4_general_ci -> utf8mb4_unicode_ci
  Colonnes supprimées:
    - date_naissance
  Colonnes ajoutées:
    + age int
  Colonne modifiée: email
    Type: varchar(100) -> varchar(255)
    Nullable: NOT NULL -> NULL
    Default: None -> NULL
  Contraintes supprimées:
    - UNIQUE idx_email (email)
  Contraintes ajoutées:
    + INDEX idx_nom (nom, prenom)

Différences pour la table `commandes`:
  Colonnes ajoutées:
    + statut enum('en_attente','payee','expediee','livree','annulee')
```

## Limitations

- Le script est conçu pour analyser les fichiers mysqldump générés avec l'option `--no-data` ou similaire.
- Certaines constructions SQL complexes pourraient ne pas être correctement analysées.
- Les vues, procédures stockées et déclencheurs ne sont pas pris en compte dans la comparaison.

## Licence

Ce projet est sous licence MIT. 