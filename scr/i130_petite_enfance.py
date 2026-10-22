
import duckdb
import pandas as pd
import requests

from utils.project import load_epci, setup_dirs

raw_dir, processed_dir = setup_dirs("data_pe")


def main():
    # Define URLs and file paths
    offset = [100 * i for i in range(13)]
    for offset in offset:
        url = f"https://data.caf.fr/api/explore/v2.1/catalog/datasets/txcouv_pe_epci/records?limit=100&offset={offset}&refine=annee%3A%222023%22"
        response = requests.get(url)
        r = response.json()
        df_pe = pd.json_normalize(r["results"])
        if offset == 0:
            df_pe_total = df_pe.copy()
        else:
            df_pe_total = pd.concat([df_pe_total, df_pe], ignore_index=True)

    df_pe_final = df_pe_total[["numepci", "txcouv_epci"]].copy()
    df_pe_final = df_pe_final.rename(
        columns={"numepci": "id_epci", "txcouv_epci": "valeur_brute"}
    )

    df_epci = load_epci()

    # query complete with join
    query = """
        SELECT 
            s1.dept_epci AS dept_id,
            CAST(s1.siren AS VARCHAR) AS id_epci,
            s1.epci_nom AS epci_lib,
            'i130' AS id_indicator,
            s2.valeur_brute,
            '2023' AS annee
        FROM df_epci AS s1
        LEFT JOIN df_pe_final AS s2
            ON CAST(s1.siren AS VARCHAR) = CAST(s2.id_epci AS VARCHAR)
        GROUP BY s1.dept_epci, s1.siren, s1.epci_nom, s2.valeur_brute
        ORDER BY s1.dept_epci, s1.siren
        """

    df_complete = duckdb.sql(query)

    output_path_complete = processed_dir / "i130_txcouv_pe.csv"
    df_complete.write_csv(str(output_path_complete))
    print(f"Données petite enfance complètes sauvegardées dans {output_path_complete}")


if __name__ == "__main__":
    main()
