from io import BytesIO

import duckdb
import pandas as pd

from utils.functions import download_file
from utils.project import load_epci, setup_dirs

raw_dir, processed_dir = setup_dirs("data_sau")


def main():

    # Création de df_epci
    df_epci = load_epci()

    # Téléchagement de la table de la sau
    url = (
        "https://www.data.gouv.fr/api/1/datasets/r/b27d31a6-107b-46ee-8427-518799b488f0"
    )
    content = download_file(url)
    df_sau = pd.read_csv(BytesIO(content), sep=",")

    # Chargement de la table avec les surface des communes
    # URL = (
    #    "https://www.insee.fr/fr/statistiques/fichier/4505239/ODD_PARQUET.zip"
    # )
    # zip_content = download_file(URL)
    # with zipfile.ZipFile(BytesIO(zip_content)) as z:
    #    with z.open("catnat_gaspar.csv") as f:
    #        df_cat_nat = pd.read_csv(f, sep=";", low_memory=False)

    df_communes = duckdb.read_parquet(str(raw_dir / "ODD_COM.parquet"))

    # Traitement de la table sau
    df_sau = df_sau[df_sau["date_mesure"].str.startswith("2020")].copy()
    df_sau["geocode_commune"] = df_sau["geocode_commune"].astype(str).str.zfill(5)

    # Traitement de la table des communes pour ne garder que les codes insee et les surfaces
    query = """ 
    SELECT 
        codgeo,
        libgeo,
        A2021 AS surface
    FROM df_communes
    WHERE variable = 'surface'
    """

    df_surf_com = duckdb.sql(query)

    query = """
    SELECT
        dept_epci as dept_id,
        siren as id_epci,
        epci_nom AS lib_epci,
        'i113' AS id_indicator,
        ROUND(sum(df_sau.valeur/100) / sum(surface)  * 100,3) AS valeur_brute,
        '2020' AS annee
    FROM df_epci
    LEFT JOIN df_surf_com 
        ON df_epci.code_insee = df_surf_com.codgeo
    LEFT JOIN df_sau
        ON df_epci.code_insee = df_sau.geocode_commune
    GROUP BY siren, dept_epci, epci_nom
    ORDER BY dept_epci, siren
    """

    df_sau_final = duckdb.sql(query)
    output_path_complete = processed_dir / "i113_part_sau.csv"
    df_sau_final.write_csv(str(output_path_complete))
    print(f"Données complètes sauvegardées dans {output_path_complete}")


if __name__ == "__main__":
    main()
