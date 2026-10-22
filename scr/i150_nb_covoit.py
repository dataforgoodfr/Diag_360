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

        filename = "nb-trajets-covoiturage_2024_export.csv"

        # Lecture des données relative au covoiturage
        df_nb_covoit = con.read_csv(str(raw_dir / filename), sep=",")

        # Téléchargement des données epci pour jointure
        df_epci = load_epci()

        # Calcul par epci du nombre de trajets de covoiturage pour 10 000 habitants
        query = """ 
        SELECT
            e1.dept_epci AS dept_id,
            e1.siren as id_epci,
            e1.epci_nom AS epci_lib,
            'i150' AS id_indicator,
            ROUND((1.0*e2.valeur)/e1.total_pop_tot*10000 ,3) AS valeur_brute,
            '2024' AS annee
        FROM df_epci e1
        LEFT JOIN df_nb_covoit e2
        ON e2.territoryid = e1.siren
        GROUP BY e1.dept_epci, e1.siren, e1.epci_nom, e2.valeur, e1.total_pop_tot
        ORDER BY e1.dept_epci, e1.siren
        """

        df_nb_trajet_complete = con.sql(query)
        output_file_complete = processed_dir / "i150_nb_covoit.csv"
        df_nb_trajet_complete.write_csv(str(output_file_complete))
        print(f"Fichier sauvegardé : {output_file_complete}")


if __name__ == "__main__":
    main()
