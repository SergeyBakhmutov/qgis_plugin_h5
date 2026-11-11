from osgeo import gdal


def read_tiff(path):
    """Return information about a TIFF file at the given path"""
    ds = gdal.Open(path)
    band = ds.GetRasterBand(1)
    info = {
        'width': ds.RasterXSize,
        'height': ds.RasterYSize,
        'band_count': ds.RasterCount,
        'geotransform': ds.GetGeoTransform(),
        'srs': ds.GetSpatialRef(),
        'nodata': band.GetNoDataValue(),
        'description': band.GetDescription(), #TODO: delete warning 1
        'data': band.ReadAsArray(),
    }
    ds = None
    return info
