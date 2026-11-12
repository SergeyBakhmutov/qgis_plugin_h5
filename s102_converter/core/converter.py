import os

from osgeo import gdal, osr

from .checks import check_input, check_output
from .config import check_settings
from .crs import find_epsg, grid_points
from .prepare import decide_flip, prepare_depths
from .reader import read_tiff
from .writer import make_dataset, write_s102
from .xyz import load_xyz


def tiff_grid(info):
    """Return the grid of a checked GeoTIFF with its EPSG code"""
    points = grid_points(info['geotransform'], info['width'], info['height'])
    epsg, warnings = find_epsg(info['srs'], points)
    return {'data': info['data'], 'nodata': info['nodata'],
            'geotransform': info['geotransform'], 'epsg': epsg,
            'warnings': warnings, 'note': ''}


def convert(input_path, settings, output_dir, settings_name='настройки'):
    """Check settings and input, write S-102 and check the written file.

    Return a summary line (None on failure) and a list of
    (source, errors, warnings) records in the order of checks.
    """
    # exceptions for this thread and this call only, see core/__init__.py
    with gdal.ExceptionMgr(), osr.ExceptionMgr():
        return _convert(input_path, settings, output_dir, settings_name)


def _convert(input_path, settings, output_dir, settings_name):
    log = []
    gdal_warnings = []

    def stage(source, errors, warnings):
        log.append((source, errors, warnings))
        return not errors

    def on_gdal_message(level, code, message):
        if level == gdal.CE_Warning:
            gdal_warnings.append(message)

    # GDAL warnings are part of the report (e.g. depth range from the driver)
    gdal.PushErrorHandler(on_gdal_message)
    try:
        if not stage(settings_name, *check_settings(settings)):
            return None, log
        if not os.path.exists(input_path):
            stage(input_path, ['файл не найден'], [])
            return None, log

        try:
            if 'xyz' in settings:
                # XYZ holds points only, the grid comes from the settings
                grid = load_xyz(input_path, settings['xyz'])
            else:
                info = read_tiff(input_path)
                if not stage(input_path, *check_input(info)):
                    return None, log
                grid = tiff_grid(info)
            flip = decide_flip(grid['data'], grid['nodata'], settings['input_values'])
        except ValueError as e:
            stage(input_path, [str(e)], [])
            return None, log
        stage(input_path, [], grid['warnings'])

        epsg = grid['epsg']
        depths = prepare_depths(grid['data'], grid['nodata'], flip_sign=flip)
        ds = make_dataset(depths, grid['geotransform'], epsg)
        os.makedirs(output_dir, exist_ok=True)
        path = write_s102(ds, settings, output_dir)

        ok = stage(path, *check_output(path))
    finally:
        gdal.PopErrorHandler()
        if gdal_warnings:
            log.insert(0, ('GDAL', [], gdal_warnings))

    if not ok:
        return None, log
    sign = 'инвертирован' if flip else 'без изменений'
    note = f', {grid['note']}' if grid['note'] else ''
    return f'Записан {path} (EPSG:{epsg}, знак {sign}{note})', log
