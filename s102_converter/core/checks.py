import os

from .prepare import mask_nodata

MAX_FILE_SIZE = 10 * 2**20


def check_input(info):
    """Return a dict of errors and warnings if the file is not suitable for conversion"""
    errors = []
    warnings = []
    valid_count = mask_nodata(info['data'], info['nodata']).count()
    # depth only, uncertainty is optional (S-102 4.4.2.1)
    if info['band_count'] != 1:
        errors.append(f'Каналов {info["band_count"]}, а нужен 1 (глубина). '
                      'Неопределённость не поддерживается')
    if (info['geotransform'][2]) != 0.0 or info['geotransform'][4] != 0:
        errors.append(
            f'Сетка повёрнута. S-102 требует регулярную сетку')  # 4.4.2.1, стр. 17
    if valid_count == 0:
        errors.append('В файле нет данных, все ячейки пустые')
    if info['nodata'] is None:
        warnings.append('Значение nodata не задано. Возможно, в файле нет пустых ячеек.')
    return errors, warnings


def check_output(path):
    """Return errors and warnings for the written S-102 file"""
    warnings = []
    size = os.path.getsize(path)
    # informative limit (S-102 11.2.2, S-158 102_9004), binary prefix (S-100 Part 11)
    if size > MAX_FILE_SIZE:
        warnings.append(f'Размер файла {size / 2**20:.1f} МиБ превышает 10 МиБ')
    return [], warnings
