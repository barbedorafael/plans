"""
Description:
    The ``iamlazy`` module provides useful template routines for pre-processing input data
    in QGIS 3.x Python console.

License:
    This software is released under the GNU General Public License v3.0 (GPL-3.0).
    For details, see: https://www.gnu.org/licenses/gpl-3.0.html

Author:
    Iporã Possantti

Contact:
    possantti@gmail.com


Overview
--------

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nulla mollis tincidunt erat eget iaculis.
Required dependencies:

- pcraster
- saga
- gdal
- processing
- geopandas

Mauris gravida ex quam, in porttitor lacus lobortis vitae.
In a lacinia nisl. Pellentesque habitant morbi tristique senectus
et netus et malesuada fames ac turpis egestas.

>>> from plans import iamlazy

Class aptent taciti sociosqu ad litora torquent per
conubia nostra, per inceptos himenaeos. Nulla facilisi. Mauris eget nisl
eu eros euismod sodales. Cras pulvinar tincidunt enim nec semper.

Example
-------

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nulla mollis tincidunt erat eget iaculis. Mauris gravida ex quam,
in porttitor lacus lobortis vitae. In a lacinia nisl.

.. code-block:: python

    import numpy as np
    from plans import analyst

    # get data to a vector
    data_vector = np.random.rand(1000)

    # instantiate the Univar object
    uni = analyst.Univar(data=data_vector, name="my_data")

    # view data
    uni.view()

Mauris gravida ex quam, in porttitor lacus lobortis vitae.
In a lacinia nisl. Mauris gravida ex quam, in porttitor lacus lobortis vitae.
In a lacinia nisl.
"""
import processing
from osgeo import gdal
from qgis.core import QgsCoordinateReferenceSystem
import numpy as np
from plans import geo
import os, shutil
import geopandas as gpd


def reproject_layer(input_db, target_crs, layer_name=None):
    """Reproject a vector layer

    :param input_db: path to database
    :type input_db: str
    :param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param layer_name: name of the layer in database (for geopackage)
    :type layer_name: str
    :return: new layer name
    :rtype: str
    """
    dict_operations = {
        "31983": {"zone": 23, "hem": "south"},
        "31982": {"zone": 22, "hem": "south"},
        "31981": {"zone": 21, "hem": "south"},
    }
    if layer_name is None:  # to shapefile
        input_file = input_db
        output_dir = os.path.dirname(input_file)
        output_name = os.path.basename(input_file).split(".")[0]
        output_file = "{}/{}_EPSG{}.shp".format(output_dir, output_name, target_crs)
        new_layer_name = output_file
    else:  # to geopackage
        input_file = "{}|layername={}".format(input_db, layer_name)
        new_layer_name = "{}_EPSG{}".format(layer_name, target_crs)
        output_file = "ogr:dbname='{}' table=\"{}\" (geom)".format(
            input_db, new_layer_name
        )
    processing.run(
        "native:reprojectlayer",
        {
            "INPUT": input_file,
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "OPERATION": "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=utm +zone={} +{} +ellps=GRS80".format(
                dict_operations[target_crs]["zone"], dict_operations[target_crs]["hem"]
            ),
            "OUTPUT": output_file,
        },
    )
    return new_layer_name


def is_bounded_by(extent_a, extent_b):
    """Check if extent B is bounded by extent A

    :param extent_a: extent A
    :type extent_a: dict
    :param extent_b: extent B
    :type extent_b: dict
    :return: Case if bounded
    :rtype: bool
    """
    return (
        extent_a["xmin"] <= extent_b["xmin"] <= extent_b["xmax"] <= extent_a["xmax"]
        and extent_a["ymin"] <= extent_b["ymin"] <= extent_b["ymax"] <= extent_a["ymax"]
    )


def get_extent_raster(file_input):
    """Get the extent from a raster layer

    :param file_input: file path to raster layer
    :type file_input: str
    :return: dictionary of bouding box: xmin, xmax, ymin, ymax
    :rtype: dict
    """
    from qgis.core import QgsRasterLayer

    # Create a raster layer object
    raster_layer = QgsRasterLayer(file_input, "Raster Layer")
    layer_extent = raster_layer.extent()

    return {
        "xmin": layer_extent.xMinimum(),
        "xmax": layer_extent.xMaximum(),
        "ymin": layer_extent.yMinimum(),
        "ymax": layer_extent.yMaximum(),
    }


def get_extent_vector(input_db, layer_name):
    """Get the extent from a vector layer

    :param input_db: path to geopackage database
    :type input_db: str
    :param layer_name: name of the layer in geopackage database
    :type layer_name: str
    :return: dictionary of bouding box: xmin, xmax, ymin, ymax
    :rtype: dict
    """
    from qgis.core import QgsVectorLayer

    # Create the vector layer from the GeoPackage
    layer = QgsVectorLayer(
        "{}|layername={}".format(input_db, layer_name), layer_name, "ogr"
    )
    layer_extent = layer.extent()
    return {
        "xmin": layer_extent.xMinimum(),
        "xmax": layer_extent.xMaximum(),
        "ymin": layer_extent.yMinimum(),
        "ymax": layer_extent.yMaximum(),
    }


def get_feature_count(input_db, layer_name):
    """Get the number of features from a vector layer

    :param input_db: path to geopackage database
    :type input_db: str
    :param layer_name: name of the layer in geopackage database
    :type layer_name: str
    :return: number of features
    :rtype: int
    """
    from qgis.core import QgsVectorLayer

    # Create the vector layer from the GeoPackage
    layer = QgsVectorLayer(
        "{}|layername={}".format(input_db, layer_name), layer_name, "ogr"
    )
    return int(layer.featureCount())


def get_cellsize(file_input):
    """Get the cell size in map units (degrees or meters)

    :param file_input: path to raster file
    :type file_input: str
    :return: number of cell resolution in map units
    :rtype: float
    """
    # Open the raster file using gdal
    raster_input = gdal.Open(file_input)
    raster_geotransform = raster_input.GetGeoTransform()
    cellsize = raster_geotransform[1]
    # -- Close the raster
    raster_input = None
    return cellsize


