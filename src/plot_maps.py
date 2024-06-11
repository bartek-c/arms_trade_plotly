import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
from typing import Union, Optional

from src.process_world_map_data import get_world_map_data
world_map_data = get_world_map_data()

def signed_log(x: Union[int, float, np.ndarray]) -> Union[int, float, np.ndarray]:
    """
    Apply a signed log transformation to the input value(s).

    Args:
        x (Union[int, float, np.ndarray]): The input value(s) to be transformed.

    Returns:
        Union[int, float, np.ndarray]: The transformed value(s).
    """
    return np.sign(x) * np.log1p(np.abs(x))

class MapPlotter:
    def __init__(
        self,
        df: pd.DataFrame,
        activity: str,
        date_column: str,
        year: Union[int, str],
        region_type: str,
        arms_category: str,
        unit: str,
        region: Optional[str] = None
    ):
        """
        Initialize the MapPlotter class with the provided parameters.

        Args:
            df (pd.DataFrame): DataFrame containing the arms trade data.
            activity (str): The type of activity ('Supplied', 'Received', etc.).
            date_column (str): The name of the column containing date information.
            year (Union[int, str]): The year for which the data is to be plotted.
            region_type (str): The type of region ('Country', 'Former Country', etc.).
            arms_category (str): The category of arms.
            unit (str): The unit of measure.
            region (Optional[str], optional): The specific region to be plotted. Defaults to None.
        """
        self.df=df
        self.activity=activity
        self.date_column=date_column
        self.year=year
        self.region_type=region_type
        self.arms_category=arms_category
        self.unit=unit
        self.region=region

    def plot_choropleth(self) -> go.Figure:
        """
        Plot a choropleth map based on the initialized data and parameters.

        Returns:
            go.Figure: The generated choropleth map figure.
        """
        self.prepare_plot_data()
        if self.region:
            self.get_plot_dict_for_region()
        else:
            self.get_plot_dict_global()

        # Convert the filtered GeoDataFrame to GeoJSON format
        data_geojson = self.data.__geo_interface__
    
        # Create an interactive map using Plotly
        fig = px.choropleth(self.data,
                            geojson=data_geojson,
                            locations='Region',
                            featureidkey="properties.Region",
                            projection="equirectangular",
                            title=self.plot_dict['title'],
                            color=f"log {self.unit}",
                            color_continuous_scale=self.plot_dict['color_scale'],
                            color_continuous_midpoint=0
                           )
    
        fig.update_layout(
            width=1000,
            height=500,
            margin={"r":0, "t":50, "l":0, "b":0},
            showlegend=False,
            coloraxis_colorbar=dict(
                title=f"{self.unit}",
                tickvals=self.plot_dict['cbar_tickvals'],
                ticktext=self.plot_dict['cbar_ticktext'],
                len=0.8,
                thickness=10
            ),
            
        # fill in coutries with no activity in gray
        geo = dict(
            landcolor = 'lightgray',
            showland = True,
            showcountries = True,
            countrycolor = 'gray',
            countrywidth = 0.5,
            )
        )
    
        fig.update_geos(fitbounds="locations", visible=False)
        
        # Customize the hover template to show only the country name
        fig.update_traces(
            hovertemplate=self.plot_dict['hovertemplate'],
            customdata=self.plot_dict['customdata'],
        )

        # Highlight selected country
        if self.region:
            selected_country_df = world_map_data[world_map_data['iso_a3'] == self.iso_a3]
            geometry = selected_country_df.geometry.iloc[0]
            
            if str(type(geometry))=="<class 'shapely.geometry.polygon.Polygon'>":
                coords = geometry.exterior.coords.xy
                lon = coords[0].tolist()
                lat = coords[1].tolist()
                fig.add_trace(
                    go.Scattergeo(
                        lon=lon,
                        lat=lat,
                        mode='lines',
                        fill='toself',
                        line=dict(width=2, color='green'),
                        text=self.region,
                        hoverinfo="text"
                    )
                )
            else:
                selected_country_df = selected_country_df.explode(index_parts=True)
                for index, row in selected_country_df.iterrows():
                    geometry = row['geometry']
                    coords = geometry.exterior.coords.xy
                    lon = coords[0].tolist()
                    lat = coords[1].tolist()
                    fig.add_trace(
                        go.Scattergeo(
                            lon=lon,
                            lat=lat,
                            mode='lines',
                            fill='toself',
                            line=dict(width=2, color='green'),
                            text=self.region,
                            hoverinfo="text"
                        )
                    )
            
        return fig
        
    def prepare_plot_data(self):
        """
        Prepare the data for plotting by filtering, calculating totals, and merging with geolocation data.
        """
        self.filter_data()
        if self.region:
            self.calculate_totals_for_region()
        else:
            self.calculate_totals_global()
        self.filter_region_type()
        if self.data.shape[0]==0:
           raise Exception("No data for selected filters.")
        self.merge_geolocation_data()
        if self.region:
            self.get_region_iso_a3()

    def filter_data(self):
        """
        Filter the data based on the initialized parameters.
        """
        self.data = self.df.copy()
        
        if self.year != 'Overall':
            self.data=self.data[self.data[self.date_column]==int(self.year)]
        if self.arms_category != 'All':
            self.data=self.data[self.data['Armament category']==self.arms_category]
        if self.region:
            if self.activity=='Supplied':
                self.data=self.data[self.data['Supplier']==self.region]
                self.data=self.data[self.data['Recipient_region_type']==self.region_type]
            elif self.activity=='Received':
                self.data=self.data[self.data['Recipient']==self.region]
            else:
                self.data=self.data[(self.data['Supplier']==self.region) | (self.data['Recipient']==self.region)]

    def calculate_totals_for_region(self):
        """
        Calculate the total units for the specific region and activity.
        """
        if self.activity=="Supplied":
            self.data=self.data.groupby(["Recipient", "Recipient_iso_a3", "Recipient_region_type"])[self.unit].sum().reset_index()
            self.data.rename(columns={'Recipient':'Region', 'Recipient_iso_a3':'iso_a3', 'Recipient_region_type':'Region_type'}, inplace=True)
        elif self.activity=="Received":
            self.data=self.data.groupby(["Supplier", "Supplier_iso_a3", "Supplier_region_type"])[self.unit].sum().reset_index()
            self.data.rename(columns={'Supplier':'Region', 'Supplier_iso_a3':'iso_a3', 'Supplier_region_type':'Region_type'}, inplace=True)
        else:
            # note switch supplier and receiver compared to global
            received=self.data.groupby(["Supplier", "Supplier_iso_a3", "Supplier_region_type"])[self.unit].sum().reset_index().rename(columns={self.unit:'Supplied'})
            supplied=self.data.groupby(["Recipient", "Recipient_iso_a3", "Recipient_region_type"])[self.unit].sum().reset_index().rename(columns={self.unit:'Received'})
            self.data=pd.merge(
                left=supplied,
                right=received,
                how='outer',
                right_on=["Supplier", "Supplier_iso_a3", "Supplier_region_type"],
                left_on=["Recipient", "Recipient_iso_a3", "Recipient_region_type"]
            )
    
            # fill in null values and names
            self.data=self.data.fillna(0)
            self.data['Region']=self.data.apply(lambda row: row['Recipient'] if row['Recipient']!=0 else row['Supplier'], axis=1)
            self.data['iso_a3']=self.data.apply(lambda row: row['Recipient_iso_a3'] if row['Recipient_iso_a3']!=0 else row['Supplier_iso_a3'], axis=1)
            self.data['Region_type']=self.data.apply(lambda row: row['Recipient_region_type'] if row['Recipient_region_type']!=0 else row['Supplier_region_type'], axis=1)
            self.data.drop(columns=["Supplier", "Recipient", "Supplier_iso_a3", "Recipient_iso_a3", "Supplier_region_type", "Recipient_region_type"], inplace=True)
    
            if self.activity=="Net Balance":
                self.data[self.unit]=self.data["Received"]-self.data["Supplied"]
            elif self.activity=="Total Activity":
                self.data[self.unit]=self.data["Supplied"]+self.data["Received"]

        # drop data for chosen region
        if self.region:
            self.data=self.data[self.data['Region']!=self.region].copy()
        
        # Apply the signed log transformation to the units
        self.data[f'log {self.unit}'] = self.data[self.unit].apply(signed_log)

    def calculate_totals_global(self):
        """
        Calculate the total units globally for the specified activity.
        """
        if self.activity=="Supplied":
            self.data=self.data.groupby(["Supplier", "Supplier_iso_a3", "Supplier_region_type"])[self.unit].sum().reset_index()
            self.data.rename(columns={'Supplier':'Region', 'Supplier_iso_a3':'iso_a3', 'Supplier_region_type':'Region_type'}, inplace=True)
        elif self.activity=="Received":
            self.data=self.data.groupby(["Recipient", "Recipient_iso_a3", "Recipient_region_type"])[self.unit].sum().reset_index()
            self.data.rename(columns={'Recipient':'Region', 'Recipient_iso_a3':'iso_a3', 'Recipient_region_type':'Region_type'}, inplace=True)
        else:
            supplied=self.data.groupby(["Supplier", "Supplier_iso_a3", "Supplier_region_type"])[self.unit].sum().reset_index().rename(columns={self.unit:'Supplied'})
            received=self.data.groupby(["Recipient", "Recipient_iso_a3", "Recipient_region_type"])[self.unit].sum().reset_index().rename(columns={self.unit:'Received'})
            self.data=pd.merge(
                left=supplied,
                right=received,
                how='outer',
                left_on=["Supplier", "Supplier_iso_a3", "Supplier_region_type"],
                right_on=["Recipient", "Recipient_iso_a3", "Recipient_region_type"]
            )
    
            # fill in null values and names
            self.data=self.data.fillna(0)
            self.data['Region']=self.data.apply(lambda row: row['Recipient'] if row['Recipient']!=0 else row['Supplier'], axis=1)
            self.data['iso_a3']=self.data.apply(lambda row: row['Recipient_iso_a3'] if row['Recipient_iso_a3']!=0 else row['Supplier_iso_a3'], axis=1)
            self.data['Region_type']=self.data.apply(lambda row: row['Recipient_region_type'] if row['Recipient_region_type']!=0 else row['Supplier_region_type'], axis=1)
            self.data.drop(columns=["Supplier", "Recipient", "Supplier_iso_a3", "Recipient_iso_a3", "Supplier_region_type", "Recipient_region_type"], inplace=True)
    
            if self.activity=="Net Balance":
                self.data[self.unit]=self.data["Supplied"]-self.data["Received"]
            elif self.activity=="Total Activity":
                self.data[self.unit]=self.data["Supplied"]+self.data["Received"]

        # Apply the signed log transformation to the units
        self.data[f'log {self.unit}'] = self.data[self.unit].apply(signed_log)

    def filter_region_type(self):
        """
        Filter the data to include only the specified region type.
        """
        if self.region_type != "All regions":
            if self.region_type == "Country":
                self.data = self.data[self.data['Region_type'].isin(['Country', 'Former Country'])].copy()
            else:
                self.data = self.data[self.data['Region_type']==self.region_type]

    def merge_geolocation_data(self):
        """
        Merge the processed data with the world map geolocation data.
        """
        self.data = pd.merge(world_map_data, self.data, how='left', on=['iso_a3'])
        self.data['Region'] = self.data.apply(lambda row: row['name'] if row['Region_type'] in ['Country', 'Former Country'] else row['Region'], axis=1) 

    def get_plot_dict_global(self):
        """
        Generate the plot dictionary for global data.
        """
        title = f"{self.region} - "
        if self.year != "Overall":
            title += f"{str(self.year)} - "
        
        if self.activity=='Supplied':
                color_scale = px.colors.sequential.Blues
                title += "Weapons Supplied to other regions"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata:.2f}}<extra></extra>"
                customdata=np.stack(self.data[self.unit])
        elif self.activity=='Received':
                color_scale = px.colors.sequential.Reds
                title += "Weapons Received from other regions"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit]))
        elif self.activity=='Net Balance':
                color_scale = px.colors.sequential.RdBu
                title += "Net Balance (Supplied - Received)"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata[0]:.2f}}<br>Supplied by {self.region}: %{{customdata[1]:.2f}}<br>Received from other regions: %{{customdata[2]:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit], self.data['Supplied'],self.data['Received'],), axis=-1)
        elif self.activity=='Total Activity':
                color_scale = px.colors.sequential.Magenta
                title += "Total Activity (Supplied + Received)"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata[0]:.2f}}<br>Supplied by {self.region}: %{{customdata[1]:.2f}}<br>Received from other regions: %{{customdata[2]:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit], self.data['Supplied'],self. data['Received']), axis=-1)
    
        if self.arms_category != "All":
            title += f" - {self.arms_category}"

        tickvals, ticktext = self.get_cbar_ticks()
        
        self.plot_dict = {
            'color_scale':color_scale,
            'title':title,
            'hovertemplate':hovertemplate,
            'customdata':customdata,
            'cbar_tickvals':tickvals,
            'cbar_ticktext':ticktext
        }

    def get_plot_dict_for_region(self):
        """
        Generate the plot dictionary for specific region data.
        """
        title = ""
        if self.year != "Overall":
            title += f"{str(self.year)} - "
        
        if self.activity=='Supplied':
                color_scale = px.colors.sequential.Blues
                title += "Weapons Supplied"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata:.2f}}<extra></extra>"
                customdata=np.stack(self.data[self.unit])
        elif self.activity=='Received':
                color_scale = px.colors.sequential.Reds
                title += "Weapons Received"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit]))
        elif self.activity=='Net Balance':
                color_scale = px.colors.sequential.RdBu
                title += "Net Balance (Supplied - Received)"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata[0]:.2f}}<br>Supplied: %{{customdata[1]:.2f}}<br>Received: %{{customdata[2]:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit], self.data['Supplied'],self. data['Received']), axis=-1)
        elif self.activity=='Total Activity':
                color_scale = px.colors.sequential.Magenta
                title += "Total Activity (Supplied + Received)"
                hovertemplate=f"<b>%{{location}}</b><br>{self.unit}: %{{customdata[0]:.2f}}<br>Supplied: %{{customdata[1]:.2f}}<br>Received: %{{customdata[2]:.2f}}<extra></extra>"
                customdata=np.stack((self.data[self.unit], self.data['Supplied'],self. data['Received']), axis=-1)
    
        if self.arms_category != "All":
            title += f" - {self.arms_category}"

        tickvals, ticktext = self.get_cbar_ticks()
        
        self.plot_dict = {
            'color_scale':color_scale,
            'title':title,
            'hovertemplate':hovertemplate,
            'customdata':customdata,
            'cbar_tickvals':tickvals,
            'cbar_ticktext':ticktext
        }

    def get_cbar_ticks(self):
        """
        Get the colorbar tick labels and values.
        """
        if self.activity == "Net Balance":
            max_abs_value = self.data[self.unit].abs().max()
            max_abs_value = round(max_abs_value, -int(math.floor(math.log10(abs(max_abs_value)))))
            max_abs_value = 10 ** (int(math.log10(max_abs_value) + 1))
            powers_of_10_pos = [10**i for i in range(1, int(math.log10(max_abs_value) + 1))]
            powers_of_10_neg = [-x for x in powers_of_10_pos]
            powers_of_10 = sorted(powers_of_10_neg + [0] + powers_of_10_pos)

            tickvals=signed_log(np.array(powers_of_10))
            ticktext=powers_of_10
        else :
            max_abs_value = self.data[self.unit].abs().max()
            max_abs_value = round(max_abs_value, -int(math.floor(math.log10(abs(max_abs_value)))))
            max_abs_value = 10 ** (int(math.log10(max_abs_value) + 1))
            powers_of_10 = [10**i for i in range(1, int(math.log10(max_abs_value) + 1))]

            tickvals=signed_log(np.array(powers_of_10))
            ticktext=powers_of_10

        return tickvals, ticktext

    def get_region_iso_a3(self):
        """
        Get the ISO A3 code for the specified region.
        """
        try:
            self.iso_a3=self.df[self.df['Supplier']==self.region].Supplier_iso_a3.unique()[0]
        except:
            self.iso_a3=self.df[self.df['Recipient']==self.region].Recipient_iso_a3.unique()[0]