#!/usr/bin/env python3
"""
Script d'ingestion des régions françaises dans PostgreSQL
Source: https://geo.api.gouv.fr/regions
"""

import requests
import psycopg2
from psycopg2 import sql
from typing import List, Dict
import logging
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_regions() -> List[Dict[str, str]]:
    """
    Récupère les données des régions depuis l'API gouvernementale.
    
    Returns:
        Liste des régions avec 'code' et 'nom'
    """
    try:
        logger.info("Récupération des régions depuis l'API...")
        response = requests.get('https://geo.api.gouv.fr/regions')
        response.raise_for_status()
        regions = response.json()
        logger.info(f"{len(regions)} régions récupérées")
        return regions
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la récupération des régions: {e}")
        raise


def create_connection(
    host: str = None,
    database: str = None,
    user: str = None,
    password: str = None,
    port: int = 5432
) -> psycopg2.extensions.connection:
    """
    Crée une connexion à la base de données PostgreSQL.
    
    Les paramètres peuvent être passés ou lus depuis les variables d'environnement:
    - DB_HOST
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    - DB_PORT
    
    Args:
        host: Hôte PostgreSQL
        database: Nom de la base de données
        user: Nom d'utilisateur
        password: Mot de passe
        port: Port PostgreSQL
        
    Returns:
        Objet de connexion psycopg2
    """
    # Utiliser les variables d'environnement par défaut
    host = host or os.getenv('DB_HOST', 'localhost')
    database = database or os.getenv('DB_NAME', 'regions_db')
    user = user or os.getenv('DB_USER', 'postgres')
    password = password or os.getenv('DB_PASSWORD', 'password')
    port = port or int(os.getenv('DB_PORT', 5432))
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        logger.info(f"Connexion établie à {user}@{host}:{port}/{database}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        raise


def create_table(conn: psycopg2.extensions.connection) -> None:
    """
    Crée la table region si elle n'existe pas.
    
    Args:
        conn: Connexion psycopg2
    """
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS region (
            code_reg VARCHAR(10) PRIMARY KEY,
            nom VARCHAR(255) NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    logger.info("Table region créée ou vérifiée")


def insert_regions(conn: psycopg2.extensions.connection, regions: List[Dict[str, str]]) -> None:
    """
    Insère les régions dans la base de données.
    
    Args:
        conn: Connexion psycopg2
        regions: Liste des régions à insérer
    """
    cursor = conn.cursor()
    
    # Suppression des données existantes
    cursor.execute('DELETE FROM region')
    logger.info("Données existantes supprimées")
    
    # Insertion des nouvelles données avec psycopg2.sql pour plus de sécurité
    inserted = 0
    for region in regions:
        try:
            cursor.execute(
                sql.SQL('INSERT INTO region (code_reg, nom) VALUES (%s, %s)'),
                (region['code'], region['nom'])
            )
            inserted += 1
        except psycopg2.Error as e:
            logger.warning(f"Erreur lors de l'insertion de {region['nom']}: {e}")
    
    conn.commit()
    cursor.close()
    logger.info(f"{inserted}/{len(regions)} régions insérées avec succès")


def verify_data(conn: psycopg2.extensions.connection) -> None:
    """
    Vérifie les données insérées.
    
    Args:
        conn: Connexion psycopg2
    """
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM region')
    count = cursor.fetchone()[0]
    logger.info(f"Vérification: {count} régions dans la base de données")
    
    cursor.execute('SELECT code_reg, nom FROM region ORDER BY code_reg LIMIT 5')
    logger.info("Premiers enregistrements:")
    for row in cursor.fetchall():
        logger.info(f"  {row[0]}: {row[1]}")
    
    cursor.close()


def main(
    host: str = None,
    database: str = None,
    user: str = None,
    password: str = None,
    port: int = 5432
) -> None:
    """
    Fonction principale pour orchestrer l'ingestion.
    
    Args:
        host: Hôte PostgreSQL
        database: Nom de la base de données
        user: Nom d'utilisateur
        password: Mot de passe
        port: Port PostgreSQL
    """
    try:
        # Récupération des données
        regions = fetch_regions()
        
        # Connexion à la base de données
        conn = create_connection(host, database, user, password, port)
        
        # Création de la table
        create_table(conn)
        
        # Insertion des données
        insert_regions(conn, regions)
        
        # Vérification
        verify_data(conn)
        
        # Fermeture de la connexion
        conn.close()
        logger.info("Ingestion terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion: {e}")
        raise


if __name__ == '__main__':
    main()