def get_blank_raster(file_input, file_output, blank_value=0):
    """get a blank raster copy from other raster

    :param file_input: path to input raster file
    :type file_input: str
    :param file_output: path to output raster file
    :type file_output: str
    :param blank_value: value for constant blank raster
    :type blank_value: int
    :return: file path of output (echo)
    :rtype: str
    """
    # -------------------------------------------------------------------------
    # LOAD

    # Open the raster file using gdal
    raster_input = gdal.Open(file_input)

    # Get the raster band
    band_input = raster_input.GetRasterBand(1)

    # Read the raster data as a numpy array
    grid_input = band_input.ReadAsArray()

    # -- Collect useful metadata

    raster_x_size = raster_input.RasterXSize
    raster_y_size = raster_input.RasterYSize
    raster_projection = raster_input.GetProjection()
    raster_geotransform = raster_input.GetGeoTransform()

    # -- Close the raster
    raster_input = None

    # -------------------------------------------------------------------------
    # PROCESS
    # get ones to byte integer
    grid_input = np.ones(shape=grid_input.shape, dtype=np.uint8)

    grid_output = grid_input * blank_value

    # -------------------------------------------------------------------------
    # EXPORT RASTER FILE
    # Get the driver to create the new raster
    driver = gdal.GetDriverByName("GTiff")

    # Create a new raster with the same dimensions as the original
    raster_output = driver.Create(
        file_output, raster_x_size, raster_y_size, 1, gdal.GDT_Byte
    )

    # Set the projection and geotransform of the new raster to match the original
    raster_output.SetProjection(raster_projection)
    raster_output.SetGeoTransform(raster_geotransform)

    # Write the new data to the new raster
    raster_output.GetRasterBand(1).WriteArray(grid_output)

    # Close
    raster_output = None
    return file_output


def get_dem(
    file_main_dem,
    file_output,
    target_crs,
    target_extent_dict,
    target_cellsize=30,
    source_crs="4326",
):
    """Get a reprojected DEM raster from a larger DEM dataset

    :param file_main_dem: file path to main DEM dataset raster
    :type file_main_dem: str
    :param file_output: file path to output raster
    :type file_output: str
    :param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param target_extent_dict: dictionary of bouding box: xmin, xmax, ymin, ymax
    :type target_extent_dict: dict
    :param target_cellsize: target resolution of cellsize in map units (degrees or meters)
    :type target_cellsize: float
    :param source_crs: EPSG code (number only) for the source CRS. default is WGS-84 (4326)
    :type source_crs: str
    :return: file path of output (echo)
    :rtype: str
    """
    # get extent string
    target_extent_str = "{},{},{},{} [EPSG:{}]".format(
        target_extent_dict["xmin"],
        target_extent_dict["xmax"],
        target_extent_dict["ymin"],
        target_extent_dict["ymax"],
        target_crs,
    )
    # run warp
    processing.run(
        "gdal:warpreproject",
        {
            "INPUT": file_main_dem,
            "SOURCE_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(source_crs)),
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "RESAMPLING": 5,  # average=5; nearest=0
            "NODATA": -1,
            "TARGET_RESOLUTION": target_cellsize,  # in meters
            "OPTIONS": "",
            "DATA_TYPE": 6,  # float32=6, byte=1
            "TARGET_EXTENT": target_extent_str,
            "TARGET_EXTENT_CRS": QgsCoordinateReferenceSystem(
                "EPSG:{}".format(target_crs)
            ),
            "MULTITHREADING": False,
            "EXTRA": "",
            "OUTPUT": file_output,
        },
    )
    return file_output


def get_downstream_ids(file_ldd, file_basins, file_outlets):
    """Get the basin Ids from downstream cells

    :param file_ldd: file path to LDD raster
    :type file_ldd: str
    :param file_basins: file path to basins raster
    :type file_basins: str
    :param file_outlets: file path to outlets raster
    :type file_outlets: str
    :return: dictionaty with lists of "Id" and "Downstream_Id"
    :rtype: dict
    """

    # -------------------------------------------------------------------------
    # LOAD LDD

    # Open the raster file using gdal
    raster_input = gdal.Open(file_ldd)

    # Get the raster band
    band_input = raster_input.GetRasterBand(1)

    # Read the raster data as a numpy array
    grid_ldd = band_input.ReadAsArray()
    # truncate to byte integer
    grid_ldd = grid_ldd.astype(np.uint8)

    # -- Close the raster
    raster_input = None

    # -------------------------------------------------------------------------
    # LOAD OUTLETS

    # Open the raster file using gdal
    raster_input = gdal.Open(file_outlets)

    # Get the raster band
    band_input = raster_input.GetRasterBand(1)

    # Read the raster data as a numpy array
    grid_outlets = band_input.ReadAsArray()
    # truncate to byte integer
    grid_outlets = grid_outlets.astype(np.uint8)

    # -- Close the raster
    raster_input = None

    # -------------------------------------------------------------------------
    # LOAD BASINS

    # Open the raster file using gdal
    raster_input = gdal.Open(file_basins)

    # Get the raster band
    band_input = raster_input.GetRasterBand(1)

    # Read the raster data as a numpy array
    grid_basins = band_input.ReadAsArray()
    # truncate to byte integer
    grid_basins = grid_basins.astype(np.uint8)

    # -- Close the raster
    raster_input = None

    # -------------------------------------------------------------------------
    # PROCESS

    # Get the indices of non-zero elements
    nonzero_indices = np.nonzero(grid_outlets)
    # Create a list of tuples containing row and column indices
    list_positions = list(zip(nonzero_indices[0], nonzero_indices[1]))

    list_ids = list()
    list_ds_ids = list()
    for outlet in list_positions:
        i = outlet[0]
        j = outlet[1]
        # get the ID
        n_id = grid_outlets[i][j]
        # get the direction code (LDD)
        n_dir = grid_ldd[i][j]
        # get downstream coordinates
        dict_dc = geo.downstream_coordinates(n_dir=n_dir, i=i, j=j, s_convention="ldd")
        new_i = dict_dc["i"]
        new_j = dict_dc["j"]
        n_ds_id = grid_basins[new_i][new_j]
        list_ids.append(n_id)
        list_ds_ids.append(n_ds_id)

    return {"Id": list_ids, "Downstream_Id": list_ds_ids}


