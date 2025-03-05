#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour traiter un fichier dump MySQL:
- Lister toutes les tables présentes dans le dump
- Créer une version du dump sans les données (INSERT) pour une ou plusieurs tables spécifiques
- Peut lire depuis STDIN et écrire sur STDOUT
"""

import argparse
import re
import sys


def list_tables(input_stream, is_file=True):
    """Liste toutes les tables présentes dans le fichier dump ou depuis STDIN."""
    tables = []
    create_table_pattern = re.compile(r'CREATE TABLE `([^`]+)`')
    
    try:
        if is_file:
            with open(input_stream, 'r', encoding='utf-8') as f:
                for line in f:
                    match = create_table_pattern.search(line)
                    if match:
                        tables.append(match.group(1))
        else:
            # Lecture depuis STDIN
            for line in input_stream:
                match = create_table_pattern.search(line)
                if match:
                    tables.append(match.group(1))
        
        if tables:
            source = input_stream if is_file else "STDIN"
            print(f"Tables trouvées dans le dump {source}:")
            for table in tables:
                print(f"- {table}")
        else:
            source = input_stream if is_file else "STDIN"
            print(f"Aucune table trouvée dans {source}")
            
    except FileNotFoundError:
        print(f"Erreur: Le fichier {input_stream} n'existe pas.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de la lecture: {e}", file=sys.stderr)
        sys.exit(1)


def remove_tables_data(input_stream, table_names, output_stream=None, is_file_input=True, is_file_output=True):
    """
    Crée une version du dump où les données (INSERT) d'une ou plusieurs tables spécifiques sont supprimées,
    tout en conservant toutes les tables et leurs structures.
    
    Args:
        input_stream: Chemin du fichier d'entrée ou sys.stdin
        table_names: Liste des noms de tables dont on veut supprimer les données
        output_stream: Chemin du fichier de sortie ou None pour sys.stdout
        is_file_input: True si input_stream est un chemin de fichier, False si c'est sys.stdin
        is_file_output: True si output_stream est un chemin de fichier, False si c'est sys.stdout
    """
    output_lines = []
    tables_found = set()
    insert_pattern = re.compile(r'INSERT INTO `([^`]+)`')
    create_table_pattern = re.compile(r'CREATE TABLE `([^`]+)`')
    
    try:
        # Lecture du dump
        if is_file_input:
            with open(input_stream, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            # Lecture depuis STDIN
            lines = input_stream.readlines()
        
        # Traitement des lignes
        for line in lines:
            # Vérifie si la ligne est une instruction INSERT pour une des tables cibles
            match = insert_pattern.search(line)
            if match and match.group(1) in table_names:
                # Ignore cette ligne car c'est un INSERT pour une table cible
                continue
            else:
                # Conserve toutes les autres lignes
                output_lines.append(line)
            
            # Vérifie si les tables existent dans le dump
            match = create_table_pattern.search(line)
            if match and match.group(1) in table_names:
                tables_found.add(match.group(1))
        
        # Écriture du résultat
        if is_file_output and output_stream:
            with open(output_stream, 'w', encoding='utf-8') as f:
                f.writelines(output_lines)
            print(f"Le dump a été créé avec succès dans le fichier '{output_stream}'.")
        else:
            # Écriture sur STDOUT
            sys.stdout.writelines(output_lines)
        
        # Affiche les tables qui n'ont pas été trouvées
        tables_not_found = set(table_names) - tables_found
        if tables_not_found:
            if len(tables_not_found) == 1:
                print(f"Attention: La table '{next(iter(tables_not_found))}' n'a pas été trouvée dans le dump.", file=sys.stderr)
            else:
                print(f"Attention: Les tables suivantes n'ont pas été trouvées dans le dump: {', '.join(tables_not_found)}", file=sys.stderr)
        
        if is_file_output and output_stream:
            if len(tables_found) == 1:
                print(f"Toutes les tables ont été conservées, mais les données de la table '{next(iter(tables_found))}' ont été supprimées.")
            elif len(tables_found) > 1:
                print(f"Toutes les tables ont été conservées, mais les données des tables suivantes ont été supprimées: {', '.join(tables_found)}")
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {input_stream} n'existe pas.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lors du traitement: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Traite un fichier dump MySQL pour lister les tables ou supprimer les données d\'une ou plusieurs tables spécifiques.')
    parser.add_argument('dump_file', nargs='?', help='Chemin vers le fichier dump MySQL. Utilisez - pour lire depuis STDIN.')
    parser.add_argument('-t', '--table', action='append', dest='tables', help='Nom d\'une table dont on veut supprimer les données. Peut être spécifié plusieurs fois.')
    parser.add_argument('-l', '--list', action='store_true', help='Liste toutes les tables présentes dans le dump')
    parser.add_argument('-o', '--output', help='Fichier de sortie. Si non spécifié, le résultat est écrit sur STDOUT.')
    
    args = parser.parse_args()
    
    # Déterminer si on lit depuis un fichier ou STDIN
    is_file_input = True
    if not args.dump_file or args.dump_file == '-':
        is_file_input = False
        input_stream = sys.stdin
    else:
        input_stream = args.dump_file
    
    # Déterminer si on écrit dans un fichier ou sur STDOUT
    is_file_output = bool(args.output)
    output_stream = args.output
    if not output_stream and is_file_input and args.tables and not args.list:
        # Génère un nom de fichier par défaut si on lit depuis un fichier et qu'aucun fichier de sortie n'est spécifié
        table_suffix = "_".join(args.tables) if len(args.tables) <= 3 else f"{args.tables[0]}_and_{len(args.tables)-1}_others"
        output_stream = f"{args.dump_file.rsplit('.', 1)[0]}_{table_suffix}_no_data.sql"
        is_file_output = True
    
    if args.list:
        list_tables(input_stream, is_file=is_file_input)
    elif args.tables:
        remove_tables_data(input_stream, args.tables, output_stream, is_file_input, is_file_output)
    else:
        parser.print_help()
        print("\nErreur: Vous devez spécifier soit l'option --list pour lister les tables, soit l'option --table pour supprimer les données d'une ou plusieurs tables.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main() 