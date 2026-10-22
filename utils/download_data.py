from pathlib import Path

import requests


class download_data:
    """
    Class permettant de télécharger des fichiers depuis une URL
    et de les sauvegarder dans un répertoire local raw/data.

    url : dict ou str
        Si dict : dictionnaire avec comme clé le nom du fichier à sauvegarder
                    et comme valeur l'URL de téléchargement.
    name_file_saved : str (à ne pas remplir si url est un dict)
    save_path : str (à ne pas remplir, par défaut)
    """

    def __init__(self, url, name_file_saved, save_path=Path("./data/raw")):
        self.url = url
        self.save_path = Path(save_path)
        self.name_file_save = name_file_saved

    def create_directory_to_save_file(self):
        """
        Création d'un répertoire raw/data s'il n'existe pas
        input : save_path = ./data/raw
        output : none
        """
        self.save_path.mkdir(parents=True, exist_ok=True)
        print(f"Dossier créé : {self.save_path}")

    def download_file(self):
        """
        Création d'un répertoire raw/data s'il n'existe pas
        input : save_path = ./data/raw
        output : none
        """
        # On télécharge le fichier en s'assurant que l'appel est OK
        response = requests.get(self.url)
        if response.status_code == 200:
            with open(self.save_path / self.name_file_save, "wb") as file:
                file.write(response.content)
        else:
            print(f"Erreur lors du téléchargement du fichier : {response.status_code}")
        print(f"Data downloaded from {self.url} and saved to {self.save_path}")

    def dict_download_file(self):
        """
        Permet à self.url d'être une liste d'url
        input : self.url = {name_file_saved1 :url1, name_file_saved2 : url2, ...} OU self.url = url
        output : none
        """
        # On créer le répertoire data/raw s'il n'existe pas
        self.create_directory_to_save_file()
        if type(self.url) == dict:
            for name, url in self.url.items():
                self.url = url
                self.name_file_save = name
                self.download_file()
        else:
            self.download_file()
