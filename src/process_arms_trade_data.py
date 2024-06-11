import pandas as pd
import numpy as np
import os
import pycountry
import re

class ArmsTradeData:
    def __init__(self, csv_path: str = "data/trade_register.csv"):
        """
        Initialize the ArmsTradeData object with the path to the CSV file.

        :param csv_path: Path to the CSV file containing the arms trade data.
        """
        self.csv_path = csv_path

    def get_arms_trade_data(self) -> pd.DataFrame:
        """
        Load, process, and return the arms trade data as a pandas DataFrame.

        :return: Processed DataFrame containing the arms trade data.
        """
        self.load_csv()
        self.rename_columns()
        self.assign_region_types()
        self.assign_iso_a3_codes()
        self.remove_trailing_asterisk()

        return self.df

    def load_csv(self):
        """
        Load the CSV file into a pandas DataFrame.
        """
        base_path = os.path.abspath('..')
        base_path += '/'
        self.df = pd.read_csv(base_path + self.csv_path)

    def rename_columns(self):
        """
        Rename columns in the DataFrame to standardize column names.
        """
        column_name_mapping = {
            'SIPRI AT Database ID': 'ID', 
            'Order date': 'Order year'
        }
        self.df.rename(columns=column_name_mapping, inplace=True)

    def assign_region_types(self):
        """
        Assign region types to the suppliers and recipients in the DataFrame.
        """
        self.regions = sorted(list(set(list(self.df.Supplier.unique()) + list(self.df.Recipient.unique()))))
        self.countries = [region for region in self.regions if ('unknown' not in region) and not region.endswith('*')]
        self.rebel_groups = [region for region in self.regions if ('unknown' not in region) and region.endswith('*') and not region.endswith('**')]
        self.orgs = [region for region in self.regions if ('unknown' not in region) and region.endswith('**')]
        self.former_countries = [
            'Biafra',
            'Czechoslovakia',
            'East Germany (GDR)',
            'North Yemen',
            'Northern Cyprus',
            'South Vietnam',
            'South Yemen',
            'Soviet Union',
            'Yugoslavia'
        ]
        self.countries = [country for country in self.countries if country not in self.former_countries]

        self.df['Supplier_region_type'] = self.df['Supplier'].apply(lambda x: self.get_region_type(x))
        self.df['Recipient_region_type'] = self.df['Recipient'].apply(lambda x: self.get_region_type(x))

    def get_region_type(self, region: str) -> str:
        """
        Determine the region type for a given region.

        :param region: The name of the region.
        :return: The type of the region (e.g., 'Country', 'Former Country', 'Organisation', 'Rebel Group', 'Unknown').
        """
        if region in self.countries:
            return 'Country'
        elif region in self.former_countries:
            return 'Former Country'
        elif region in self.orgs:
            return 'Organisation'
        elif region in self.rebel_groups:
            return 'Rebel Group'
        else:
            return 'Unknown'

    def assign_iso_a3_codes(self):
        """
        Assign ISO A3 codes to suppliers and recipients in the DataFrame.
        """
        self.get_country_iso_a3_codes()
        self.get_former_country_iso_a3_codes()
        self.get_organisation_iso_a3_codes()
        self.get_rebel_group_iso_a3_codes()
        self.df = self.df.apply(lambda row: self.assign_iso_a3_code_to_row(row), axis=1)

    def get_country_iso_a3_codes(self):
        """
        Retrieve and store ISO A3 codes for countries.
        """
        self.country_mapping = {}
        for country in self.countries:
            try:
                self.country_mapping[country] = pycountry.countries.search_fuzzy(country)[0].alpha_3
            except:
                pass

        self.country_mapping['Bosnia-Herzegovina'] = "BIH"
        self.country_mapping['DR Congo'] = "COD"
        self.country_mapping['Libya GNC'] = "LBY"
        self.country_mapping['Yemen Arab Republic (North Yemen)'] = "YEM"
        self.country_mapping['UAE'] = "ARE"

    def get_former_country_iso_a3_codes(self):
        """
        Retrieve and store ISO A3 codes for former countries.
        """
        self.former_country_mapping = {
            'Biafra': 'NGA',
            'Czechoslovakia': 'CZE',
            'East Germany (GDR)': 'DEU',
            'North Yemen': 'YEM',
            'Northern Cyprus': 'CYP',
            'South Vietnam': 'VNM',
            'South Yemen': 'YEM',
            'Soviet Union': 'RUS',
            'Yugoslavia': 'SRB'
        }

    def get_organisation_iso_a3_codes(self):
        """
        Retrieve and store ISO A3 codes for organisations.
        """
        self.org_mapping = {
            'African Union**': 'ETH',
            'European Union**': 'BEL',
            'NATO**': 'BEL',
            'OSCE**': 'AUT',
            'Regional Security System**': 'BRB',
            'United Nations**': 'USA'
        }

    def get_rebel_group_iso_a3_codes(self):
        """
        Retrieve and store ISO A3 codes for rebel groups.
        """
        self.rebel_group_mapping = {}
        for group in self.rebel_groups:
            try:
                country = re.search(r'\((.*?)\)', group).group(1)
                self.rebel_group_mapping[group] = pycountry.countries.search_fuzzy(country)[0].alpha_3
            except:
                try:
                    country = group.split(' ', 1)[0]
                    self.rebel_group_mapping[group] = pycountry.countries.search_fuzzy(country)[0].alpha_3
                except:
                    pass

        self.rebel_group_mapping['PIJ (Israel/Palestine)*'] = 'PSE'
        self.rebel_group_mapping['PRC (Israel/Palestine)*'] = 'PSE'

    def assign_iso_a3_code_to_row(self, row: pd.Series) -> pd.Series:
        """
        Assign ISO A3 codes to a row based on the supplier and recipient region types.

        :param row: A row from the DataFrame.
        :return: The updated row with ISO A3 codes for supplier and recipient.
        """
        if row['Supplier_region_type'] == 'Country':
            row['Supplier_iso_a3'] = self.country_mapping.get(row['Supplier'])
        elif row['Supplier_region_type'] == 'Former Country':
            row['Supplier_iso_a3'] = self.former_country_mapping.get(row['Supplier'])
        elif row['Supplier_region_type'] == 'Organisation':
            row['Supplier_iso_a3'] = self.org_mapping.get(row['Supplier'])
        elif row['Supplier_region_type'] == 'Rebel Group':
            row['Supplier_iso_a3'] = self.rebel_group_mapping.get(row['Supplier'])

        if row['Recipient_region_type'] == 'Country':
            row['Recipient_iso_a3'] = self.country_mapping.get(row['Recipient'])
        elif row['Recipient_region_type'] == 'Former Country':
            row['Recipient_iso_a3'] = self.former_country_mapping.get(row['Recipient'])
        elif row['Recipient_region_type'] == 'Organisation':
            row['Recipient_iso_a3'] = self.org_mapping.get(row['Recipient'])
        elif row['Recipient_region_type'] == 'Rebel Group':
            row['Recipient_iso_a3'] = self.rebel_group_mapping.get(row['Recipient'])

        return row

    def remove_trailing_asterisk(self):
        """
        Remove trailing asterisks from the supplier and recipient names in the DataFrame.
        """
        self.df['Supplier'] = self.df['Supplier'].apply(lambda x: x.rstrip('*'))
        self.df['Recipient'] = self.df['Recipient'].apply(lambda x: x.rstrip('*'))
