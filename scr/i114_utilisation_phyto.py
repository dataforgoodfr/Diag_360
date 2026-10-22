from io import BytesIO

import duckdb
import pandas as pd

from utils.functions import download_file, download_stock_file
from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_phyto")


def main():
    with duckdb.connect() as con:
        # Téléchargement de la table epci
        df_epci = load_epci()

        # Téléchagement de la table de la sau
        url = "https://www.data.gouv.fr/api/1/datasets/r/b27d31a6-107b-46ee-8427-518799b488f0"
        content = download_file(url)
        df_sau = pd.read_csv(BytesIO(content), sep=",")
        print(df_sau.head())

        # Téléchargement de la table phyto
        url_phyto = "https://www.data.gouv.fr/api/1/datasets/r/a1fe6b6c-4658-4c24-a8d8-dec530bcfc7c"

        # download_stock_file(url: str, extract_to: str = ".", filename: str = None)
        download_stock_file(url_phyto, raw_dir, "achat_commune_phyto.parquet")
        print("coucou")
        df_phyto = con.read_parquet(str(raw_dir / "achat_commune_phyto.parquet"))

        # traitement de df_sau : on ajoute des zéros et on corrige les codes insee de Paris, Lyon, Marseille pour les faire correspondre à ceux de l'INSEE
        df_sau["geocode_commune"] = df_sau["geocode_commune"].apply(lambda x: str(x).zfill(5))
        df_sau["geocode_commune"] = remap_arrondissements(df_sau["geocode_commune"])

        # Correction de Paris, Lyon, Marseille dans df_phyto
        df_phyto = con.sql("""
        SELECT
            *,
            CASE
                WHEN code_insee LIKE '75%'  THEN '75056'
                WHEN code_insee LIKE '132%' THEN '13055'
                WHEN code_insee LIKE '693%' THEN '69123'
                ELSE code_insee
            END AS code_insee
        FROM df_phyto
    """)

        # Préparation de df_sau : on ne garde que 2020
        query_sau = """ 
        SELECT 
            df_epci.siren,
            ROUND(SUM(TRY_CAST(valeur AS DOUBLE)), 2) AS sau_ha
        FROM df_sau
        LEFT JOIN df_epci
        ON df_sau.geocode_commune = df_epci.code_insee
        WHERE date_mesure LIKE '2020%'
        GROUP BY df_epci.siren
        """
        df_sau = con.sql(query_sau)

        # Jointure entre df_epci et df_phyto
        query = """
        SELECT 
            df_phyto.annee,
            df_epci.siren,
            TRY_CAST(df_phyto.quantite_substance AS DOUBLE) AS quantite_substance
        FROM df_epci 
        INNER JOIN df_phyto 
        ON df_epci.code_insee = df_phyto.code_insee
        """

        df_phyto_merged = con.sql(query)

        # Calcul de la moyenne annuelle par EPCI
        query_avg = """ 
        WITH df_temp AS (
            SELECT
                siren,
                COUNT(DISTINCT annee) AS n_years,
                SUM(quantite_substance) AS total_quantite_substance
            FROM df_phyto_merged
            GROUP BY siren
        )

        SELECT
            siren,
            (1.0*total_quantite_substance / n_years) AS avg_annual_phyto
        FROM df_temp
        """

        avg_annual_phyto = con.sql(query_avg)

        query_bdd = """
        WITH epci AS (
        SELECT 
            DISTINCT siren, 
            dept_epci, 
            epci_nom 
        FROM df_epci)
    
        SELECT
            epci.dept_epci AS dept_id,
            epci.siren AS id_epci,
            epci.epci_nom AS epci_lib,
            'i114' AS id_indicator,
            ROUND((1.0 * aap.avg_annual_phyto / ds.sau_ha), 3) AS valeur_brute,
            '2023' AS annee
        FROM epci
        LEFT JOIN avg_annual_phyto AS aap
            ON epci.siren = aap.siren
        LEFT JOIN df_sau AS ds
            ON epci.siren = ds.siren
        ORDER BY epci.dept_epci, epci.siren
        """

        df_final = con.sql(query_bdd)

        # Sauvegarde du fichier final
        output_path = processed_dir / "i114_kg_phyto_per_ha_sau.csv"
        df_final.write_csv(str(output_path))
        print(f"Fichier sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
