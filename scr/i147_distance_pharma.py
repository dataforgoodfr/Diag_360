import duckdb
import numpy as np
import pandas as pd

from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_dist_soin")


def main():
    with duckdb.connect() as con:
        # chargement des données
        df_dist_pharma = pd.read_csv(raw_dir / "dist_pharma.csv", skiprows=2, sep=";")

        # Création de la table duckdb des epci
        df_epci = load_epci()

        # Changement des noms de colonnes
        mapping_pharma = {
            "Code": "code_insee",
            "Libellé": "nom_commune",
            "Distance à la pharmacie la plus proche 2024": "dist_pharma_min",
        }

        df_dist_pharma = df_dist_pharma.rename(columns=mapping_pharma)

        # On modifie le code_insee de Paris, Marseille et Lyon
        df_dist_pharma["code_insee"] = remap_arrondissements(df_dist_pharma["code_insee"])

        # on remplace les lignes où dist_pharma_min est "'N/A - résultat non disponible' par un vrai NA"
        df_dist_pharma.loc[
            df_dist_pharma["dist_pharma_min"].str.contains("N/A", na=False),
            "dist_pharma_min",
        ] = np.nan
        # on groupe par code_insee en faisant la moyenne ds distance
        df_dist_pharma["dist_pharma_min"] = (
            df_dist_pharma["dist_pharma_min"].str.replace(",", ".").astype(float)
        )
        df_dist_pharma = df_dist_pharma.groupby("code_insee", as_index=False).agg(
            {"dist_pharma_min": "mean"}
        )

        # Jointure des données distance moyenne aux pharmacies par epci
        query_final = """ 
        SELECT
            df_epci.dept_epci AS dept_id,
            df_epci.siren AS id_epci,
            df_epci.epci_nom as epci_lib,
            'i147' AS id_indicator,
            ROUND(AVG(TRY_CAST(dist_pharma_min AS DOUBLE)),2) AS valeur_brute,
            '2024' AS annee
        FROM df_epci
        LEFT JOIN df_dist_pharma
        ON df_epci.code_insee = df_dist_pharma.code_insee
        GROUP BY siren, epci_nom, dept_id
        ORDER BY dept_id, id_epci
        """
        df_dist_pharma_final = con.sql(query_final)

        # Sauvegarde du fichier final
        output_file_final = processed_dir / "i_147_dist_pharma.csv"
        df_dist_pharma_final.write_csv(str(output_file_final))
        print(f"Fichier sauvegardé : {output_file_final}")


if __name__ == "__main__":
    main()
