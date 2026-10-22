import re

import pandas as pd


class format_file:
    def __init__(
        self,
        path,
        separateur_fichier=";",
        keyword_header=["Code commune INSEE", "Commune"],
        extension="csv",
        onglet_to_filter=True,
    ):
        self.filepath = path
        self.separateur_fichier = separateur_fichier
        self.extension = extension
        self.onglet_to_filter = onglet_to_filter
        self.keyword_header = keyword_header

    def onglet_excel_to_select(self):
        xls = pd.ExcelFile(self.filepath).sheet_names
        sheet_map = {}
        for name in xls:
            # On cherche 4 chiffres consécutifs (ex: 2024) dans le nom
            match = re.search(r"(\d{4})", name)
            if match:
                year = int(match.group(1))
                sheet_map[year] = name

        # On retourne l'onglet qui a l'année la plus élevée
        if sheet_map:
            latest_year = max(sheet_map.keys())
            return sheet_map[latest_year]

        # Si aucune date n'est trouvée, on prend le premier par défaut
        return xls[0]

    def _detect_header(self):
        # On teste les 15 premières lignes
        if self.extension in ["xlsx", "xls"]:
            if self.onglet_to_filter:
                onglet_excel_to_select = self.onglet_excel_to_select()
                df_test = pd.read_excel(
                    self.filepath,
                    sheet_name=onglet_excel_to_select,
                    nrows=15,
                    header=None,
                )

        else:
            df_test = pd.read_csv(
                self.filepath, sep=self.separateur_fichier, nrows=15, header=None
            )
        for i, row in df_test.iterrows():
            if any(
                key in str(val) for val in row.values for key in self.keyword_header
            ):
                return i
        return 0

    def read_file(self):
        if self.extension == "csv":
            header_row = self._detect_header()
            df = pd.read_csv(
                self.filepath, skiprows=header_row, sep=self.separateur_fichier
            )
        elif self.extension in ["xlsx", "xls"]:
            header_row = self._detect_header()
            self.onglet_excel_to_select = self.onglet_excel_to_select()
            df = pd.read_excel(
                self.filepath,
                sheet_name=self.onglet_excel_to_select,
                skiprows=header_row,
            )
        else:
            raise ValueError("Unsupported file extension, need to be added.")
        return df
