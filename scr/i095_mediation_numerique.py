from io import BytesIO

import duckdb
import pandas as pd

from utils.functions import download_file
from utils.project import load_communes, load_epci, setup_dirs

raw_dir, processed_dir = setup_dirs("data_medi_num")


def main():
    with duckdb.connect() as con:
        url = "https://www.data.gouv.fr/api/1/datasets/r/398edc71-0d51-4cb6-9cbe-2540a4db573c"

        # Télécharger et extraire les données médiation
        content = download_file(url)
        df_mediation_num = pd.read_csv(BytesIO(content), low_memory=False)

        # Création de df_epci
        df_epci = load_epci()

        # Création de df_com
        df_com = load_communes(low_memory=False)

        df_mediation_num["code_postal"] = df_mediation_num["code_postal"].astype(str).str.zfill(5)
        df_med_num = (
            df_mediation_num[["commune", "code_postal", "code_insee", "adresse"]]
            .sort_values(by="code_insee")
            .drop_duplicates()
        )

        # Identifier les lignes avec code_insee manquant et extraire le code département
        df_isna = df_med_num[df_med_num["code_insee"].isna()]
        df_isna["dep_code"] = df_isna["code_postal"].astype(str).str.zfill(5).str[:2]

        def find_code_insee(row):
            com = str(row["commune"]).upper()
            dep = row["dep_code"]
            matches = df_com[
                (df_com["dep_code"] == dep)
                & (
                    df_com["nom_standard_majuscule"].str.contains(
                        com, case=False, na=False, regex=False
                    )
                )
            ]
            return matches["code_insee"].iloc[0] if not matches.empty else None

        df_isna["code_insee"] = df_isna.apply(find_code_insee, axis=1)

        # Afficher les lignes avec code_insee toujours manquant après tentative de correspondance
        df_isna_null = df_isna[df_isna["code_insee"].isna()]

        # On crée un mapping des communes avec code_insee manquant pour les corriger dans df_med_num
        mapping_com = {
            "AIX-LA-DURANNE": "13001",
            "BLETTRANS": "39056",
            "Bordères-et-Lamensens": "40049",
            "CAPAVENIR-VOSGES": "88465",
            "CEZAIS": "85292",
            "CHERVES-RICHEMONT": "16097",
            "COSNE-SUR-LOIRE": "58086",
            "ETRAT": "42092",
            "Eryaud-Crempse-Maurens": "24259",
            "Etroeugnt": "59218",
            "HELLEMMES---LILLE": "59350",
            "HELLEMMES-LILLE": "59350",
            "LA-TARDIERE": "85289",
            "LE-BÉNY-BOCAGE": "14061",
            "La-Chapelle-aux-Pots": "61275",
            "Le-Merlerault": "60333",
            "MARDYCK": "59183",
            "MONTIGNY-PRES-LOUHANS": "71303",
            "MORET-SUR-LOING": "77316",
            "MOREZ": "39368",
            "NANTEUIL-LE-HAUDOIN": "60446",
            "NUIT-SAINT-GEORGES": "21464",
            "Neussargues-en-Pinatelle": "15141",
            "PONT-A-BUCY": "02559",
            "PONT-DU-LOUP": "06148",
            "Richerbourg": "62706",
            "SAINT-MACOUX": "86247",
            "SAINT-SAVIOL": "86247",
            "SAINT-SULPICE-DE-COGNAC": "16097",
            "SECHELLES": "02004",
            "SENNECEY-SUR-SAÔNE-SAINT-ALBIN": "70482",
            "Saint-Macoux": "86247",
            "Saint-Paul-lez-Durance": "13099",
            "Saint-Saviol": "86247",
            "THOUARSAIS-BOUILDROUX": "85292",
            "TOURETTES-SUR-LOUP": "06148",
            "VALENCIENES": "59606",
            "hondshoote": "59309",
        }
        # On applique le mapping
        df_isna_null["code_insee"] = df_isna_null["commune"].map(mapping_com)

        # On regroupe les datarame
        df_isna_not_null = df_isna[df_isna["code_insee"].notna()]
        df_med_num_not_null = df_med_num[df_med_num["code_insee"].notna()]
        df_med_num_final = pd.concat(
            [df_isna_not_null, df_isna_null, df_med_num_not_null], ignore_index=True
        ).sort_values(by="code_insee")

        # Jointure des données
        query = """ 
        WITH df_mediation_num_grouped AS (
        SELECT 
            count(*) AS nb_mediation,
            code_insee
        FROM df_med_num_final
        GROUP BY code_insee)

        SELECT 
            dept_epci as dept_id,
            siren as id_epci,
            epci_nom as epci_lib,
            'i095' as id_indicator,
            round(10000 * sum(dmn.nb_mediation) / df_epci.total_pop_mun, 2) AS valeur_brute,
            '2025' as annee
        FROM df_epci
        LEFT JOIN df_mediation_num_grouped as dmn
        ON dmn.code_insee = df_epci.code_insee
        GROUP BY dept_epci, siren, epci_nom, total_pop_mun
        ORDER BY dept_epci, siren
        """
        df_epci_mediation = con.sql(query)
        print(df_epci_mediation.df().head())

        # Sauvegarde du fichier final
        output_file = processed_dir / "i095_mediation_numerique_per_10k_habs.csv"
        df_epci_mediation.write_csv(str(output_file))
        print(f"Fichier sauvegardé : {output_file}")


if __name__ == "__main__":
    main()  # mediation_numerique.py
