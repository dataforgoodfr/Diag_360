/* ============================================================
   DROP TABLES (reproductibilité complète)
   ============================================================ */

    DROP TABLE IF EXISTS region CASCADE;
    DROP TABLE IF EXISTS departement CASCADE;
    DROP TABLE IF EXISTS commune CASCADE;
    DROP TABLE IF EXISTS epci CASCADE;
    DROP TABLE IF EXISTS population CASCADE;
    DROP TABLE IF EXISTS besoin CASCADE;
    DROP TABLE IF EXISTS besoin_indicateur CASCADE;
    DROP TABLE IF EXISTS objectif CASCADE;
    DROP TABLE IF EXISTS objectif_indicateur CASCADE;
    DROP TABLE IF EXISTS indicateur CASCADE;
    DROP TABLE IF EXISTS indicateur_source CASCADE;
    DROP TABLE IF EXISTS source CASCADE;
    DROP TABLE IF EXISTS mesure CASCADE;
    DROP TABLE IF EXISTS diagnostic mesure CASCADE;
    DROP TABLE IF EXISTS score CASCADE;
    DROP TABLE IF EXISTS utilisateur CASCADE;
    DROP TABLE IF EXISTS diagnostic CASCADE;

/* ============================================================
   TABLES DE RÉFÉRENCE – MAILLE TERRITORIALE ET POPULATION
   ============================================================ */

    CREATE TABLE region (
        code_reg VARCHAR(10) PRIMARY KEY,
        nom VARCHAR(255) NOT NULL
    );

    CREATE TABLE departement (
        code_dept VARCHAR(10) PRIMARY KEY,
        nom VARCHAR(255) NOT NULL,
        code_reg VARCHAR(10) NOT NULL,
        FOREIGN KEY (code_reg) REFERENCES region(code_reg)
    );

    CREATE TABLE commune (
        code_com SERIAL PRIMARY KEY,
        nom VARCHAR(255) NOT NULL,
        superficie_hectares FLOAT NOT NULL,
        superficie_km2 FLOAT NOT NULL,
        code_dept VARCHAR(10) NOT NULL,
        code_reg VARCHAR(10) NOT NULL,
        code_bassin VARCHAR(10) NOT NULL,
        code_zone_emloi VARCHAR(10) NOT NULL,
        code_epci VARCHAR(10) NOT NULL,
        FOREIGN KEY (code_dept) REFERENCES departement(code_dept),
        FOREIGN KEY (code_reg) REFERENCES region(code_reg),
        FOREIGN KEY (code_epci) REFERENCES epci(siren)
    );

    CREATE TABLE epci (
        siren VARCHAR(10) PRIMARY KEY,
        nom VARCHAR(255) NOT NULL,
        type VARCHAR(50) NOT NULL,
        superficie_hectares FLOAT NOT NULL,
        superficie_km2 FLOAT NOT NULL,
        code_dept VARCHAR(10) NOT NULL,
        code_reg VARCHAR(10) NOT NULL,
        FOREIGN KEY (code_dept) REFERENCES departement(code_dept),
        FOREIGN KEY (code_reg) REFERENCES region(code_reg)
    );

    CREATE TABLE population (
        territoire_id varchar(10) PRIMARY KEY,
        annee INT NOT NULL,
        valeur_brute INT NOT NULL,
    )

    /* ============================================================
   TABLES DE RÉFÉRENCE – LIEN BESOIN-OBJECTIF-INDICATEUR-SOURCE
   ============================================================ */

   CREATE TABLE besoin (
    besoin_id SERIAL PRIMARY KEY,
    libelle VARCHAR(255) NOT NULL,
    description_courte TEXT,
    description_longue TEXT,
    type_besoin VARCHAR(100) NOT NULL
   );

   CREATE TABLE besoin_indicateur (
    besoin_id INT NOT NULL,
    indicateur_id INT NOT NULL,
    PRIMARY KEY (besoin_id, indicateur_id),
    FOREIGN KEY (besoin_id) REFERENCES besoin(besoin_id),
    FOREIGN KEY (indicateur_id) REFERENCES indicateur(indicateur_id)
   );

   CREATE TABLE objectif (
    objectif_id SERIAL PRIMARY KEY,
    libelle VARCHAR(255) NOT NULL,
    description_courte TEXT,
    description_longue TEXT,
    type_objectif VARCHAR(100) NOT NULL
   )

   CREATE TABLE objectif_indicateur (
    objectif_id INT NOT NULL,
    indicateur_id INT NOT NULL,
    PRIMARY KEY (objectif_id, indicateur_id),
    FOREIGN KEY (objectif_id) REFERENCES objectif(objectif_id),
    FOREIGN KEY (indicateur_id) REFERENCES indicateur(indicateur_id)
    );

    CREATE TABLE indicateur (
        indicateur_id SERIAL PRIMARY KEY,
        libelle VARCHAR(255) NOT NULL,
        description TEXT,
        unite VARCHAR(100),
        type_donnees VARCHAR(100) NOT NULL,
        type_indicateur VARCHAR(100) NOT NULL,  
        bornage FLOAT,
        methode_collecte TEXT,
        coefficient_defaut FLOAT NOT NULL,
        justification TEXT
    );

    CREATE TABLE indicateur_source (
        indicateur_id INT NOT NULL,
        source_id INT NOT NULL,
        annee INT NOT NULL,
        url_annee VARCHAR(255) NOT NULL,
        PRIMARY KEY (indicateur_id, source_id, annee),
        FOREIGN KEY (indicateur_id) REFERENCES indicateur(indicateur_id),
        FOREIGN KEY (source_id) REFERENCES source(source_id)
    );

    CREATE TABLE source (
        source_id SERIAL PRIMARY KEY,
        source_nom VARCHAR(255) NOT NULL,
        type_source VARCHAR(100) NOT NULL,
        url VARCHAR(255)
    );


    /* ============================================================
   TABLES DE RÉFÉRENCE – MESURE, DIAGNOSTIC et SCORE
   ============================================================ */

    CREATE TABLE mesure (
        mesure_id VARCHAR(20) PRIMARY KEY,
        territoire_id VARCHAR(10) NOT NULL,
        indicateur_id INT NOT NULL,
        annee INT NOT NULL,
        valeur_brute INT,
        valeur_normalisee FLOAT,
        FOREIGN KEY (indicateur_id) REFERENCES indicateur(indicateur_id),
    );


    CREATE TABLE diagnostic_mesure (
        diagnostic_id varchar(20) NOT NULL,
        indicateur_id VARCHAR(10) NOT NULL,
        valeur_brute FLOAT,
        valeur_normalisee FLOAT,
        coefficient FLOAT,
        exclu BOOLEAN,
        commentaire TEXT,
        PRIMARY KEY (diagnostic_id, indicateur_id),
        FOREIGN KEY (diagnostic_id) REFERENCES diagnostic(diagnostic_id),
        FOREIGN KEY (indicateur_id) REFERENCES indicateur(indicateur_id)
    );

    CREATE TABLE score (
        score_id VARCHAR(20) PRIMARY KEY,
        diagnostic_id VARCHAR(20) NOT NULL,
        dimension VARCHAR(100) NOT NULL,
        dimension_id VARCHAR(10) NOT NULL,
        valeur FLOAT,
        taux_completion FLOAT,
        calcule_le DATE,
        FOREIGN KEY (diagnostic_id) REFERENCES diagnostic(diagnostic_id)
    );

/* ============================================================
   TABLES DE RÉFÉRENCE – DIAGNOSTIC et UTILISATEUR
   ============================================================ */

    CREATE TABLE diagnostic (
        diagnostic_id VARCHAR(20) PRIMARY KEY,
        territoire_id VARCHAR(10) NOT NULL,
        annee INT NOT NULL,
        type VARCHAR(100) NOT NULL,
        statut VARCHAR(100) NOT NULL,
        cree_le DATE default CURRENT_DATE,
        finalise_le DATE,
        utilisateur_id VARCHAR(20) NOT NULL,
        FOREIGN KEY (territoire_id) REFERENCES epci(siren),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateur(utilisateur_id)
    );

    CREATE TABLE utilisateur (
        utilisateur_id varchar(20) PRIMARY KEY,
        type varchar(100) NOT NULL,
        nom varchar(255),
        email varchar(255) UNIQUE ,
        cree_le date default CURRENT_DATE
    );