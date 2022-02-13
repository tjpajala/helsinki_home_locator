from fileinput import filename
from pathlib import Path
from tkinter import E
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


logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)-15s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def load_dataset_wfs(dataset_name:str):
    wfs11 = WebFeatureService(url='https://kartta.hel.fi/ws/geoserver/avoindata/wfs', version='1.1.0')
    # [operation.name for operation in wfs11.operations]
    # vars(wfs11.getOperationByName('GetFeature'))
    # vars(wfs11.getOperationByName('GetCapabilities'))
    # list(wfs11.contents)
    # wfs11.contents[dataset_name].boundingBoxWGS84
    # wfs11.contents[dataset_name]

    file_name = dataset_name.replace("avoindata:","")
    response = wfs11.getfeature(
        typename=dataset_name, 
        #bbox=wms.contents[dataset_name].boundingBoxWGS84, 
        #srsname='urn:x-ogc:def:crs:EPSG:3879',
        #outputFormat="application/json"
        )
    with open(f'data/{file_name}.gml', 'wb') as f:
        f.write(bytes(response.read()))





def read_map_file(str_path: str, type="gml"):
    if type=="gml":
        logger.info(f"Reading {str_path}")
        return gpd.read_file(str_path, driver='GML')
    else:
        raise ValueError("Unsupported file type")

def plot_layer(d, ax, boundary=False, **kwargs) -> None:
    
    logger.info(f"Making plot from {Path(file_path).stem}")
    if boundary:
        d.boundary.plot(ax=ax, **kwargs)
    else:
        d.plot(ax=ax, **kwargs)


if __name__ == '__main__':

    ## define bbox so we don't draw all of HEL
    xlim = (2.5491*1e7, 2.5502*1e7)
    ylim = (6.670*1e6, 6.680*1e6)
    bbox = gpd.GeoSeries(Polygon([
        (xlim[0], ylim[0]),
        (xlim[0], ylim[1]),
        (xlim[1], ylim[1]),
        (xlim[1], ylim[0]),
         ])
         )
    bbox=gpd.GeoDataFrame({'geometry': bbox, 'df1_data':[1]})

    # Define datasets
    open_data_datasets = [
        #"avoindata:Maavesi_vesialue_yleistetty",
        "avoindata:Maavesi_merialue",
        "avoindata:Maavesi_muut_vesialueet",
        "avoindata:YLRE_Viheralue_alue",
        #"avoindata:Toimipisterekisteri_yksikot",
        "avoindata:Toimipisterekisteri_palvelut"
        'avoindata:Postinumeroalue'
    ]
    data_paths = [Path(x).stem for x in glob("data/*.gml")]
    for dataset in open_data_datasets:
        file_name = dataset.replace("avoindata:","")
        if file_name not in data_paths:
            logger.info(f"Downloading {dataset}")
            load_dataset_wfs(dataset_name=dataset)
        else:
            logger.info(f"Dataset {dataset} already exists.")

    fig, ax = plt.subplots(figsize=(12,8))
    ax.set_aspect('equal')
    plot_kwargs = {
        'avoindata:Maavesi_merialue': {"alpha":0.2, "color":"blue"},
        "avoindata:Maavesi_muut_vesialueet": {"alpha":0.2, "color":"blue"},
        "avoindata:YLRE_Viheralue_alue":{"alpha":0.3, "color":"green"},
        'avoindata:Postinumeroalue': {"edgecolor":"grey", "linewidth":1},
    }
    for dataset in open_data_datasets:
        file_path = "data/" + dataset.replace("avoindata:","") + ".gml"
        try:
            d = read_map_file(file_path)
        except DriverError as e:
            raise e
        d = gpd.overlay(d, bbox)

        if dataset == 'avoindata:Toimipisterekisteri_palvelut':
            esiopetus = d.loc[d.service_ids=="160"]
            suomenkielinen_pvhoito = d.loc[d.service_ids=="663"]
            suomenkielinen_alakoulu = d.loc[d.service_ids=="661"]
            suomenkielinen_ylakoulu = d.loc[d.service_ids=="662"]
            uimaranta = d.loc[d.service_ids=="731"]
            urheilukentta = d.loc[d.service_ids=="817"]
            kuntosalit = d.loc[d.service_ids=="350"]

        new_kwargs = plot_kwargs.get(dataset, {})
        if dataset == 'avoindata:Postinumeroalue':
            plot_layer(d, ax=ax, boundary=True, **new_kwargs)
        else:
            plot_layer(d, ax=ax, boundary=False, **new_kwargs)
    ax.set_axis_off()
    plt.show()