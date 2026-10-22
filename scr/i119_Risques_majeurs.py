from pathlib import Path

import duckdb
import pandas as pd

from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("risques_majeurs")


def prepare_df_risque() -> tuple[pd.DataFrame, Path]:
    """Charge et nettoie les données de risques majeurs"""

    # Lire le CSV
    path_file = raw_dir / "i119.csv"
    if not path_file.exists():
        raise FileNotFoundError(f"Fichier {path_file} introuvable après extraction")

    df_risques = pd.read_csv(path_file, sep=";", header=2, low_memory=False)

    mapping = {
        "Code": "code_insee",
        "Libellé": "nom_commune",
        "risque d'inondations, 2019": "inondations",
        "risque de mouvements de terrain, 2019": "mouvements_terrain",
        "risque de séismes, 2019": "seismes",
        "risque d'avalanches, 2019": "avalanches",
        "risque de feux de forêt, 2019": "feux_foret",
        "risque de lié à des phénomènes atmosphériques, 2019": "phenomenes_atmo",
        "risque d'éruptions volcaniques, 2019": "eruptions",
        "risque industriel, 2019": "industriel",
        "risque nucléaire, 2019": "nucleaire",
        "risque de rupture de barrage, 2019": "barrage",
        "risque lié au transport de marchandises dangereuses, 2019": "transport_matieres",
        "risque lié aux engins de guerre": "engins_guerre",
        "risque d'affaissements miniers, 2019": "affaissements_miniers",
    }

    df_risques = df_risques.rename(columns=mapping).drop(columns=["nom_commune"])

    df_risques["code_insee"] = df_risques["code_insee"].apply(lambda x: str(x).zfill(5))

    # Modification des valeurs commençant par "N/A" en Nan
    df_risques = df_risques.replace(r"^N/A.*", pd.NA, regex=True)

    return df_risques


def main():
    with duckdb.connect() as con:
        # chargement des données des pharmacies
        df_risques = prepare_df_risque()
        df_risques = df_risques.dropna(
            subset=["code_insee"]
        )  # Supprimer les lignes avec des valeurs nulles dans code_insee

        # on traite les codes insee pour les communes de Paris, Marseille et Lyon
        df_risques["code_insee"] = remap_arrondissements(df_risques["code_insee"])

        # Chargement de la table epci
        df_epci = load_epci()

        df_risques["code_insee"] = remap_arrondissements(df_risques["code_insee"])

        # jointure avec les communes pour obtenir les codes epci
        query = """ 
        SELECT 
            df_epci.siren AS id_epci,
            df_risques.*
        FROM df_risques
        LEFT JOIN df_epci
            ON df_risques.code_insee = df_epci.code_insee
            """

        df_risques_epci = con.sql(query)

        # compter le nombre de risques majeurs par epci
        query = """ 
        SELECT
            id_epci,
            SUM(TRY_CAST(inondations AS INTEGER)) AS inondations,
            SUM(TRY_CAST(mouvements_terrain AS INTEGER)) AS mouvements_terrain,
            SUM(TRY_CAST(seismes AS INTEGER)) AS seismes,
            SUM(TRY_CAST(avalanches AS INTEGER)) AS avalanches,
            SUM(TRY_CAST(feux_foret AS INTEGER)) AS feux_foret,
            SUM(TRY_CAST(phenomenes_atmo AS INTEGER)) AS phenomenes_atmo,
            SUM(TRY_CAST(eruptions AS INTEGER)) AS eruptions,
            SUM(TRY_CAST(nucleaire AS INTEGER)) AS nucleaire,
            SUM(TRY_CAST(barrage AS INTEGER)) AS barrage,
            SUM(TRY_CAST(transport_matieres AS INTEGER)) AS transport_matieres,
            SUM(TRY_CAST(engins_guerre AS INTEGER)) AS engins_guerre,
            SUM(TRY_CAST(affaissements_miniers AS INTEGER)) AS affaissements_miniers,
            SUM(TRY_CAST(industriel AS INTEGER)) AS industriel
        FROM df_risques_epci
        GROUP BY id_epci
        """

        df_total_risques = con.sql(query)
        print(df_total_risques.df().head())

        query = """ 
        SELECT 
            df_total_risques.id_epci,
            SUM(CASE WHEN inondations > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN mouvements_terrain > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN seismes > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN avalanches > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN feux_foret > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN phenomenes_atmo > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN eruptions > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN nucleaire > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN barrage > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN transport_matieres > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN engins_guerre > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN affaissements_miniers > 0 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN industriel > 0 THEN 1 ELSE 0 END)
            AS total_risques
        FROM df_total_risques
        GROUP BY id_epci
            """
        df_total_risques = con.sql(query)
        print(df_total_risques.df().head())

        # query complete with join
        query = """
        WITH s1 AS (
        SELECT DISTINCT siren, dept_epci, epci_nom
        FROM df_epci
            )
            SELECT
                s1.dept_epci AS dept_id,
                CAST(s1.siren AS VARCHAR) AS id_epci,
                s1.epci_nom AS epci_lib,
                'i119' AS id_indicator,
                s2.total_risques
            AS valeur_brute,
                '2019' AS annee
            FROM s1
            LEFT JOIN df_total_risques AS s2
                ON CAST(s1.siren AS VARCHAR) = CAST(s2.id_epci AS VARCHAR)
            GROUP BY s1.dept_epci, s1.siren, s1.epci_nom, s2.total_risques
            ORDER BY s1.dept_epci, s1.siren
        """

        df_complete = con.sql(query)

        output_path_complete = processed_dir / "i119_total_risques.csv"
        df_complete.write_csv(str(output_path_complete))
        print(f"Données risques majeurs complètes sauvegardées dans {output_path_complete}")


if __name__ == "__main__":
    main()
