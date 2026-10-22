from pathlib import Path

import duckdb

from utils.download_data import download_data
from utils.format_file import format_file
from utils.project import load_epci

base_dir = Path(__file__).resolve().parent.parent  # racine du projet diag360
raw_dir = base_dir / "data" / "raw"
processed_dir = base_dir / "data" / "processed"

processed_dir.mkdir(parents=True, exist_ok=True)

URL = "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/530_l-accessibilite-potentielle-localisee-apl/attachments/indicateur_d_accessibilite_potentielle_localisee_apl_aux_chirurgiens_dentistes_xlsx/"
FILENAME = "data_apl_chirurgiens_dentiste.xlsx"


def main():
    # Téléchargement du fichier APL aux chirurgiens-dentistes
    download = download_data(url=URL, name_file_saved=FILENAME, save_path=raw_dir)
    download.dict_download_file()

    # Chargement de la table des epci
    df_epci = load_epci()

    # Formatage du fichier reçu pour avoir un dataframe exploitable
    df_chirurgiens_dentiste = format_file(
        path=download.save_path / FILENAME, extension="xlsx"
    ).read_file()

    # On modifie le code_insee de Paris pour mettre 75056
    df_chirurgiens_dentiste["Code commune INSEE"] = (
        df_chirurgiens_dentiste["Code commune INSEE"]
        .astype(str)
        .apply(lambda x: "75056" if x.startswith("75") else x)
    )

    # Jointure avec les communes et EPCI pour le format final
    output_file = processed_dir / "i069_apl_chirurgiens_dentiste_clean.csv"
    query = f"""
    COPY (
    SELECT
        c.dept_epci AS dept_id,
        c.siren AS id_epci,
        c.epci_nom AS epci_lib,
        'i069' AS id_indicator,
        ROUND(sum(CAST(#3 AS float) * CAST(#4 AS float)) / sum(CAST(#4 AS float)), 1) AS valeur_brute,
        '2025' AS annee
    FROM df_epci AS c
    LEFT JOIN df_chirurgiens_dentiste AS d
        ON d."Code commune INSEE" = c.code_insee
    GROUP BY c.dept_epci, c.siren, c.epci_nom
    ORDER BY c.dept_epci, c.siren
    )
    TO '{output_file}' (HEADER, DELIMITER ';');
    """
    duckdb.sql(query)
    print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()
