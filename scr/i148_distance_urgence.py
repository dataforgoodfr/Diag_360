import duckdb
import numpy as np
import pandas as pd

from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_dist_soin")


def main():
    with duckdb.connect() as con:
        # chargement des données des urgences
        df_dist_urg = pd.read_csv(raw_dir / "dist_urgence.csv", skiprows=2, sep=";")

        # Création de la table duckdb des epci
        df_epci = load_epci()

        # Changement des noms de colonnes
        mapping_urg = {
            "Code": "code_insee",
            "Libellé": "nom_commune",
            "Distance à la structure la plus proche 2024": "dist_urgence_min",
        }

        df_dist_urg = df_dist_urg.rename(columns=mapping_urg)

        # On modifie le code_insee de Paris, Marseille et Lyon
        df_dist_urg["code_insee"] = remap_arrondissements(df_dist_urg["code_insee"])

        # on supprime les lignes où dist_urg_min est "'N/A - résultat non disponible'"
        df_dist_urg.loc[
            df_dist_urg["dist_urgence_min"].str.contains("N/A", na=False),
            "dist_urgence_min",
        ] = np.nan

        # on groupe par code_insee en faisant la moyenne des distances
        df_dist_urg["dist_urgence_min"] = (
            df_dist_urg["dist_urgence_min"].str.replace(",", ".").astype(float)
        )
        df_dist_urg = df_dist_urg.groupby("code_insee", as_index=False).agg(
            {"dist_urgence_min": "mean"}
        )

        query_final = """ 
        SELECT
            df_epci.dept_epci AS dept_id,
            df_epci.siren AS id_epci,
            df_epci.epci_nom AS epci_lib,
            'i148' AS id_indicator,
            ROUND(AVG(TRY_CAST(dist_urgence_min AS DOUBLE)),2) AS valeur_brute,
            '2024' AS annee
        FROM df_epci
        LEFT JOIN df_dist_urg
        ON df_epci.code_insee = df_dist_urg.code_insee
        GROUP BY siren, epci_nom, dept_id
        ORDER BY dept_id, id_epci
        """

        df_dist_urg_moy = con.sql(query_final)
        print(f"taille df_dist_urg_moy: {df_dist_urg_moy.shape}")

        # sauvegarde du fichier final
        output_file_moy = processed_dir / "i_148_dist_urgence.csv"
        df_dist_urg_moy.write_csv(str(output_file_moy))
        print(f"Fichier sauvegardé : {output_file_moy}")


if __name__ == "__main__":
    main()