def get_carved_dem(file_dem, file_rivers, file_output, w=3, h=10):
    """Apply a carving method to DEM raster

    :param file_dem: file path to DEM raster
    :type file_dem: str
    :param file_rivers: file path to main rivers pseudo-boolean raster
    :type file_rivers: str
    :param file_output: file path to output raster
    :type file_output: str
    :param w: width parameter in unit cells
    :type w: int
    :param h: height parameter in dem units (e.g., meters)
    :type h: float
    :return: file path of output (echo)
    :rtype: str
    """
    # -------------------------------------------------------------------------
    # LOAD DEM

    # Open the raster file using gdal
    raster_dem = gdal.Open(file_dem)

    # Get the raster band
    band_dem = raster_dem.GetRasterBand(1)

    # Read the raster data as a numpy array
    grd_dem = band_dem.ReadAsArray()

    # -- Collect useful metadata

    raster_x_size = raster_dem.RasterXSize
    raster_y_size = raster_dem.RasterYSize
    raster_projection = raster_dem.GetProjection()
    raster_geotransform = raster_dem.GetGeoTransform()

    # -- Close the raster
    raster_dem = None

    # -------------------------------------------------------------------------
    # LOAD RIVERs

    # Open the raster file using gdal
    raster_rivers = gdal.Open(file_rivers)

    # Get the raster band
    band_rivers = raster_rivers.GetRasterBand(1)

    # Read the raster data as a numpy array
    grd_rivers = band_rivers.ReadAsArray()

    # truncate to byte integer
    grd_rivers = grd_rivers.astype(np.uint8)

    # -- Close the raster
    raster_rivers = None

    # -------------------------------------------------------------------------
    # PROCESS
    grid_output = geo.burn_dem(grd_dem=grd_dem, grd_rivers=grd_rivers, w=w, h=h)

    # -------------------------------------------------------------------------
    # EXPORT RASTER FILE
    # Get the driver to create the new raster
    driver = gdal.GetDriverByName("GTiff")

    # Create a new raster with the same dimensions as the original
    raster_output = driver.Create(
        file_output, raster_x_size, raster_y_size, 1, gdal.GDT_Float32
    )

    # Set the projection and geotransform of the new raster to match the original
    raster_output.SetProjection(raster_projection)
    raster_output.SetGeoTransform(raster_geotransform)

    # Write the new data to the new raster
    raster_output.GetRasterBand(1).WriteArray(grid_output)

    # Close
    raster_output = None
    return file_output


def get_slope(file_dem, file_output):
    """Get the Slope map in degrees from a DEM raster

    :param file_dem: file path to DEM raster
    :type file_dem: str
    :param file_output: file path to output raster
    :type file_output: str
    :return: file path of output (echo)
    :rtype: str
    """
    # -------------------------------------------------------------------------
    # LOAD DEM

    # Open the raster file using gdal
    raster_dem = gdal.Open(file_dem)

    # Get the raster band
    band_dem = raster_dem.GetRasterBand(1)

    # Read the raster data as a numpy array
    grd_dem = band_dem.ReadAsArray()

    # -- Collect useful metadata

    raster_x_size = raster_dem.RasterXSize
    raster_y_size = raster_dem.RasterYSize
    raster_projection = raster_dem.GetProjection()
    raster_geotransform = raster_dem.GetGeoTransform()
    cellsize = raster_geotransform[1]
    # -- Close the raster
    raster_dem = None

    # -------------------------------------------------------------------------
    # PROCESS
    grid_output = geo.slope(dem=grd_dem, cellsize=cellsize, degree=True)

    # -------------------------------------------------------------------------
    # EXPORT RASTER FILE
    # Get the driver to create the new raster
    driver = gdal.GetDriverByName("GTiff")

    # Create a new raster with the same dimensions as the original
    raster_output = driver.Create(
        file_output, raster_x_size, raster_y_size, 1, gdal.GDT_Float32
    )

    # Set the projection and geotransform of the new raster to match the original
    raster_output.SetProjection(raster_projection)
    raster_output.SetGeoTransform(raster_geotransform)

    # Write the new data to the new raster
    raster_output.GetRasterBand(1).WriteArray(grid_output)

    # Close
    raster_output = None
    return file_output


def get_twi(file_slope, file_flowacc, file_output):
    """Get the TWI map from Slope and Flow Accumulation (SAGA)

    :param file_slope: file path to Slope raster map
    :type file_slope: str
    :param file_flowacc: file path to Flow Accumulation raster map
    :type file_flowacc: str
    :param file_output: file path to output raster
    :type file_output: str
    :return: file path of output (echo)
    :rtype: str
    """
    # -------------------------------------------------------------------------
    # LOAD SLOPE

    # Open the raster file using gdal
    raster_slope = gdal.Open(file_slope)

    # Get the raster band
    band_slope = raster_slope.GetRasterBand(1)

    # Read the raster data as a numpy array
    grd_slope = band_slope.ReadAsArray()

    # -- Collect useful metadata

    raster_x_size = raster_slope.RasterXSize
    raster_y_size = raster_slope.RasterYSize
    raster_projection = raster_slope.GetProjection()
    raster_geotransform = raster_slope.GetGeoTransform()
    cellsize = raster_geotransform[1]
    # -- Close the raster
    raster_slope = None

    # -------------------------------------------------------------------------
    # LOAD RIVERs

    # Open the raster file using gdal
    raster_flowacc = gdal.Open(file_flowacc)

    # Get the raster band
    band_flowacc = raster_flowacc.GetRasterBand(1)

    # Read the raster data as a numpy array
    grd_flowacc = band_flowacc.ReadAsArray()

    # -- Close the raster
    raster_flowacc = None

    # -------------------------------------------------------------------------
    # PROCESS
    grid_output = geo.twi(slope=grd_slope, flowacc=grd_flowacc, cellsize=cellsize)

    # -------------------------------------------------------------------------
    # EXPORT RASTER FILE
    # Get the driver to create the new raster
    driver = gdal.GetDriverByName("GTiff")

    # Create a new raster with the same dimensions as the original
    raster_output = driver.Create(
        file_output, raster_x_size, raster_y_size, 1, gdal.GDT_Float32
    )

    # Set the projection and geotransform of the new raster to match the original
    raster_output.SetProjection(raster_projection)
    raster_output.SetGeoTransform(raster_geotransform)

    # Write the new data to the new raster
    raster_output.GetRasterBand(1).WriteArray(grid_output)

    # Close
    raster_output = None
    return file_output


