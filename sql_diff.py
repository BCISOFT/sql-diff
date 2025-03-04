#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour comparer la structure de deux fichiers mysqldump.
Affiche uniquement les différences de structure, pas les différences de données.
"""

import sys
import re
import argparse
import os
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Column:
    """Classe représentant une colonne de table SQL."""
    name: str
    data_type: str
    nullable: bool
    default: Optional[str]
    extra: str
    
    def __eq__(self, other):
        if not isinstance(other, Column):
            return False
        return (self.name == other.name and
                self.data_type == other.data_type and
                self.nullable == other.nullable and
                self.default == other.default and
                self.extra == other.extra)
    
    def __hash__(self):
        return hash((self.name, self.data_type, self.nullable, 
                    str(self.default), self.extra))


@dataclass
class Constraint:
    """Classe représentant une contrainte SQL."""
    name: str
    constraint_type: str  # PRIMARY KEY, FOREIGN KEY, UNIQUE, etc.
    columns: List[str]
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None
    
    def __eq__(self, other):
        if not isinstance(other, Constraint):
            return False
        return (self.name == other.name and
                self.constraint_type == other.constraint_type and
                self.columns == other.columns and
                self.referenced_table == other.referenced_table and
                self.referenced_columns == other.referenced_columns)
    
    def __hash__(self):
        return hash((self.name, self.constraint_type, tuple(self.columns), 
                    self.referenced_table, 
                    tuple(self.referenced_columns) if self.referenced_columns else None))


@dataclass
class Table:
    """Classe représentant une table SQL avec ses colonnes et contraintes."""
    name: str
    columns: Dict[str, Column]
    constraints: List[Constraint]
    charset: Optional[str] = None
    collation: Optional[str] = None
    
    def __eq__(self, other):
        if not isinstance(other, Table):
            return False
        return (self.name == other.name and
                self.columns == other.columns and
                set(self.constraints) == set(other.constraints) and
                self.charset == other.charset and
                self.collation == other.collation)


class MySQLDumpParser:
    """Classe pour analyser les fichiers mysqldump."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tables: Dict[str, Table] = {}
        self.parse()
    
    def parse(self):
        """Analyse le fichier mysqldump et extrait les informations de structure."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Le fichier {self.file_path} n'existe pas.")
            
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Trouver toutes les définitions de tables
        create_table_pattern = r"CREATE TABLE\s+`([^`]+)`\s+\(([\s\S]+?)\)\s*(ENGINE[\s\S]+?);(?=\n|$)"
        table_matches = re.finditer(create_table_pattern, content)
        
        for match in table_matches:
            table_name = match.group(1)
            table_definition = match.group(2)
            table_options = match.group(3)
            
            # Extraire les colonnes et contraintes
            columns = {}
            constraints = []
            
            # Extraire le jeu de caractères et la collation
            charset = None
            collation = None
            charset_match = re.search(r"DEFAULT CHARSET=(\w+)", table_options)
            if charset_match:
                charset = charset_match.group(1)
            
            collation_match = re.search(r"COLLATE=(\w+)", table_options)
            if collation_match:
                collation = collation_match.group(1)
            
            # Diviser la définition de la table en lignes
            lines = [line.strip() for line in table_definition.split(',\n')]
            
            # Nettoyer les lignes
            cleaned_lines = []
            current_line = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Gérer les lignes qui peuvent être divisées incorrectement
                if current_line:
                    current_line += ", " + line
                else:
                    current_line = line
                
                # Vérifier si la ligne est complète
                if self._is_line_complete(current_line):
                    cleaned_lines.append(current_line)
                    current_line = ""
            
            if current_line:  # Ajouter la dernière ligne si elle existe
                cleaned_lines.append(current_line)
            
            # Analyser chaque ligne
            for line in cleaned_lines:
                line = line.strip()
                
                # Vérifier si c'est une définition de colonne
                if not line.startswith(('PRIMARY KEY', 'UNIQUE KEY', 'KEY', 'CONSTRAINT', 'FOREIGN KEY')):
                    column_match = re.match(r"`([^`]+)`\s+", line)
                    if column_match:
                        col_name = column_match.group(1)
                        
                        # Extraire le type de données complet
                        rest_of_line = line[column_match.end():]
                        
                        # Gérer les types enum et set spécialement
                        if rest_of_line.lower().startswith(('enum', 'set')):
                            # Trouver la parenthèse fermante correspondante
                            enum_match = re.match(r"(enum|set)\s*\(([^)]+)\)", rest_of_line, re.IGNORECASE)
                            if enum_match:
                                data_type = f"{enum_match.group(1)}({enum_match.group(2)})"
                                attributes = rest_of_line[enum_match.end():].strip()
                            else:
                                # Fallback si on ne peut pas analyser correctement
                                data_type_parts = rest_of_line.split(None, 1)
                                data_type = data_type_parts[0]
                                attributes = data_type_parts[1] if len(data_type_parts) > 1 else ""
                        else:
                            # Pour les autres types de données
                            data_type_parts = rest_of_line.split(None, 1)
                            data_type = data_type_parts[0]
                            attributes = data_type_parts[1] if len(data_type_parts) > 1 else ""
                        
                        # Extraire les attributs de la colonne
                        nullable = "NOT NULL" not in attributes
                        default = None
                        default_match = re.search(r"DEFAULT\s+([^,\s]+)", attributes)
                        if default_match:
                            default = default_match.group(1)
                        
                        extra = ""
                        if "AUTO_INCREMENT" in attributes:
                            extra = "AUTO_INCREMENT"
                        
                        columns[col_name] = Column(col_name, data_type, nullable, default, extra)
                        continue
                
                # Vérifier si c'est une clé primaire
                pk_match = re.match(r"PRIMARY KEY\s+\(([^)]+)\)", line)
                if pk_match:
                    pk_columns = [col.strip('` ') for col in pk_match.group(1).split(',')]
                    constraints.append(Constraint("PRIMARY", "PRIMARY KEY", pk_columns))
                    continue
                
                # Vérifier si c'est une clé unique
                unique_match = re.match(r"UNIQUE KEY\s+`([^`]+)`\s+\(([^)]+)\)", line)
                if unique_match:
                    unique_name = unique_match.group(1)
                    unique_columns = [col.strip('` ') for col in unique_match.group(2).split(',')]
                    constraints.append(Constraint(unique_name, "UNIQUE", unique_columns))
                    continue
                
                # Vérifier si c'est une clé étrangère
                fk_match = re.match(r"CONSTRAINT\s+`([^`]+)`\s+FOREIGN KEY\s+\(([^)]+)\)\s+REFERENCES\s+`([^`]+)`\s+\(([^)]+)\)", line)
                if fk_match:
                    fk_name = fk_match.group(1)
                    fk_columns = [col.strip('` ') for col in fk_match.group(2).split(',')]
                    ref_table = fk_match.group(3)
                    ref_columns = [col.strip('` ') for col in fk_match.group(4).split(',')]
                    constraints.append(Constraint(fk_name, "FOREIGN KEY", fk_columns, ref_table, ref_columns))
                    continue
                
                # Vérifier si c'est un index normal
                idx_match = re.match(r"KEY\s+`([^`]+)`\s+\(([^)]+)\)", line)
                if idx_match:
                    idx_name = idx_match.group(1)
                    idx_columns = [col.strip('` ') for col in idx_match.group(2).split(',')]
                    constraints.append(Constraint(idx_name, "INDEX", idx_columns))
                    continue
            
            # Créer l'objet Table et l'ajouter au dictionnaire
            self.tables[table_name] = Table(table_name, columns, constraints, charset, collation)
    
    def _is_line_complete(self, line: str) -> bool:
        """Vérifie si une ligne de définition est complète."""
        # Cette méthode est simplifiée et pourrait nécessiter plus de logique
        # pour gérer correctement tous les cas
        if line.startswith('CONSTRAINT') and 'REFERENCES' in line and ')' in line.split('REFERENCES')[1]:
            return True
        if line.startswith(('PRIMARY KEY', 'UNIQUE KEY', 'KEY')) and line.endswith(')'):
            return True
        if '`' in line and not line.startswith(('PRIMARY KEY', 'UNIQUE KEY', 'KEY', 'CONSTRAINT', 'FOREIGN KEY')):
            return True
        return False


class SQLDiff:
    """Classe pour comparer deux structures de base de données MySQL."""
    
    def __init__(self, file1: str, file2: str):
        self.parser1 = MySQLDumpParser(file1)
        self.parser2 = MySQLDumpParser(file2)
    
    def compare(self) -> str:
        """Compare les deux structures et retourne un rapport des différences."""
        result = []
        
        # Comparer les tables
        tables1 = set(self.parser1.tables.keys())
        tables2 = set(self.parser2.tables.keys())
        
        # Tables manquantes
        missing_tables = tables1 - tables2
        if missing_tables:
            result.append("Tables présentes dans le premier fichier mais absentes dans le second:")
            for table in sorted(missing_tables):
                result.append(f"  - {table}")
            result.append("")
        
        # Tables supplémentaires
        extra_tables = tables2 - tables1
        if extra_tables:
            result.append("Tables présentes dans le second fichier mais absentes dans le premier:")
            for table in sorted(extra_tables):
                result.append(f"  - {table}")
            result.append("")
        
        # Comparer les tables communes
        common_tables = tables1.intersection(tables2)
        for table_name in sorted(common_tables):
            table1 = self.parser1.tables[table_name]
            table2 = self.parser2.tables[table_name]
            
            table_diff = []
            
            # Comparer les jeux de caractères
            if table1.charset != table2.charset:
                table_diff.append(f"  Différence de jeu de caractères: {table1.charset} -> {table2.charset}")
            
            # Comparer les collations
            if table1.collation != table2.collation:
                table_diff.append(f"  Différence de collation: {table1.collation} -> {table2.collation}")
            
            # Comparer les colonnes
            cols1 = set(table1.columns.keys())
            cols2 = set(table2.columns.keys())
            
            # Colonnes manquantes
            missing_cols = cols1 - cols2
            if missing_cols:
                table_diff.append("  Colonnes supprimées:")
                for col in sorted(missing_cols):
                    table_diff.append(f"    - {col}")
            
            # Colonnes supplémentaires
            extra_cols = cols2 - cols1
            if extra_cols:
                table_diff.append("  Colonnes ajoutées:")
                for col in sorted(extra_cols):
                    table_diff.append(f"    + {col} {table2.columns[col].data_type}")
            
            # Comparer les colonnes communes
            common_cols = cols1.intersection(cols2)
            for col_name in sorted(common_cols):
                col1 = table1.columns[col_name]
                col2 = table2.columns[col_name]
                
                if col1 != col2:
                    table_diff.append(f"  Colonne modifiée: {col_name}")
                    if col1.data_type != col2.data_type:
                        table_diff.append(f"    Type: {col1.data_type} -> {col2.data_type}")
                    if col1.nullable != col2.nullable:
                        nullable1 = "NULL" if col1.nullable else "NOT NULL"
                        nullable2 = "NULL" if col2.nullable else "NOT NULL"
                        table_diff.append(f"    Nullable: {nullable1} -> {nullable2}")
                    if col1.default != col2.default:
                        table_diff.append(f"    Default: {col1.default} -> {col2.default}")
                    if col1.extra != col2.extra:
                        table_diff.append(f"    Extra: {col1.extra} -> {col2.extra}")
            
            # Comparer les contraintes
            constraints1 = {(c.constraint_type, tuple(c.columns)): c for c in table1.constraints}
            constraints2 = {(c.constraint_type, tuple(c.columns)): c for c in table2.constraints}
            
            # Contraintes manquantes
            missing_constraints = set(constraints1.keys()) - set(constraints2.keys())
            if missing_constraints:
                table_diff.append("  Contraintes supprimées:")
                for c_type, c_cols in sorted(missing_constraints):
                    c = constraints1[(c_type, c_cols)]
                    if c.constraint_type == "FOREIGN KEY":
                        table_diff.append(f"    - {c.constraint_type} {c.name} ({', '.join(c.columns)}) REFERENCES {c.referenced_table} ({', '.join(c.referenced_columns)})")
                    else:
                        table_diff.append(f"    - {c.constraint_type} {c.name} ({', '.join(c.columns)})")
            
            # Contraintes supplémentaires
            extra_constraints = set(constraints2.keys()) - set(constraints1.keys())
            if extra_constraints:
                table_diff.append("  Contraintes ajoutées:")
                for c_type, c_cols in sorted(extra_constraints):
                    c = constraints2[(c_type, c_cols)]
                    if c.constraint_type == "FOREIGN KEY":
                        table_diff.append(f"    + {c.constraint_type} {c.name} ({', '.join(c.columns)}) REFERENCES {c.referenced_table} ({', '.join(c.referenced_columns)})")
                    else:
                        table_diff.append(f"    + {c.constraint_type} {c.name} ({', '.join(c.columns)})")
            
            # Ajouter les différences de cette table au résultat
            if table_diff:
                result.append(f"Différences pour la table `{table_name}`:")
                result.extend(table_diff)
                result.append("")
        
        return "\n".join(result) if result else "Aucune différence de structure trouvée."


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Comparer la structure de deux fichiers mysqldump.")
    parser.add_argument("file1", help="Premier fichier mysqldump")
    parser.add_argument("file2", help="Second fichier mysqldump")
    parser.add_argument("-o", "--output", help="Fichier de sortie (par défaut: sortie standard)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux")
    args = parser.parse_args()
    
    try:
        if args.verbose:
            print(f"Analyse du fichier {args.file1}...")
        
        diff = SQLDiff(args.file1, args.file2)
        
        if args.verbose:
            print(f"Analyse du fichier {args.file2}...")
            print("Comparaison des structures...")
        
        result = diff.compare()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            if args.verbose:
                print(f"Résultat écrit dans {args.output}")
        else:
            print(result)
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 