import os
from osgeo import gdal, osr
from .prepare import FILL_VALUE

QUALITY_DIR = '/vsimem/s102conv'
QUALITY_PATH = f'{QUALITY_DIR}/quality.tif'
# driver casts columns to Table 10-8 types by name
RAT_TYPES = {int: gdal.GFT_Integer, float: gdal.GFT_Real, str: gdal.GFT_String}


def make_dataset(depths, geotransform, epsg):
    height, width = depths.shape

    driver = gdal.GetDriverByName('MEM')
    ds = driver.Create('', width, height, 1, gdal.GDT_Float32)
    ds.SetGeoTransform(geotransform)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    # geotransform is x = lon/easting; EPSG:4326 itself is lat, lon
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetSpatialRef(srs)

    band = ds.GetRasterBand(1)
    band.WriteArray(depths)
    band.SetNoDataValue(FILL_VALUE)
    band.SetDescription('depth')

    return ds


def make_creation_options(settings):
    options = [
        f'VERTICAL_DATUM={settings["vertical_datum"]}',
        f'ISSUE_DATE={settings["issue_date"]}',
        f'HORIZONTAL_POSITION_UNCERTAINTY={settings["horizontal_position_uncertainty"]}',
        f'VERTICAL_UNCERTAINTY={settings["vertical_uncertainty"]}',
    ]
    if 'issue_time' in settings:
        options.append(f'ISSUE_TIME={settings["issue_time"]}')
    return options


def make_filename(settings):
    return f'102{settings["producer_code"]}{settings["dataset_name"]}.H5'


def make_quality_dataset(ds, quality):
    """Write a quality raster with a single attribute record (S-102 10.2.8-10.2.11)"""
    ids = (ds.GetRasterBand(1).ReadAsArray() != FILL_VALUE).astype('uint32')

    qds = gdal.GetDriverByName('GTiff').Create(
        QUALITY_PATH, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_UInt32)
    qds.SetGeoTransform(ds.GetGeoTransform())
    qds.SetSpatialRef(ds.GetSpatialRef())
    band = qds.GetRasterBand(1)
    # record id 1 where depth exists, fill value 0 elsewhere (S-102 10.2.11)
    band.WriteArray(ids)

    fields = {'id': 1, **quality}
    rat = gdal.RasterAttributeTable()
    for name, value in fields.items():
        rat.CreateColumn(name, RAT_TYPES[type(value)], gdal.GFU_Generic)
    rat.SetRowCount(1)
    setters = {int: rat.SetValueAsInt, float: rat.SetValueAsDouble, str: rat.SetValueAsString}
    for col, value in enumerate(fields.values()):
        setters[type(value)](0, col, value)
    band.SetDefaultRAT(rat)

    qds = None
    return QUALITY_PATH


def write_s102(ds, settings, output_dir='output'):
    path = os.path.join(output_dir, make_filename(settings))
    options = make_creation_options(settings)
    quality_path = None
    # quality coverage is optional, multiplicity 0..1 (S-102 10.2.8)
    if settings['quality']:
        quality_path = make_quality_dataset(ds, settings['quality'])
        options.append(f'QUALITY_DATASET={quality_path}')
    try:
        gdal.Translate(path, ds, format='S102', creationOptions=options)
    finally:
        if quality_path:
            gdal.RmdirRecursive(QUALITY_DIR)
    return path