def get_hand(file_dem_filled, output_folder, hand_cells=100, file_dem_sample=None):
    """Get the HAND raster map from a DEM.
    The DEM must be hydrologically consistent (no sinks).

    :param file_dem_filled: file path to filled DEM (no sinks)
    :type file_dem_filled: str
    :param output_folder: path to output folder
    :type output_folder: str
    :param hand_cells: threshhold for HAND in number of maximum hillslope cells
    :type hand_cells: int
    :param file_dem_sample: [optional] file path to raw DEM for sampling the HAND.
    :type file_dem_sample: str
    :return: dictionary with raster output paths. keys:
        "ldd", "material", "accflux", "threshold", "drainage", "hs_outlets_scalar",
        "hs_outlets_nominal", "hillslopes", "hs_zmin", "hand"

    :rtype: dict
    """
    # -- PCRaster - get LDD map
    file_ldd = "{}/ldd.map".format(output_folder)
    processing.run(
        "pcraster:lddcreate",
        {
            "INPUT": file_dem_filled,
            "INPUT0": 0,
            "INPUT1": 0,
            "INPUT2": 9999999,
            "INPUT4": 9999999,
            "INPUT3": 9999999,
            "INPUT5": 9999999,
            "OUTPUT": file_ldd,
        },
    )
    # -- PCRaster - create material layer with cell x cell (area)
    cellsize = get_cellsize(file_input=file_dem_filled)
    file_material = "{}/material.map".format(output_folder)
    processing.run(
        "pcraster:spatial",
        {
            "INPUT": cellsize * cellsize,
            "INPUT1": 3,
            "INPUT2": file_dem_filled,
            "OUTPUT": file_material,
        },
    )
    # -- PCRaster - accumulate flux
    file_accflux = "{}/accflux.map".format(output_folder)
    processing.run(
        "pcraster:accuflux",
        {
            "INPUT": file_ldd,
            "INPUT2": file_material,
            "OUTPUT": file_accflux,
        },
    )
    # -- PCRaster - create drainage threshold layer with
    file_threshold = "{}/threshold.map".format(output_folder)
    processing.run(
        "pcraster:spatial",
        {
            "INPUT": hand_cells * cellsize * cellsize,
            "INPUT1": 3,
            "INPUT2": file_dem_filled,
            "OUTPUT": file_threshold,
        },
    )
    # -- PCRaster - create drainage boolean
    file_drainage = "{}/drainage.map".format(output_folder)
    processing.run(
        "pcraster:comparisonoperators",
        {
            "INPUT": file_accflux,
            "INPUT1": 1,
            "INPUT2": file_threshold,
            "OUTPUT": file_drainage,
        },
    )
    # -- PCRaster - create unique ids Map
    file_outlets_1 = "{}/hs_outlets_scalar.map".format(output_folder)
    processing.run(
        "pcraster:uniqueid",
        {"INPUT": file_drainage, "OUTPUT": file_outlets_1},
    )

    # -- PCRaster - convert unique ids to nominal
    file_outlets_2 = "{}/hs_outlets_nominal.map".format(output_folder)
    processing.run(
        "pcraster:convertdatatype",
        {
            "INPUT": file_outlets_1,
            "INPUT1": 1,
            "OUTPUT": file_outlets_2,
        },
    )
    # -- PCRaster - create subcatchments
    file_hillslopes = "{}/hillslopes.map".format(output_folder)
    processing.run(
        "pcraster:subcatchment",
        {
            "INPUT1": file_ldd,
            "INPUT2": file_outlets_2,
            "OUTPUT": file_hillslopes,
        },
    )

    # -- PCRaster - sample z min by catchment
    file_zmin = "{}/hs_zmin.map".format(output_folder)
    if file_dem_sample is None:
        file_dem_sample = file_dem_filled
    processing.run(
        "pcraster:areaminimum",
        {
            "INPUT": file_hillslopes,
            "INPUT2": file_dem_sample,
            "OUTPUT": file_zmin,
        },
    )

    # -- GDAL- compute HAND
    file_hand = "{}/hand.tif".format(output_folder)
    processing.run(
        "gdal:rastercalculator",
        {
            "INPUT_A": file_dem_sample,
            "BAND_A": 1,
            "INPUT_B": file_zmin,
            "BAND_B": 1,
            "INPUT_C": None,
            "BAND_C": None,
            "INPUT_D": None,
            "BAND_D": None,
            "INPUT_E": None,
            "BAND_E": None,
            "INPUT_F": None,
            "BAND_F": None,
            "FORMULA": "A - B",
            "NO_DATA": None,
            "PROJWIN": None,
            "RTYPE": 1,
            "OPTIONS": "",
            "EXTRA": "",
            "OUTPUT": file_hand,
        },
    )
    return {
        "ldd": file_ldd,
        "material": file_material,
        "accflux": file_accflux,
        "threshold": file_threshold,
        "drainage": file_drainage,
        "hs_outlets_scalar": file_outlets_1,
        "hs_outlets_nominal": file_outlets_2,
        "hillslopes": file_hillslopes,
        "hs_zmin": file_zmin,
        "hand": file_hand,
    }

