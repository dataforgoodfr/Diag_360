import re
from pathlib import Path

import duckdb
import pandas as pd

from utils.project import load_communes, load_epci, setup_dirs

raw_dir, processed_dir = setup_dirs("data_media")


def main():
    with duckdb.connect() as con:
        # dataframe des epci
        # df_epci = create_dataframe_epci()
        df_epci = load_epci()

        # dataframe des communes
        # df_com = create_dataframe_communes()
        df_com = load_communes()

        # dataframe des médias non indépendants
        url_media_non_independants = (
            "https://raw.githubusercontent.com/mdiplo/Medias_francais/refs/heads/master/medias.tsv"
        )
        df_non_independants = pd.read_csv(url_media_non_independants, sep="\t")

        # dataframe des medias locaux
        file_path = raw_dir / "medias_locaux.txt"

        def extraire_donnees_media(chemin_fichier):
            contenu = Path(chemin_fichier).read_text(encoding="utf-8")

            # 1. On récupère d'abord tout le texte entre les balises <a>...</a>
            # Le format est : <a href="#">Texte (Ville)</a>
            balises = re.findall(r'<a href="#">(.*?)</a>', contenu)

            data = []

            for item in balises:
                # 2. On sépare le nom de la ville
                # On cherche la DERNIÈRE parenthèse de la chaîne
                # (.*) -> Nom du média
                # \s -> espace
                # \(([^)]+)\)$ -> Contenu de la dernière parenthèse à la fin de la chaîne
                match = re.search(r"(.*)\s\(([^)]+)\)$", item)

                if match:
                    nom_media = match.group(1).strip()
                    ville = match.group(2).strip()
                    data.append([nom_media, ville])
                else:
                    # Cas de secours si le format est différent
                    data.append([item, "Inconnue"])

            # 3. Création du DataFrame
            df = pd.DataFrame(data, columns=["Nom_media", "Ville"])
            return df

        # Exécution
        try:
            df_medias = extraire_donnees_media(str(file_path))
            print("Extraction réussie :")
            print(df_medias.head())

        except Exception as e:
            print(f"Erreur lors de la lecture du fichier : {e}")

        print(f"Nombre de lignes dans df_medias : {df_medias.shape[0]}")
        # On remplace les manquants par les noms de villes
        # différence des villes entre df_médias et df_result_final
        # set_villes_medias = set(df_medias["Ville"].unique())
        # set_villes_result = set(df_temp["nom_standard"].unique())
        # set_villes_diff = set_villes_medias - set_villes_result
        # set_villes_diff

        # correction de l'orthographe de certaines villes pour faire correspondre les noms de villes entre df_medias et df_com
        ville_mapping = {
            "Bourg Les Valence": "Bourg-lès-Valence",
            "Charleville-Mézieres": "Charleville-Mézières",
            "Cherbourg": "Cherbourg-en-Cotentin",
            "Cherbourg-En-Cotentin": "Cherbourg-en-Cotentin",
            "Château du Loir": "Montval-sur-Loir",
            "Cierp Gaud": "Cierp-Gaud",
            "Digne les Bains": "Digne-les-Bains",
            "Echouboulains": "Échouboulains",
            "Inconnue": "Château-Chinon (Ville)",
            "SAINT-AIGNAN DE GRAND LIEU": "Saint-Aignan-Grandlieu",
            "Saint-Quentin-en-Yvelines": "Montigny-le-Bretonneux",
            "Sanary": "Sanary-sur-Mer",
            "St Philbert de Grand-Lieu": "Saint-Philbert-de-Grand-Lieu",
            "Vaux-Sur-Mer": "Vaux-sur-Mer",
            "la Seyne": "La Seyne-sur-Mer",
        }

        df_medias["Ville"] = df_medias["Ville"].replace(ville_mapping)

        # premiere jointure avec les communes
        query = """
        SELECT 
            code_insee,
            nom_standard,
            dep_code,
            epci_code,
            epci_nom,
            df_medias.Nom_media AS nom_media  
        FROM df_com  
        INNER JOIN df_medias
        ON df_com.nom_standard = df_medias.Ville
        WHERE epci_code NOT LIKE 'Z%'
        """

        df_result = con.query(query).to_df()
        print(df_result.shape)

        # on supprime les doublons
        # Configuration des règles de filtrage
        # Format : "Ville": département_autorisé  OU  "Ville": fonction_spécifique
        RULES_CONFIG = {
            "Bailleul": "59",
            "Castres": "81",
            "Chaumont": "52",
            "Clamecy": "58",
            "Falaise": "14",
            "Flers": "61",
            "Fontaine": "38",
            "La Rochelle": "17",
            "Langon": "33",
            "Marmagne": "71",
            "Montreuil": "93",
            "Moulins": "03",
            "Olivet": "45",
            "Prades": "66",
            "Rochefort": "17",
            "Saint-Claude": "39",
            "Saint-Nazaire": "44",
            "Saint-Omer": "62",
            "Saint-Raphaël": "83",
            "Ussel": "19",
            "Verdun": "55",
            "Vernon": "27",
            # Cas complexes avec conditions multiples
            "Blanquefort": lambda r: r["dep_code"] == "33" and r["nom_media"] == "R.I.G",
            "Valence": lambda r: (
                (r["dep_code"] == "82" and r["nom_media"] in ["VFM", "La Dépêche du Midi"])
                or (r["dep_code"] == "26" and r["nom_media"] not in ["VFM", "La Dépêche du Midi"])
            ),
        }

        def filter_logic(row):
            ville = row["nom_standard"]

            # Si la ville n'est pas dans le dictionnaire, on garde la ligne par défaut
            if ville not in RULES_CONFIG:
                return True

            regle = RULES_CONFIG[ville]

            # Si la règle est une fonction (cas complexes)
            if callable(regle):
                return regle(row)

            # Sinon, c'est une règle simple de département (comparaison directe)
            return row["dep_code"] == regle

        # Application du filtre en une seule ligne
        df_temp = df_result[df_result.apply(filter_logic, axis=1)].copy()

        df_temp.drop_duplicates(inplace=True)

        df_temp.to_csv(str(processed_dir / "medias_extraits.csv"), index=False)

        # on retire de df_result_final les médias présents dans df
        df_final = df_temp[~df_temp["nom_media"].isin(df_non_independants["Nom"])]

        print(df_final.head())
        query_by_dept = """ 
        SELECT 
            dep_code as dept,
            count(nom_media) AS n_medias_par_dept
        FROM df_final
        GROUP BY dep_code
        ORDER BY dep_code
        """

        nb_medias_par_dept = con.query(query_by_dept).to_df()
        nb_medias_par_dept.to_csv(str(processed_dir / "nb_medias_par_dept.csv"), index=False)

        query_by_epci = """ 
        SELECT
            df_epci.dept_epci AS dept_id,
            df_epci.siren as id_epci,
            df_epci.epci_nom AS epci_lib,
            'i096' AS id_indicator,
            COUNT(nom_media) AS valeur_brute,
            '2024' AS annee
        FROM df_epci
        LEFT JOIN df_final
        ON df_epci.code_insee = df_final.code_insee
        GROUP BY dept_id, id_epci, epci_lib
        ORDER BY dept_id, id_epci
        """

        nb_medias_par_epci = con.query(query_by_epci).to_df()
        nb_medias_par_epci.to_csv(str(processed_dir / "i096_medias_epci.csv"), index=False)


if __name__ == "__main__":
    main()
