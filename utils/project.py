from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent  # racine du projet diag360

# Préfixe des codes INSEE des arrondissements -> code INSEE de la commune
ARRONDISSEMENTS = {"75": "75056", "132": "13055", "693": "69123"}


def setup_dirs(data_subdir: str) -> tuple[Path, Path]:
    """
    Crée (si besoin) et retourne les dossiers raw et processed d'un indicateur.

    Parameters
    ----------
    data_subdir : str
        Nom du dossier de l'indicateur dans `data/` (ex. "data_asso").

    Returns
    -------
    tuple[Path, Path]
        (raw_dir, processed_dir) = (data/<data_subdir>/raw, data/<data_subdir>/processed)
    """
    data_dir = BASE_DIR / "data" / data_subdir
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir, processed_dir


def load_epci() -> pd.DataFrame:
    """Charge la table des communes membres des EPCI (data/processed/epci_membres.csv)."""
    return pd.read_csv(BASE_DIR / "data" / "processed" / "epci_membres.csv", sep=",")


def load_communes(**kwargs) -> pd.DataFrame:
    """
    Charge la table des communes (data/raw/communes_france_2025.csv).

    Les arguments nommés sont transmis à `pd.read_csv` (ex. `low_memory=False`).
    """
    kwargs.setdefault("sep", ",")
    return pd.read_csv(BASE_DIR / "data" / "raw" / "communes_france_2025.csv", **kwargs)


def remap_arrondissements(codes: pd.Series) -> pd.Series:
    """
    Remplace les codes INSEE des arrondissements de Paris, Lyon et Marseille
    par celui de la commune (75056, 69123, 13055), comme dans la table des EPCI.

    Les valeurs manquantes sont conservées.

    Parameters
    ----------
    codes : pandas.Series
        Codes INSEE (chaînes de caractères).

    Returns
    -------
    pandas.Series
        Série de même index, avec les codes d'arrondissements remplacés.
    """
    as_str = codes.astype(str)
    for prefix, code_commune in ARRONDISSEMENTS.items():
        codes = codes.mask(as_str.str.startswith(prefix), code_commune)
    return codes
