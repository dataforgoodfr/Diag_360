import zipfile
from io import BytesIO

import duckdb
import pandas as pd

from utils.functions import download_file
from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_cat_nat")


def main():
    with duckdb.connect() as con:
        # Define URLs and file paths
        URL = "https://www.data.gouv.fr/api/1/datasets/r/d6fb9e18-b66b-499c-8284-46a3595579cc"
        zip_content = download_file(URL)
        with zipfile.ZipFile(BytesIO(zip_content)) as z:
            with z.open("catnat_gaspar.csv") as f:
                df_cat_nat = pd.read_csv(f, sep=";", low_memory=False)

        # Création de la table duckdb des epci
        df_epci = load_epci()

        # On modifie les code insee de Paris, Lyon, Marseille pour les faire correspondre à ceux de l'INSEE
        df_cat_nat["cod_commune"] = remap_arrondissements(df_cat_nat["cod_commune"])

        # nombre de cat nat par commune sur 40 ans
        query = """
        SELECT 
            cod_commune AS code_insee, 
            count(*) AS nb_cat_nat
        FROM df_cat_nat
        GROUP BY cod_commune
        """
        df_cat_nat_communes = con.sql(query).df()
        print(f"df_cat_nat_communes.shape: {df_cat_nat_communes.shape}")

        # Surface de chaque epci et nb de cat nat par epci sur 40 ans
        query = """
        WITH df_temp AS (
        SELECT 
            df_epci.siren AS siren,
            sum(df_cat_nat_communes.nb_cat_nat) as nb_cat_nat_total,
            sum(df_epci.superficie_km2) as superficie_km2
        FROM df_epci
        LEFT JOIN df_cat_nat_communes
        ON df_epci.code_insee = df_cat_nat_communes.code_insee
        GROUP BY df_epci.siren
        )

        SELECT 
            siren,
            ROUND(nb_cat_nat_total / superficie_km2, 3) AS cat_nat_per_km2
        FROM df_temp
        """

        df_cat_nat_temp = con.sql(query)
        print(f"df_cat_nat_temp.shape: {df_cat_nat_temp.shape}")

        # Ajout du nom des epci
        query_complete = """
        SELECT 
            df_epci.dept_epci as dept_id,
            CAST(df_epci.siren AS VARCHAR) as id_epci,
            df_epci.epci_nom as epci_lib,
            'i158' AS id_indicator,
            df_cat_nat_temp.cat_nat_per_km2 as valeur_brute,
            '2025' AS annee
        FROM df_epci
        LEFT JOIN df_cat_nat_temp
        ON df_cat_nat_temp.siren = df_epci.siren
        GROUP BY df_epci.dept_epci, df_epci.siren, df_epci.epci_nom, df_cat_nat_temp.cat_nat_per_km2
        ORDER BY df_epci.dept_epci, df_epci.siren
        """

        df_cat_nat_final = con.sql(query_complete)
        print(f"df_cat_nat_final.shape: {df_cat_nat_final.shape}")

        # Sauvegarde du fichier final
        output_file = processed_dir / "i158_cat_nat_per_epci.csv"
        df_cat_nat_final.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")

        # NB_cat_nat
        query = """ 
        SELECT 
            df_epci.dept_epci as dept_id,
            df_epci.siren AS siren,
            df_epci.epci_nom as epci_lib,
            sum(df_cat_nat_communes.nb_cat_nat) as nb_cat_nat_total
        FROM df_epci
        LEFT JOIN df_cat_nat_communes
        ON df_epci.code_insee = df_cat_nat_communes.code_insee
        GROUP BY df_epci.siren, df_epci.dept_epci, df_epci.epci_nom
        ORDER BY df_epci.dept_epci, df_epci.siren
        """

        df_cat_nat_nb = con.sql(query)
        print(f"df_cat_nat_nb.shape: {df_cat_nat_nb.shape}")

        # Sauvegarde du fichier final
        output_file = processed_dir / "nb_cat_nat_per_epci.csv"
        df_cat_nat_nb.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()  # asso.py
