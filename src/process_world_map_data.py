import geopandas as gpd

def get_world_map_data() -> gpd.geodataframe.GeoDataFrame:
    """
    Retrieve and prepare world map data excluding Antarctica.

    This function loads the low-resolution world map dataset from Natural Earth, 
    extracts relevant columns, and removes Antarctica from the dataset.

    Returns:
        gpd.geodataframe.GeoDataFrame: A GeoDataFrame containing the world map data with columns 
        for continent, country name, ISO A3 code, and geometry.
    """
    naturalearth_lowres = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    world_map_data = naturalearth_lowres[['continent', 'name', 'iso_a3', 'geometry']].copy()
    world_map_data = world_map_data[world_map_data['name']!='Antarctica'].copy()
    
    return world_map_data