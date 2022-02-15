#%%
from pathlib import Path
from typing import List
import geopandas as gpd
import matplotlib.pyplot as plt
import logging
from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
import os
from glob import glob
from fiona.errors import DriverError
from shapely.geometry import Polygon
import georasters as gr
import pandas as pd
import folium
from IPython.display import display

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)-15s %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def load_dataset_wfs(dataset_name: str):
    wfs11 = WebFeatureService(
        url="https://kartta.hel.fi/ws/geoserver/avoindata/wfs", version="1.1.0"
    )
    # [operation.name for operation in wfs11.operations]
    # vars(wfs11.getOperationByName('GetFeature'))
    # vars(wfs11.getOperationByName('GetCapabilities'))
    # list(wfs11.contents)
    # wfs11.contents[dataset_name].boundingBoxWGS84
    # wfs11.contents[dataset_name]

    file_name = dataset_name.replace("avoindata:", "")
    response = wfs11.getfeature(
        typename=dataset_name,
        # bbox=wms.contents[dataset_name].boundingBoxWGS84,
        # srsname='urn:x-ogc:def:crs:EPSG:3879',
        # outputFormat="application/json"
    )
    with open(f"data/{file_name}.gml", "wb") as f:
        f.write(bytes(response.read()))


def read_map_file(str_path: str, type="gml"):
    if type == "gml":
        logger.info(f"Reading {str_path}")
        return gpd.read_file(str_path, driver="GML", crs="epsg:3879")
    else:
        raise ValueError("Unsupported file type")


def plot_layer(d, ax, boundary=False, **kwargs) -> None:

    logger.info(f"Making plot from {Path(file_path).stem}")
    if boundary:
        d.boundary.plot(ax=ax, **kwargs)
    else:
        d.plot(ax=ax, **kwargs)


#%%
# if __name__ == '__main__':
if True:
    os.makedirs("data", exist_ok=True)
    best_place = None
    constraints = None
    ## define bbox so we don't draw all of HEL
    xlim = (2.5491 * 1e7, 2.5902 * 1e7)
    ylim = (6.670 * 1e6, 6.690 * 1e6)
    bbox = gpd.GeoSeries(
        Polygon(
            [
                (xlim[0], ylim[0]),
                (xlim[0], ylim[1]),
                (xlim[1], ylim[1]),
                (xlim[1], ylim[0]),
            ]
        )
    )
    bbox = gpd.GeoDataFrame({"geometry": bbox, "df1_data": [1]})

    # TODO: raster base map?
    # myRaster = 'data/OpHki_4m_harmaa_pohja.tif'
    # base_map = gr.from_file(myRaster)

    # Define datasets
    open_data_datasets = [
        #"avoindata:Opaskartta_alue",
        # "avoindata:Maavesi_vesialue_yleistetty",
        "avoindata:Maavesi_merialue",
        # "avoindata:Maavesi_muut_vesialueet",
        "avoindata:YLRE_Viheralue_alue",
        # "avoindata:Toimipisterekisteri_yksikot",
        "avoindata:Toimipisterekisteri_palvelut",
        "avoindata:Postinumeroalue",
    ]
    data_paths = [Path(x).stem for x in glob("data/*.gml")]
    for dataset in open_data_datasets:
        file_name = dataset.replace("avoindata:", "")
        if file_name not in data_paths:
            logger.info(f"Downloading {dataset}")
            load_dataset_wfs(dataset_name=dataset)
        else:
            logger.info(f"Dataset {dataset} already exists.")

    #%%
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_aspect("equal")
    plot_kwargs = {
        "avoindata:Maavesi_merialue": {"alpha": 0.2, "color": "blue"},
        "avoindata:Maavesi_muut_vesialueet": {"alpha": 0.2, "color": "blue"},
        "avoindata:YLRE_Viheralue_alue": {"alpha": 0.2, "color": "green"},
        "avoindata:Postinumeroalue": {"edgecolor": "grey", "linewidth": 1},
        "avoindata:Toimipisterekisteri_palvelut": {"alpha": 0.2, "color": "purple"},
        "avoindata:Opaskartta_alue": {"linewidth": 0.05, "color": "black"},
    }
    for dataset in open_data_datasets:
        file_path = "data/" + dataset.replace("avoindata:", "") + ".gml"
        try:
            d = read_map_file(file_path)
        except DriverError as e:
            raise e
        d = gpd.overlay(d, bbox)

        if dataset == "avoindata:Toimipisterekisteri_palvelut":
            esiopetus = d.loc[d.service_ids == "160"]
            suomenkielinen_pvhoito = d.loc[d.service_ids == "663"]
            suomenkielinen_alakoulu = d.loc[d.service_ids == "661"]
            suomenkielinen_ylakoulu = d.loc[d.service_ids == "662"]
            uimaranta = d.loc[d.service_ids == "731"]
            urheilukentta = d.loc[d.service_ids == "817"]
            kuntosalit = d.loc[d.service_ids == "350"]
            d = suomenkielinen_pvhoito
            DAYCARE_BUFFER = 500
            LOWER_SCHOOL_BUFFER = 500
            UPPER_SCHOOL_BUFFER = 2000
            TRACK_FIELD_BUFFER = 10000
            d["geometry"] = d.buffer(DAYCARE_BUFFER)
            d["constraint_name"] = "daycare"
            d = d[["constraint_name", "geometry"]]

            def get_buffered_subdata(data, constraint_name, buffer):
                data["constraint_name"] = constraint_name
                data["geometry"] = data.buffer(buffer)
                return data[["constraint_name", "geometry"]]

            suomenkielinen_alakoulu = get_buffered_subdata(
                suomenkielinen_alakoulu, "lower_school", LOWER_SCHOOL_BUFFER
            )
            suomenkielinen_ylakoulu = get_buffered_subdata(
                suomenkielinen_ylakoulu, "upper_school", UPPER_SCHOOL_BUFFER
            )
            urheilukentta = get_buffered_subdata(
                urheilukentta, "track_field", TRACK_FIELD_BUFFER
            )
            # TODO: These need to be added to constraints separately
            d = pd.concat([d, suomenkielinen_alakoulu])
            d = pd.concat([d, suomenkielinen_ylakoulu])
            #d = pd.concat([d, urheilukentta])

        if dataset == "avoindata:YLRE_Viheralue_alue":
            big_parks = d
            big_parks["area"] = big_parks.geometry.apply(lambda x: x.area)
            PARK_MIN_AREA = 110000
            BUFFER_DISTANCE = 700
            big_parks = big_parks.loc[big_parks["area"] > PARK_MIN_AREA]
            d["geometry"] = big_parks.buffer(BUFFER_DISTANCE)
            d["constraint_name"] = "big_park"

        if dataset == "avoindata:Maavesi_merialue":
            water_areas = d
            WATER_BUFFER_DISTANCE = 700
            d["geometry"] = water_areas.buffer(WATER_BUFFER_DISTANCE)
            d["constraint_name"] = "sea"

        if dataset == "avoindata:Maavesi_muut_vesialueet":
            small_water_areas = d
            SMALL_WATER_BUFFER_DISTANCE = 100
            d["geometry"] = small_water_areas.buffer(SMALL_WATER_BUFFER_DISTANCE)
            d["constraint_name"] = "other_water"

        new_kwargs = plot_kwargs.get(dataset, {})
        if (
            dataset == "avoindata:Postinumeroalue"
            or dataset == "avoindata:Opaskartta_alue"
        ):
            plot_layer(d, ax=ax, boundary=True, **new_kwargs)
        else:
            plot_layer(d, ax=ax, boundary=False, **new_kwargs)
            constraints = pd.concat(
                [
                    constraints,
                    d[["constraint_name", "geometry"]].dropna(subset=["geometry"]),
                ]
            )
            # print(best_place.shape)
            # print(best_place.head(2))
    ax.set_axis_off()
    plt.show()