def get_topo(
    output_folder,
    file_main_dem,
    target_crs,
    input_db,
    layer_aoi="aoi",
    layer_rivers="rivers",
    source_crs="4326",
    w=3,
    h=10,
    hand_cells=100,
):
    """Get all ``topo`` datasets for running PLANS.

    :param output_folder: path to output folder to export datasets
    :type output_folder: str
    :param file_main_dem: file path to larger DEM dataset raster -- expected to be in WGS-84
    :type file_main_dem: str
    :param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param input_db: path to geopackage database
    :type input_db: str
    :param layer_aoi: name of Area Of Interest layer (polygon). Default is "aoi"
    :type layer_aoi: str
    :param layer_rivers: name of main rivers layers (lines). Default is "rivers"
    :type layer_rivers: str
    :param source_crs: EPSG code (number only) for the source CRS. default is WGS-84 (4326)
    :type source_crs: str
    :param w: [burning dem parameter] width parameter in unit cells
    :type w: int
    :param h: [burning dem parameter] height parameter in dem units (e.g., meters)
    :type h: float
    :param hand_cells: [hand parameter] threshhold for HAND in number of maximum hillslope cells
    :type hand_cells: int
    :return: None
    :rtype: None

    Script example (for QGIS Python Console):

    .. code-block:: python

        # plans source code must be pasted to QGIS plugins directory
        from plans import iamlazy

        # call function
        iamlazy.get_topo(
            output_folder="path/to/folder",
            file_main_dem="path/to/main_large_dem.tif",
            target_crs="31982",
            input_db="path/to/project_db.gpkg",
            layer_aoi='aoi',
            layer_rivers='rivers',
            source_crs='4326',
            w=3,
            h=10,
            hand_cells=100
        )

    .. warning::

        You must change the path files in the previous example.

    """
    # folders and file setup
    output_folder_interm = "{}/intermediate".format(output_folder)
    if os.path.isdir(output_folder_interm):
        pass
    else:
        os.mkdir(output_folder_interm)

    # GDAL folder
    output_folder_gdal = "{}/gdal".format(output_folder_interm)
    if os.path.isdir(output_folder_gdal):
        pass
    else:
        os.mkdir(output_folder_gdal)

    # SAGA folder
    output_folder_saga = "{}/saga".format(output_folder_interm)
    if os.path.isdir(output_folder_saga):
        pass
    else:
        os.mkdir(output_folder_saga)

    # PCRASTER folder
    output_folder_pcraster = "{}/pcraster".format(output_folder_interm)
    if os.path.isdir(output_folder_pcraster):
        pass
    else:
        os.mkdir(output_folder_pcraster)

    dict_files = {
        "dem": "{}/dem.tif".format(output_folder_gdal),
        "main_rivers": "{}/main_rivers.tif".format(output_folder_gdal),
        "dem_b": "{}/dem_b.tif".format(output_folder_gdal),
        "slope": "{}/slope.tif".format(output_folder_gdal),
        "fill": "{}/fill.sdat".format(output_folder_saga),
        "flowacc_mfd_sg": "{}/flowacc_mfd.sdat".format(output_folder_saga),
        "flowacc_mfd": "{}/flowacc_mfd.tif".format(output_folder_gdal),
        "twi": "{}/twi.tif".format(output_folder_gdal),
        "dem_bf": "{}/dem_bf.tif".format(output_folder_gdal),
        "dem_bfb": "{}/dem_bfb.tif".format(output_folder_gdal),
        "dem_pc": "{}/dem.map".format(output_folder_pcraster),
        "dem_bf_pc": "{}/dem_bf.map".format(output_folder_pcraster),
    }

    #
    print("reproject layers...")
    # reproject aoi
    new_layer_aoi = reproject_layer(
        input_db=input_db, layer_name=layer_aoi, target_crs=target_crs
    )
    # reproject rivers
    new_layer_rivers = reproject_layer(
        input_db=input_db, layer_name=layer_rivers, target_crs=target_crs
    )
    # 2)
    print("get aoi extent...")
    dict_bbox = get_extent_vector(input_db=input_db, layer_name=new_layer_aoi)
    # print(dict_bbox)
    # 3)
    print("clip and warp dem...")
    file_dem = get_dem(
        file_main_dem=file_main_dem,
        target_crs=target_crs,
        target_extent_dict=dict_bbox,
        file_output=dict_files["dem"],
        source_crs=source_crs,
    )
    cellsize = get_cellsize(file_input=dict_files["dem"])
    # get rivers blank
    # 4)
    print("get main rivers...")
    file_rivers = get_blank_raster(
        file_input=file_dem, file_output=dict_files["main_rivers"], blank_value=0
    )
    print("rasterize...")
    # 5) rasterize rivers
    processing.run(
        "gdal:rasterize_over_fixed_value",
        {
            "INPUT": "{}|layername={}".format(input_db, new_layer_rivers),
            "INPUT_RASTER": dict_files["main_rivers"],
            "BURN": 1,
            "ADD": False,
            "EXTRA": "",
        },
    )
    print("burn dem...")
    # 6) get burned
    file_burn = get_carved_dem(
        file_dem=dict_files["dem"],
        file_rivers=dict_files["main_rivers"],
        file_output=dict_files["dem_b"],
        w=w,
        h=h,
    )
    # get slope
    print("get slope....")
    get_slope(file_dem=dict_files["dem"], file_output=dict_files["slope"])

    print("fill sinks...")
    processing.run(
        "saga:fillsinksplanchondarboux2001",
        {"DEM": dict_files["dem_b"], "RESULT": dict_files["fill"], "MINSLOPE": 0.01},
    )
    print("translate fill...")
    processing.run(
        "gdal:translate",
        {
            "INPUT": dict_files["fill"],
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "NODATA": None,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 6,
            "OUTPUT": dict_files["dem_bf"],
        },
    )
    print("get flowacc mfd ...")
    processing.run(
        "saga:flowaccumulationparallelizable",
        {
            "DEM": dict_files["dem_bf"],
            "FLOW": dict_files["flowacc_mfd_sg"],
            "UPDATE": 0,
            "METHOD": 2,
            "CONVERGENCE": 1.1,
        },
    )
    print("translate flowacc mfd...")
    processing.run(
        "gdal:translate",
        {
            "INPUT": dict_files["flowacc_mfd_sg"],
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "NODATA": None,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 6,
            "OUTPUT": dict_files["flowacc_mfd"],
        },
    )
    print("get TWI...")
    get_twi(
        file_slope=dict_files["slope"],
        file_flowacc=dict_files["flowacc_mfd"],
        file_output=dict_files["twi"],
    )
    print("convert dem to pcraster...")
    processing.run(
        "pcraster:converttopcrasterformat",
        {"INPUT": dict_files["dem"], "INPUT2": 3, "OUTPUT": dict_files["dem_pc"]},
    )
    print("convert dem_bf to pcraster...")
    processing.run(
        "pcraster:converttopcrasterformat",
        {"INPUT": dict_files["dem_bf"], "INPUT2": 3, "OUTPUT": dict_files["dem_bf_pc"]},
    )

    print("get HAND...")
    dict_hand = get_hand(
        file_dem_filled=dict_files["dem_bf_pc"],
        output_folder=output_folder_pcraster,
        hand_cells=hand_cells,
        file_dem_sample=dict_files["dem_pc"],
    )
    # append to dict
    for f in dict_hand:
        dict_files[f] = dict_hand[f]

    # translate all
    dict_raster = {"nodata": -1, "data_type": 6}
    dict_qualiraster = {"nodata": 0, "data_type": 1}
    dict_translate = {
        "dem": dict_raster,
        "slope": dict_raster,
        "twi": dict_raster,
        "accflux": dict_raster,
        "hand": dict_raster,
        "ldd": dict_qualiraster,
    }
    # loop
    print("translating outputs...")
    for k in dict_translate:
        processing.run(
            "gdal:translate",
            {
                "INPUT": dict_files[k],
                "TARGET_CRS": QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(target_crs)
                ),
                "NODATA": dict_translate[k]["nodata"],
                "COPY_SUBDATASETS": False,
                "OPTIONS": "",
                "EXTRA": "",
                "DATA_TYPE": dict_translate[k]["data_type"],
                "OUTPUT": "{}/{}.asc".format(output_folder, k),
            },
        )

    return None


