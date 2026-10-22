
import duckdb
import geopandas as gpd
import pandas as pd
from shapely import wkb

from utils.project import load_epci, remap_arrondissements, setup_dirs

raw_dir, processed_dir = setup_dirs("data_zone_urb")


def main():
    # Chargement local des données mais sinon utiliser :
    # https://docs.google.com/spreadsheets/d/1y6yy7_XCmhSUIqBmzZ200mgMo93YuZS8/edit?usp=sharing&ouid=108793438427721456504&rtpof=true&sd=true
    path_zones_urb = raw_dir / "zones_urbaines.csv"
    df_zones_urb = pd.read_csv(path_zones_urb)

    # Chargement des données des EPCI
    df_epci = load_epci()

    # Chargement des données des aménagements cyclables
    url = (
        "https://www.data.gouv.fr/api/1/datasets/r/f5d6ae97-b62e-46a7-ad5e-736c8084cee8"
    )
    df_amenagement_cyclable = duckdb.read_parquet(url)

    # Traitement des données des zones urbaines
    df_zones_urb.drop("Unnamed: 6", axis=1, inplace=True)
    df_zones_urb.drop(
        "* Les donnes proviennent de Corine Land Cover millésime 2018",
        axis=1,
        inplace=True,
    )
    mapping = {
        "SIREN": "siren",
        "Nom de l'EPCI": "nom_epci",
        "Nature de l'EPCI": "nature_epci",
        "Superficie de l'EPCI (km²)": "superficie_epci",
        "Superficie des territoires artificialisés* (km²)": "superficie_artificialisee",
        "Part de la superficie artificialisée": "part_percent_superficie_artificialisee",
    }

    df_zones_urb.rename(columns=mapping, inplace=True)
    df_zones_urb["superficie_epci"] = (
        df_zones_urb["superficie_epci"].replace(",", ".", regex=True).astype(float)
    )
    df_zones_urb["superficie_artificialisee"] = (
        df_zones_urb["superficie_artificialisee"]
        .replace(",", ".", regex=True)
        .astype(float)
    )
    df_zones_urb["part_percent_superficie_artificialisee"] = (
        df_zones_urb["part_percent_superficie_artificialisee"]
        .replace(",", ".", regex=True)
        .replace(" %", "", regex=True)
        .astype(float)
    )
    print(f"df_zones_urb.shape: {df_zones_urb.shape}")

    # traitement des données des aménagements cyclables
    # 1. Charger l'extension sur l'instance par défaut de DuckDB
    duckdb.sql("INSTALL spatial;")
    duckdb.sql("LOAD spatial;")

    query = """
        SELECT * EXCLUDE (geometry), 
               ST_AsWKB(geometry) AS geometry 
        FROM df_amenagement_cyclable
        WHERE ST_GeometryType(geometry) IN ('LINESTRING', 'MULTILINESTRING')
    """

    df_amenagement_cyclable = duckdb.sql(query)
    print(f"df_amenagement_cyclable.shape: {df_amenagement_cyclable.df().shape}")

    df_pandas = df_amenagement_cyclable.df()
    df_pandas["geometry"] = df_pandas["geometry"].apply(
        lambda x: wkb.loads(bytes(x)) if x else None
    )

    # 2. On crée le GeoDataFrame directement à partir du DF existant
    gdf = gpd.GeoDataFrame(df_pandas, geometry="geometry", crs="EPSG:4326")

    # 3. Calcul des kilomètres
    # On projette vers le système métrique (EPSG:2154 pour la France)
    # .length donne des mètres, on divise par 1000 pour les km
    gdf["distance_km"] = gdf.to_crs(epsg=2154).geometry.length / 1000

    df_temp_pandas = pd.DataFrame(gdf.drop(columns="geometry"))
    df_temp_pandas = df_temp_pandas.dropna(subset=["code_com_d"])

    # n retraite les codes insee de Paris, Marseille et Lyon
    df_temp_pandas["code_com_d"] = remap_arrondissements(df_temp_pandas["code_com_d"])

    # Jointure des données des zones urbanisées avec les EPCI
    query = """
    SELECT
        DISTINCT epci.siren,
        zu.superficie_artificialisee,
    FROM df_epci epci
    LEFT JOIN df_zones_urb zu
    ON zu.siren = epci.siren
    """

    df_zone_urbanise_merged = duckdb.sql(query)
    print(f"df_zone_urbanise_merged.shape: {df_zone_urbanise_merged.df().shape}")

    # Amenagement cyclable par epci
    query = """
    WITH df_temp AS(
    SELECT 
        code_com_d AS code_insee,
        sum(distance_km) AS km_amenagements
    FROM df_temp_pandas
    GROUP BY code_com_d)
    
    SELECT 
        df_epci.dept_epci AS dept_id,
        df_epci.siren as id_epci,
        df_epci.epci_nom AS epci_lib,
        sum(df_temp.km_amenagements) AS km_amenagements
    FROM df_epci
    LEFT JOIN df_temp
    ON df_epci.code_insee = df_temp.code_insee 
    GROUP BY df_epci.siren, df_epci.dept_epci, df_epci.epci_nom
    """

    df_amenagements_par_epci = duckdb.sql(query)

    # On merge les aménagements cyclables avec les zones urbanisées
    query_bdd = """ 
    SELECT 
        ape.dept_id,
        ape.id_epci,
        ape.epci_lib,
        'i058' AS id_indicator,
        ROUND(ape.km_amenagements / zu.superficie_artificialisee,2) AS valeur_brute,
        '2025' AS annee
    FROM df_amenagements_par_epci ape
    LEFT JOIN df_zone_urbanise_merged zu
    ON ape.id_epci = zu.siren
    ORDER BY ape.dept_id, ape.id_epci
    """

    # sauvegarde du dataframe final
    df_final = duckdb.sql(query_bdd)
    path_output = processed_dir / "i058_zone_urbanise.csv"
    df_final.write_csv(str(path_output))
    print(f"Dataframe final sauvegardé à: {path_output}")


if __name__ == "__main__":
    main()