#%%
constraints

#%%
constraints.head()
# %%
m2 = folium.Map(location=[60.18, 24.94], zoom_start=11)
best_place = None
for constr in sorted(list(constraints.constraint_name.unique())):
    print(constr)
    if best_place is None:
        best_place = constraints.loc[
            constraints.constraint_name == constr, ["constraint_name", "geometry"]
        ].dropna(subset=["geometry"])
    else:
        if (
            len(
                constraints.loc[
                    constraints.constraint_name == constr,
                    ["constraint_name", "geometry"],
                ].dropna(subset=["geometry"])
            )
            == 0
        ):
            print(f"Skipping {constr}")
            continue
        best_place = gpd.overlay(
            best_place,
            constraints.loc[
                constraints.constraint_name == constr, ["constraint_name", "geometry"]
            ]
            .dropna(subset=["geometry"])
            .rename(columns={"constraint_name": constr}),
            how="intersection",
        )

# folium.TileLayer('Stamen Toner', control=True).add_to(m)  # use folium to add alternative tiles
best_place.set_crs(epsg=3879).explore(
    popup=False,
    tiles="OpenStreetMap",
    cmap="red",
    style_kwds=dict(color="red", opacity=0.0, fillOpacity=0.1),
    m=m2,
)

# %%
m = folium.Map(location=[60.18, 24.94], zoom_start=11)
# folium.TileLayer('Stamen Toner', control=True).add_to(m)  # use folium to add alternative tiles
def my_colormapper(x):
    colormap = {"big_park": "green", "daycare": "purple", "sea": "blue"}
    return plt.colormap.get(x, "red")


constraints.set_crs(epsg=3879).explore(
    column="constraint_name",
    tooltip="constraint_name",
    popup=True,
    tiles="OpenStreetMap",
    cmap=["green", "purple", "orange", "blue", "darkred", "yellow"],
    style_kwds=dict(color="black", opacity=0.0, fillOpacity=0.1),
    m=m,
)
# m