def get_lulc(
    list_main_files,
    list_dates,
    output_folder,
    target_file,
    target_crs,
    input_db=None,
    layer_roads_dirty="roads_dirty",
    layer_roads_paved="roads_paved",
    source_crs="4326",
    qml_file=None,
):
    """Get LULC maps from a larger main LULC dataset.

    :param list_main_files: list of file paths to main lulc rasters
    :type list_main_files: list
    :param list_dates: list of dates (YYYY-MM-DD) for each main raster
    :type list_dates: list
    :param output_folder: path to output folder
    :type output_folder: str
    :param target_file: file path to target raster (e.g., the DEM raster)
    :type target_file: str
    :param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param input_db: [optional] path to geopackage database with road layers
    :type input_db: str
    :param layer_roads_dirty: layer name of dirty roads
    :type layer_roads_dirty: str
    :param layer_roads_paved: layer name of paved roads
    :type layer_roads_paved: str
    :param source_crs: EPSG code (number only) for the source CRS. default is WGS-84 (4326)
    :type source_crs: str
    :param qml_file: [optional] file path to QML style file
    :type qml_file: str
    :return: None
    :rtype: None

    Script example (for QGIS):

    .. code-block:: python

        # plans source code must be pasted to QGIS plugins directory
        from plans import iamlazy
        # set files
        lst_files = [
            "path/to/lulc_2015.tif",
            "path/to/lulc_2015.tif",
            "path/to/lulc_2016.tif",
        ]
        # set dates
        lst_dates = [
            "2014-01-01",
            "2015-01-01",
            "2016-01-01",
        ]
        # run function
        iamlazy.get_lulc(
            list_main_files=lst_files,
            list_dates=lst_dates,
            output_folder="path/to/output",
            target_file="/path/to/raster.tif",
            target_crs="31982",
            input_db="path/to/input_db.gpkg",
            layer_roads_dirty='roads_dirty',
            layer_roads_paved='roads_paved',
            source_crs='4326',
            qml_file="path/to/style.qml"
        )

    """
    # folders and file setup
    output_folder_interm = "{}/intermediate".format(output_folder)
    if os.path.isdir(output_folder_interm):
        pass
    else:
        os.mkdir(output_folder_interm)
    # ---------- warp lulc -----------
    target_extent_dict = get_extent_raster(file_input=target_file)
    # get extent string
    target_extent_str = "{},{},{},{} [EPSG:{}]".format(
        target_extent_dict["xmin"],
        target_extent_dict["xmax"],
        target_extent_dict["ymin"],
        target_extent_dict["ymax"],
        target_crs,
    )
    cellsize = get_cellsize(file_input=target_file)
    list_output_files = list()
    list_filenames = list()
    print("clip and warp lulc ... ")
    for i in range(len(list_main_files)):
        file_main_lulc = list_main_files[i]
        date = list_dates[i]
        str_filename = "lulc_{}".format(date)
        file_output = "{}/{}.tif".format(output_folder_interm, str_filename)
        list_output_files.append(file_output[:])
        list_filenames.append(str_filename[:])
        # run warp
        processing.run(
            "gdal:warpreproject",
            {
                "INPUT": file_main_lulc,
                "SOURCE_CRS": QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(source_crs)
                ),
                "TARGET_CRS": QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(target_crs)
                ),
                "RESAMPLING": 0,
                "NODATA": 0,
                "TARGET_RESOLUTION": cellsize,
                "OPTIONS": "",
                "DATA_TYPE": 1,
                "TARGET_EXTENT": target_extent_str,
                "TARGET_EXTENT_CRS": QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(target_crs)
                ),
                "MULTITHREADING": False,
                "EXTRA": "",
                "OUTPUT": file_output,
            },
        )

    #
    # ---------- handle roads -----------
    if input_db is None:
        pass
    else:
        print("reproject road layers...")
        # reproject dirty
        new_layer_dirty = reproject_layer(
            input_db=input_db, layer_name=layer_roads_dirty, target_crs=target_crs
        )
        # reproject paved
        new_layer_paved = reproject_layer(
            input_db=input_db, layer_name=layer_roads_paved, target_crs=target_crs
        )

        # rasterize loop
        print("rasterizing road layers...")
        for i in range(len(list_output_files)):
            input_raster = list_output_files[i]
            # dirty
            processing.run(
                "gdal:rasterize_over_fixed_value",
                {
                    "INPUT": "{}|layername={}".format(input_db, new_layer_dirty),
                    "INPUT_RASTER": input_raster,
                    "BURN": 255,
                    "ADD": False,
                    "EXTRA": "",
                },
            )
            # paved
            processing.run(
                "gdal:rasterize_over_fixed_value",
                {
                    "INPUT": "{}|layername={}".format(input_db, new_layer_paved),
                    "INPUT_RASTER": input_raster,
                    "BURN": 254,
                    "ADD": False,
                    "EXTRA": "",
                },
            )
    # ---------- translate all -----------
    print("translate...")
    for i in range(len(list_output_files)):
        input_file = list_output_files[i]
        filename = list_filenames[i]
        processing.run(
            "gdal:translate",
            {
                "INPUT": input_file,
                "TARGET_CRS": QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(target_crs)
                ),
                "NODATA": 0,
                "COPY_SUBDATASETS": False,
                "OPTIONS": "",
                "EXTRA": "",
                "DATA_TYPE": 1,
                "OUTPUT": "{}/{}.asc".format(output_folder, filename),
            },
        )
        # Handle style
        if qml_file is None:
            pass
        else:
            shutil.copy(src=qml_file, dst="{}/{}.qml".format(output_folder, filename))

    return None


