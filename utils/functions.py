import logging
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests


def download_file(url: str) -> bytes:
    """Télécharge le fichier et retourne son contenu en mémoire"""
    logger = logging.getLogger(__name__)
    logger.info(f"Téléchargement du fichier : {url}")
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        content = response.content
    logger.info("Fichier téléchargé avec succès")
    return content


def download_stock_file(url: str, extract_to: str = ".", filename: str = None) -> None:
    """
    Télécharge un fichier depuis une URL et l'enregistre localement.

    Le fichier est téléchargé uniquement s'il n'existe pas déjà
    dans le répertoire de destination.

    Parameters
    ----------
    url : str
        URL du fichier à télécharger.
    extract_to : str, optional
        Répertoire de destination du fichier (par défaut : répertoire courant).
    filename : str
        Nom du fichier local (avec extension).
    """

    # Création du dossier si nécessaire
    extract_to = Path(extract_to)
    if not extract_to.exists():
        extract_to.mkdir(parents=True, exist_ok=True)
        print(f"Dossier créé : {extract_to}")

    file_path = extract_to / filename

    if not file_path.exists():
        print(f"Téléchargement du fichier : {file_path}")
        response = requests.get(url)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"Fichier téléchargé avec succès : {file_path}")
    else:
        print(f"Fichier déjà présent : {file_path}")


def extract_zip_from_bytes(zip_bytes: bytes, extract_to: str = ".") -> None:
    """
    Extrait le contenu d'une archive ZIP fournie en mémoire.

    Parameters
    ----------
    zip_bytes : bytes
        Contenu binaire de l'archive ZIP.
    extract_to : str, optional
        Répertoire de destination (par défaut : courant).
    """

    with zipfile.ZipFile(BytesIO(zip_bytes)) as z:
        z.extractall(extract_to)

    print(f"Extraction terminée dans le dossier : {extract_to}")


def extract_zip(zip_filename: str, extract_to: str = ".") -> None:
    """
    Extrait le contenu d'une archive ZIP dans un répertoire cible.

    Parameters
    ----------
    zip_filename : str
        Chemin vers le fichier ZIP à extraire.
    extract_to : str, optional
        Répertoire de destination des fichiers extraits
        (par défaut : répertoire courant).

    Raises
    ------
    FileNotFoundError
        Si le fichier ZIP n'existe pas.
    zipfile.BadZipFile
        Si le fichier fourni n'est pas une archive ZIP valide.
    """

    with zipfile.ZipFile(zip_filename, "r") as z:
        z.extractall(extract_to)
    print(f"Extraction terminée dans le dossier : {extract_to}")


def load_csv_to_duckdb(file_path, table_name, con):
    """
    Charge un fichier CSV dans DuckDB sous forme de table.

    Le fichier CSV est lu automatiquement par DuckDB à l'aide de
    `read_csv_auto`, qui infère les types de colonnes.

    Parameters
    ----------
    file_path : str
        Chemin vers le fichier CSV à importer.
    table_name : str
        Nom de la table DuckDB à créer.
    con : duckdb.DuckDBPyConnection
        Connexion DuckDB active.

    Notes
    -----
    - La table est créée à partir du contenu du CSV.
    - Si une table du même nom existe déjà, une erreur sera levée.
    """

    con.execute(
        f"""
        CREATE OR REPLACE TABLE {table_name} AS 
        SELECT * FROM read_csv_auto('{file_path}',header=True,delim=',)
        """
    )


def float_to_codepostal(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Convertit une colonne contenant des codes postaux numériques en format chaîne à 5 caractères.

    Cette fonction est destinée aux cas où les codes postaux ont été lus comme
    des nombres flottants (ex. `1400.0`) et doivent être restaurés en chaînes
    avec zéros initiaux (ex. `01400`).

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame contenant la colonne à transformer.
    col : str
        Nom de la colonne contenant les codes postaux.

    Returns
    -------
    pandas.DataFrame
        DataFrame avec la colonne des codes postaux convertie en chaînes
        de longueur 5.
    """

    df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.zfill(5)
    return df


def homogene_nan(df):
    cols = ["adrs_codeinsee", "adrs_codepostal"]
    invalid_values = ["nan", "<NA>", "NaN", "Nan", "0", "0.0", "", "INSEE", "commune"]
    for col in cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(invalid_values, pd.NA)
        df = float_to_codepostal(df, col)
    return df


def create_dataframe_communes():
    com_url = (
        "https://www.data.gouv.fr/api/1/datasets/r/f5df602b-3800-44d7-b2df-fa40a0350325"
    )
    content = download_file(com_url)
    print("Fichier des communes téléchargé")
    df_com = pd.read_csv(BytesIO(content))
    df_com = float_to_codepostal(df_com, "code_postal")
    print("Dataframe communes créé")
    return df_com


def create_dataframe_epci():
    epci_url = (
        "https://www.data.gouv.fr/api/1/datasets/r/6e05c448-62cc-4470-aa0f-4f31adea0bc4"
    )
    content = download_file(epci_url)

    df_epci = pd.read_csv(BytesIO(content), sep=";", encoding="latin1")
    print("Dataframe EPCI créé")
    return df_epci


def create_full(path_folder):
    """
    Lit tous les fichiers CSV d'un dossier, filtre certaines colonnes,
    concatène les résultats et supprime chaque fichier après lecture.

    Parameters
    ----------
    path_folder : str
        Chemin vers le dossier contenant les fichiers CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame complet avec les colonnes 'adrs_codeinsee' et 'adrs_codepostal'
        pour les lignes où 'position' == 'A'.
    """
    df_full = pd.DataFrame()

    for file_path in sorted(Path(path_folder).glob("rna_waldec*.csv")):
        # Lire le CSV
        df_temp = pd.read_csv(file_path, sep=";")
        print(f"Fichier lu : {file_path} avec {len(df_temp)} lignes.")
        df_temp = df_temp.loc[
            df_temp["position"] == "A"
        ]  # filtre les association en activité
        df_temp = df_temp[["adrs_codeinsee", "adrs_codepostal"]]

        # Concaténer dans le DataFrame complet
        df_full = pd.concat([df_full, df_temp], ignore_index=True, axis=0)

        # Supprimer le fichier après lecture
        file_path.unlink()

    print("Dataframe complet créé.")
    return df_full
