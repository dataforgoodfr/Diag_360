import duckdb

from utils.project import load_epci, setup_dirs

raw_dir, processed_dir = setup_dirs("data_covoit")


def main():
    with duckdb.connect() as con:
        # définition des urls
        # url_nb_lieu_covoit = "https://www.data.gouv.fr/api/1/datasets/r/4fd78dee-e122-4c0d-8bf6-ff55d79f3af1"
        # téléchargement des données
        # download_file(url_nb_lieu_covoit, raw_dir, filename="nb_lieux_covoiturage.csv")
        # mais manque à priori des données

        filename = "nb-lieux-covoiturage_2025_export.csv"

        # Lecture des données relative au covoiturage
        df_nb_lieu_covoit = con.read_csv(str(raw_dir / filename))

        # Téléchargement des données epci pour jointure
        df_epci = load_epci()

        # Calcul par epci du nombre de lieux de covoiturage pour 10000 habitants
        query = """
        WITH df_nb_lieu_covoit_filtered AS (
            SELECT 
                territoryid AS siren,
                sum(valeur) AS nb_aires_covoiturage
            FROM df_nb_lieu_covoit
            WHERE type_lieu = 'Aire de covoiturage'
            GROUP BY territoryid
            )
    
        SELECT 
            e1.dept_epci AS dept_id,
            e1.siren AS id_epci,
            e1.epci_nom AS epci_lib,
            'i149' AS id_indicator,
            ROUND(e2.nb_aires_covoiturage / e1.total_pop_mun * 10000,3) AS valeur_brute,
            '2025' AS annee
        FROM df_epci e1
        LEFT JOIN df_nb_lieu_covoit_filtered e2
        ON e1.siren = e2.siren
        GROUP BY e1.dept_epci, e1.siren, e1.epci_nom, e2.nb_aires_covoiturage,  e1.total_pop_mun
        ORDER BY e1.dept_epci, e1.siren
        """

        df_nb_lieu_covoit_bdd = con.sql(query)

        # Sauvegarde du fichier final
        output_file = processed_dir / "i149_aires_covoit_per_epci.csv"
        df_nb_lieu_covoit_bdd.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()