def get_rain(
    output_folder,
    input_db,
    target_file,
    target_crs,
    layer_aoi="aoi",
    layer_rain_gauges="rain",
):
    """Get [rain] datasets for running PLANS.

    ::param output_folder: path to output folder
    :type output_folder: str
    :param input_db: path to geopackage database with rain gauge layer
    :type input_db: str
    :param target_file: file path to target raster (e.g., the DEM raster)
    :type target_file: str
    ::param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param layer_aoi: name of Area Of Interest layer (polygon). Default is "aoi"
    :type layer_aoi: str
    :param layer_rain_gauges: layer name of rain gauges layer
    :type layer_rain_gauges: str
    :return: None
    :rtype: None

    Script example (for QGIS Python Console):

    .. code-block:: python

        # plans source code must be pasted to QGIS plugins directory
        from plans import iamlazy

        # call function
        iamlazy.get_rain(
            output_folder="path/to/rain",
            target_file="path/to/dem.asc",
            target_crs="31982",
            input_db="path/to/my_db.gpkg",
            layer_aoi="aoi",
            layer_rain_gauges="rain"
        )

    """
    def calculate_buffer_ratios(box_small, box_large):
        delta_x_small = abs(box_small["xmax"] - box_small["xmin"])
        lower_x = abs(box_small["xmin"] - box_large["xmin"])
        upper_x = abs(box_small["xmax"] - box_large["xmax"])
        x_ratio = max(lower_x / delta_x_small, upper_x / delta_x_small)

        delta_y_small = abs(box_small["ymax"] - box_small["ymin"])
        lower_y = abs(box_small["ymin"] - box_large["ymin"])
        upper_y = abs(box_small["ymax"] - box_large["ymax"])
        y_ratio = max(lower_y / delta_y_small, upper_y / delta_y_small)

        return (x_ratio, y_ratio)

    print("folder setup...")
    # folders and file setup
    output_folder_interm = "{}/intermediate".format(output_folder)
    if os.path.isdir(output_folder_interm):
        pass
    else:
        os.mkdir(output_folder_interm)

    print("get info...")
    # load table
    rain_gdf = gpd.read_file(input_db, layer=layer_rain_gauges, ignore_geometry=True)
    # export csv file
    rain_gdf.to_csv("{}/rain_info.csv".format(output_folder), sep=";", index=False)
    # print(rain_gdf.to_string())

    # first check number of features
    n_rain_gauges = get_feature_count(input_db=input_db, layer_name=layer_rain_gauges)
    dict_blank = {"constant": 0, "voronoi": 0}
    s_type = "voronoi"
    if n_rain_gauges < 2:
        print(" -- only one rain gauge found")
        s_type = "constant"
        # create constant raster layer based on target and Id

        # >> find rain id
        n_id = rain_gdf["Id"].values[0]
        # update dict
        dict_blank["constant"] = n_id
    else:
        # get voronoi zones

        # first validade extents
        dict_extent_aoi = get_extent_vector(input_db=input_db, layer_name=layer_aoi)
        dict_extent_rain = get_extent_vector(
            input_db=input_db, layer_name=layer_rain_gauges
        )

        # check is is bounded:
        if is_bounded_by(extent_a=dict_extent_rain, extent_b=dict_extent_aoi):
            n_buffer = 20
        else:
            n_buffer = (
                100
                * 1.2
                * max(
                    calculate_buffer_ratios(
                        box_small=dict_extent_rain, box_large=dict_extent_aoi
                    )
                )
            )

        # reproject rain
        layer_rain_gauges_2 = reproject_layer(
            input_db=input_db, layer_name=layer_rain_gauges, target_crs=target_crs
        )
        print("get voronoi polygons...")
        # run function
        processing.run(
            "qgis:voronoipolygons",
            {
                "INPUT": "{}|layername={}".format(input_db, layer_rain_gauges_2),
                "BUFFER": n_buffer,
                "OUTPUT": "{}/zones.shp".format(output_folder_interm),
            },
        )
    print("get zones raster...")
    zones_raster = "{}/zones.tif".format(output_folder_interm)
    # >> create constant raster layer
    get_blank_raster(
        file_input=target_file, file_output=zones_raster, blank_value=dict_blank[s_type]
    )
    # rasterize target raster
    if s_type == "voronoi":
        # rasterize voronoi
        processing.run(
            "gdal:rasterize_over",
            {
                "INPUT": "{}/zones.shp".format(output_folder_interm),
                "INPUT_RASTER": "{}/rain_zones.tif".format(output_folder_interm),
                "FIELD": "Id",
                "ADD": False,
                "EXTRA": "",
            },
        )
    print("translate...")
    # translante raster layer
    processing.run(
        "gdal:translate",
        {
            "INPUT": "{}/rain_zones.tif".format(output_folder_interm),
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "NODATA": 0,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 1,
            "OUTPUT": "{}/rain_zones.asc".format(output_folder),
        },
    )
    print("end")
    return None


