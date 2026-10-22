from io import BytesIO

import duckdb
import pandas as pd

from utils.functions import download_file, download_stock_file, float_to_codepostal
from utils.project import load_communes, load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_asso")


def asso_sans_alsace(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Charge les données des associations hors Alsace-Moselle.

    Returns
    -------
    pd.DataFrame
        DataFrame contenant les données des associations hors Alsace-Moselle nettoyées.
    """
    url_complete = "https://www.data.gouv.fr/api/1/datasets/r/cc7b8f0c-45ea-4444-8b55-55d30bc34ac5"
    filename_asso = "rna_waldec_20250901_complete.parquet"
    download_stock_file(url_complete, extract_to=raw_dir, filename=filename_asso)
    df_asso = con.read_parquet(str(raw_dir / filename_asso))

    # On garde les assos actives et on retire celles que l'on ne peut rattacher à une commune
    query = """ 
    SELECT 
        id,
        adrs_codeinsee, 
        adrs_codepostal
    FROM df_asso 
    WHERE position = 'A' 
            AND (adrs_codeinsee IS NOT NULL OR adrs_codepostal IS NOT NULL)
            AND (adrs_codeinsee != '0' OR adrs_codepostal != '00000')
            AND (adrs_codeinsee !='0' OR adrs_codepostal IS NOT NULL)
    ORDER BY adrs_codeinsee
    """

    df_asso_filtered = con.sql(query).df()

    # Récupération des valeurs code_insee et code_postal manquantes via jointure avec df_com
    query_insee_not_null = """
    SELECT
        *
    FROM df_asso_filtered
    WHERE adrs_codeinsee IS NOT NULL 
        AND adrs_codeinsee!='0'
        """

    df_insee_not_null = con.sql(query_insee_not_null).df()

    query_insee_null = """
    SELECT
        *
    FROM df_asso_filtered
    WHERE adrs_codeinsee IS NULL 
        OR adrs_codeinsee='0'
    """
    df_insee_null = con.sql(query_insee_null).df()

    df_com = load_communes()
    df_com = float_to_codepostal(df_com, "code_postal")

    for _, row in df_insee_null.iterrows():
        code_postal = row["adrs_codepostal"]
        code_insee = df_com[df_com["code_postal"] == code_postal]["code_insee"].values[0]
        print(f"Code postal: {code_postal} -> Code insee: {code_insee}")
        row["adrs_codeinsee"] = code_insee

    query = """ 
    select * from df_insee_null
    union
    select * from df_insee_not_null
    """

    df_asso_als = con.sql(query)

    # On règle les problèmes de code postal
    query_sans_pb_postal = """ 
    SELECT * 
    FROM df_asso_als 
    WHERE adrs_codepostal not like '00%' 
    ORDER BY adrs_codeinsee
    """

    df_sans_pb_postal = con.sql(query_sans_pb_postal).df()

    query_pb_postal = """ 
    SELECT *
    FROM df_asso_als
    WHERE adrs_codepostal like '00%'
    ORDER BY adrs_codeinsee
    """

    df_pb_postal = con.sql(query_pb_postal)

    ##Correction des codes postaux de Paris
    query_paris_corrige = """ 
    SELECT 
        id, 
        '75056' AS adrs_codeinsee,
        adrs_codepostal
    FROM df_pb_postal 
    WHERE adrs_codeinsee LIKE '75%'
    ORDER BY adrs_codeinsee
    """

    df_paris_corrige = con.sql(query_paris_corrige).df()

    ##On revient aux codes postaux problématiques en enlevant paris corrigé
    query_pb_postal_sans_paris = """
    SELECT * 
    FROM df_pb_postal
    WHERE adrs_codeinsee != '75112'
    """
    df_pb_postal_sans_paris = con.sql(query_pb_postal_sans_paris).df()

    # Correction des derniers codes postaux problématiques via jointure avec df_com
    for _, row in df_pb_postal_sans_paris.iterrows():
        code_insee = row["adrs_codeinsee"]
        try:
            code_postal = df_com[df_com["code_insee"] == code_insee]["code_postal"].values[0]
        except IndexError:
            print(f"Code insee: {code_insee} not found in df_com")
            continue

    # On supprime les derniers problèmes
    df_pb_postal_clean = df_pb_postal_sans_paris[
        df_pb_postal_sans_paris["adrs_codepostal"] != "00000"
    ]

    # On concatène les dataframes pour obtenir le dataframe final
    df_asso_sans_final = pd.concat([df_sans_pb_postal, df_pb_postal_clean, df_paris_corrige])

    return df_asso_sans_final


def asso_alsace_moselle(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    # Données des associations pour 57,67,68 (Alsace-Moselle)
    dico_url = {
        "57": "https://www.data.gouv.fr/api/1/datasets/r/f5073265-9689-441c-bd6d-8d9fbd360161",
        "67": "https://www.data.gouv.fr/api/1/datasets/r/b7acf7a2-1480-465e-b02b-22633d0a378d",
        "68": "https://www.data.gouv.fr/api/1/datasets/r/b7d6b412-5da6-4ed2-97cc-c9d8e7b321de",
    }

    df_asso = pd.DataFrame()
    for dept, url in dico_url.items():
        content = download_file(url)
        df_dept = pd.read_csv(BytesIO(content), sep=";", dtype=str)
        df_asso = pd.concat([df_asso, df_dept], ignore_index=True)

    # On garde les assos inscrites
    query = """ 
    SELECT 
        NUMERO_AMALIA as id,
        COMMUNE as commune,
        CODE_POSTAL as adrs_codepostal
    FROM df_asso
    WHERE ETAT_ASSOCIATION = 'INSCRITE'
    ORDER BY CODE_POSTAL
    """

    df_asso_filtered = con.sql(query).df()

    # On règle les problèmes de code postal
    # query = """
    # SELECT *
    # FROM df_asso_filtered
    # WHERE LENGTH(adrs_codepostal) != 5
    # """
    # df_asso_filtered_5 = con.sql(query).df()

    mapping_code_postal = {
        "57": "57050",
        "5700": "57000",
        "570000": "57000",
        "573000": "57300",
        "57657660": "57660",
        "67000": "67000",
        "670000": "67000",
        "680000": "68000",
        "681180 ": "68118",
        "684809": "68480",
        "686102": "68610",
    }

    df_asso_corrige = df_asso_filtered.replace({"adrs_codepostal": mapping_code_postal})
    print(f"Taille df_asso_als_moselle: {df_asso_corrige.shape}")
    return df_asso_corrige


def main():
    with duckdb.connect() as con:
        # Données des associations hors Alsace-Moselle
        df_asso_sans_als = asso_sans_alsace(con).reset_index(drop=True)

        # Données des associations pour 57,67,68 (Alsace-Moselle)
        df_asso_als = asso_alsace_moselle(con).reset_index(drop=True)

        # Création de la table duckdb des communes
        df_com = load_communes()
        df_com = float_to_codepostal(df_com, "code_postal")

        # Création de la table duckdb des epci
        df_epci = load_epci()

        # jointure avec les communes pour récupérer les codes insee
        query_join = """ 
        SELECT 
            a.id,
            c.nom_standard_majuscule as commune,
            a.adrs_codepostal,
            c.code_insee as adrs_codeinsee  
        FROM df_asso_als a
        LEFT JOIN df_com c
        ON a.commune = c.nom_standard_majuscule 
            AND LEFT(a.adrs_codepostal, 2) = LEFT(c.code_postal, 2)
        ORDER BY a.adrs_codepostal  
        """

        df_joined = con.sql(query_join)

        # Concaténation des deux dataframes des assos
        query_union = """
        SELECT 
            id,
            adrs_codeinsee,
            adrs_codepostal 
        FROM df_joined

        UNION

        SELECT * 
        FROM df_asso_sans_als
        ORDER BY adrs_codeinsee
        """

        df_asso_complete = con.sql(query_union).df()

        # On retraite le code insee pour les communes de Paris, Marseille et Lyon
        df_asso_complete.dropna(
            subset=["adrs_codeinsee"], inplace=True
        )  # Supprimer les lignes avec des valeurs nulles dans adrs_codeinsee
        df_asso_complete["adrs_codeinsee"] = remap_arrondissements(
            df_asso_complete["adrs_codeinsee"]
        )

        # Calcul de l'indicateur i131 : nombre d'associations pour 1000 habitants par EPCI
        query = """ 
        SELECT 
            p.dept_epci AS dept_id,
            CAST(p.siren AS VARCHAR) AS id_epci,
            p.epci_nom AS epci_lib,
            'i131' AS id_indicator,
            ROUND(COUNT(e2.adrs_codeinsee) / p.total_pop_mun * 1000,2) AS valeur_brute,
            '2025' AS annee
        FROM df_epci p
        LEFT JOIN df_epci e1 ON e1.siren = p.siren
        LEFT JOIN df_asso_complete e2 
            ON e2.adrs_codeinsee = e1.code_insee
        GROUP BY p.dept_epci, p.siren, p.epci_nom, p.total_pop_mun
        ORDER BY dept_id, id_epci;

        """

        df_asso_final = con.sql(query)
        print(df_asso_final.shape)

        # sauvegarde du fichier final
        output_file = processed_dir / "i131_asso_per_epci.csv"
        df_asso_final.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")

        # Calcul de l'indicateur i131 : nombre d'associations par EPCI
        query = """ 
        SELECT 
            p.dept_epci AS dept_id,
            CAST(p.siren AS VARCHAR) AS id_epci,
            p.epci_nom AS epci_lib,
            'i131' AS id_indicator,
            COUNT(e2.adrs_codeinsee) AS nb_asso,
            '2025' AS annee
        FROM df_epci p
        LEFT JOIN df_epci e1 ON e1.siren = p.siren
        LEFT JOIN df_asso_complete e2 
            ON e2.adrs_codeinsee = e1.code_insee
        GROUP BY p.dept_epci, p.siren, p.epci_nom, p.total_pop_mun
        ORDER BY dept_id, id_epci;

        """

        df_nb_asso = con.sql(query)
        print(df_nb_asso.shape)

        # sauvegarde du fichier final
        output_file = processed_dir / "nb_asso_per_epci.csv"
        df_nb_asso.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()  # asso.py
