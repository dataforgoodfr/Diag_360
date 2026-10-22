import duckdb
import pandas as pd

from utils.project import BASE_DIR, load_epci, setup_dirs

_, processed_dir = setup_dirs("data_pop_precaire")


def main():
    # Chargement de la table des populations précaires
    data_precaire = pd.read_csv(
        BASE_DIR / "data" / "raw" / "pop_precaire.csv", sep=";", header=2
    )

    # chargement de la table des epci
    df_epci = load_epci()

    # Traitement de la table des populations précaires
    df_precaire = data_precaire.rename(
        columns={
            "Code": "code_insee",
            "Libellé": "nom_com",
            "Part de la population en emploi précaire 2022": "valeur",
        }
    )

    # Part moyenne d'emploi précaire par epci, pondérée par la population des communes
    # dont la valeur est disponible (les valeurs non numériques, ex. "N/A", sont ignorées)
    query = """
    WITH communes AS (
        SELECT
            df_epci.dept_epci,
            df_epci.siren,
            df_epci.epci_nom,
            df_epci.pop_mun_commune AS pop,
            TRY_CAST(replace(CAST(df_precaire.valeur AS VARCHAR), ',', '.') AS DOUBLE) AS valeur
        FROM df_epci
        LEFT JOIN df_precaire
            ON df_epci.code_insee = df_precaire.code_insee
    )

    SELECT
        dept_epci AS dept_id,
        siren AS id_epci,
        epci_nom AS epci_lib,
        'i164' AS id_indicator,
        ROUND(
            SUM(pop * valeur) / NULLIF(SUM(CASE WHEN valeur IS NOT NULL THEN pop END), 0),
            2
        ) AS valeur_brute,
        '2022' AS annee
    FROM communes
    GROUP BY dept_epci, siren, epci_nom
    ORDER BY dept_epci, siren
    """

    df_final = duckdb.sql(query)
    print(df_final.df().shape)

    # sauvegarde du fichier final
    output_file = processed_dir / "i164_pop_precaire.csv"
    df_final.write_csv(str(output_file))
    print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()