def get_basins(
    output_folder,
    input_db,
    ldd_file,
    target_crs,
    layer_stream_gauges="stream",
):
    """Get all ``basins`` datasets for running PLANS.

    :param output_folder: path to output folder
    :type output_folder: str
    :param input_db: path to geopackage database with streamflow gauges layer
    :type input_db: str
    :param ldd_file: file path to LDD raster
    :type ldd_file: str
    :param target_crs: EPSG code (number only) for the target CRS
    :type target_crs: str
    :param layer_stream_gauges: layer name of streamflow gauges layer
    :type layer_stream_gauges: str
    :return: None
    :rtype: None

    Script example (for QGIS Python Console):

    .. code-block:: python

        # plans source code must be pasted to QGIS plugins directory
        from plans import iamlazy

        # call function
        iamlazy.get_basins(
            output_folder="path/to/basins",
            ldd_file="path/to/ldd.asc",
            target_crs="31982",
            input_db="path/to/my_db.gpkg",
            layer_stream_gauges="stream"
        )

    """
    print("folder setup...")
    # folders and file setup
    output_folder_interm = "{}/intermediate".format(output_folder)
    if os.path.isdir(output_folder_interm):
        pass
    else:
        os.mkdir(output_folder_interm)

    # GDAL folder
    output_folder_gdal = "{}/gdal".format(output_folder_interm)
    if os.path.isdir(output_folder_gdal):
        pass
    else:
        os.mkdir(output_folder_gdal)

    # PCRASTER folder
    output_folder_pcraster = "{}/pcraster".format(output_folder_interm)
    if os.path.isdir(output_folder_pcraster):
        pass
    else:
        os.mkdir(output_folder_pcraster)
    print("reproject...")
    # reproject streams
    layer_stream_gauges_new = reproject_layer(
        input_db=input_db, target_crs=target_crs, layer_name=layer_stream_gauges
    )
    print("blank raster...")
    gauge_raster = "{}/gauges.tif".format(output_folder_gdal)
    # get blanks
    get_blank_raster(file_input=ldd_file, file_output=gauge_raster, blank_value=0)
    print("rasterize...")
    # rasterize
    processing.run(
        "gdal:rasterize_over",
        {
            "INPUT": "{}|layername={}".format(input_db, layer_stream_gauges_new),
            "INPUT_RASTER": gauge_raster,
            "FIELD": "Id",
            "ADD": False,
            "EXTRA": "",
        },
    )
    # todo validate gauge positions

    # convert to pc raster
    print("get outlets...")
    outlets_raster_pc = "{}/outlets.map".format(output_folder_pcraster)
    processing.run(
        "pcraster:converttopcrasterformat",
        {"INPUT": gauge_raster, "INPUT2": 1, "OUTPUT": outlets_raster_pc},
    )
    # convert ldd
    print("get ldd...")
    ldd_file_pc = "{}/ldd.map".format(output_folder_pcraster)
    processing.run(
        "pcraster:converttopcrasterformat",
        {"INPUT": ldd_file, "INPUT2": 5, "OUTPUT": ldd_file_pc},
    )
    # get basins
    basins_file_pc = "{}/basins.map".format(output_folder_pcraster)
    print("get basins...")
    processing.run(
        "pcraster:subcatchment",
        {"INPUT1": ldd_file_pc, "INPUT2": outlets_raster_pc, "OUTPUT": basins_file_pc},
    )
    # translante raster layers
    outlets_raster = "{}/outlets.asc".format(output_folder)
    processing.run(
        "gdal:translate",
        {
            "INPUT": outlets_raster_pc,
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "NODATA": 0,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 1,
            "OUTPUT": outlets_raster,
        },
    )
    basins_raster = "{}/basins.asc".format(output_folder)
    processing.run(
        "gdal:translate",
        {
            "INPUT": basins_file_pc,
            "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:{}".format(target_crs)),
            "NODATA": 0,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 1,
            "OUTPUT": basins_raster,
        },
    )
    # load table
    basins_gdf = gpd.read_file(
        input_db, layer=layer_stream_gauges, ignore_geometry=True
    )
    print("compute basin topology")

    dict_aux = get_downstream_ids(
        file_ldd=ldd_file, file_basins=basins_raster, file_outlets=outlets_raster
    )

    aux_gdf = gpd.GeoDataFrame.from_dict(dict_aux, geometry=None)
    merged_gdf = basins_gdf.merge(aux_gdf, on="Id")
    # export csv file
    merged_gdf.to_csv("{}/basins_info.csv".format(output_folder), sep=";", index=False)

    print("end")
    return None
