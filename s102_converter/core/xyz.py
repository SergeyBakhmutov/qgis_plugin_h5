import re

import numpy as np
from osgeo import osr

osr.UseExceptions()

SEPARATOR_RE = re.compile(r'[,;\s]+')
# the whole bounding grid is kept in memory, longer strips need tiling
MAX_CELLS = 50_000_000


def read_xyz(path, columns):
    """Return lon, lat, z arrays and source line numbers of the points"""
    rows = []
    lines = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for number, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                values = [float(v) for v in SEPARATOR_RE.split(text)]
            except ValueError:
                # header lines before the data are skipped
                if not rows:
                    continue
                raise ValueError(f'Строка {number}: не числа: {text[:60]!r}')
            if len(values) != 3:
                raise ValueError(
                    f'Строка {number}: колонок {len(values)}, а нужно 3 (координаты и глубина)')
            rows.append(values)
            lines.append(number)
    if not rows:
        raise ValueError('В файле нет строк с данными')

    data = np.array(rows)
    lines = np.array(lines)
    if columns == 'lat_lon':
        lat, lon = data[:, 0], data[:, 1]
    else:
        lon, lat = data[:, 0], data[:, 1]

    bad = np.flatnonzero(~np.isfinite(data).all(axis=1))
    if bad.size:
        raise ValueError(f'Строка {lines[bad[0]]}: значение не является числом')
    for values, name, limit in ((lat, 'широта', 90), (lon, 'долгота', 180)):
        bad = np.flatnonzero(np.abs(values) > limit)
        if bad.size:
            raise ValueError(
                f'Строка {lines[bad[0]]}: {name} {values[bad[0]]} вне ±{limit}°. '
                'Проверьте порядок колонок')
    return lon, lat, data[:, 2], lines


def project(lon, lat, epsg):
    """Return x, y of WGS 84 points in the grid CRS"""
    if epsg == 4326:
        return lon, lat
    src = osr.SpatialReference()
    src.ImportFromEPSG(4326)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(epsg)
    for srs in (src, dst):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(src, dst)
    xy = np.array(ct.TransformPoints(np.column_stack((lon, lat))))
    return xy[:, 0], xy[:, 1]


def make_grid(x, y, z, lines, step_x, step_y, tolerance, unit):
    """Place points into cells of a regular grid.

    Return the depth array (NaN in empty cells), the geotransform
    and the largest offset of a point from its node.
    """
    # grid position is not stored in XYZ: node numbers are counted from
    # the first point, the node position is the mean over all points,
    # so rounding of single coordinates cancels out
    col = np.rint((x - x[0]) / step_x)
    row = np.rint((y - y[0]) / step_y)
    x0 = np.mean(x - col * step_x)
    y0 = np.mean(y - row * step_y)
    offset = np.maximum(np.abs(x - x0 - col * step_x), np.abs(y - y0 - row * step_y))

    far = np.flatnonzero(offset > tolerance)
    if far.size:
        worst = far[np.argmax(offset[far])]
        raise ValueError(
            f'Точки не образуют регулярную сетку с шагом {step_x:g}×{step_y:g}{unit}: '
            f'{far.size} из {x.size} дальше {tolerance:g}{unit} от узлов, '
            f'наибольшее отклонение {offset[worst]:.3g}{unit} (строка {lines[worst]}). '
            'Проверьте порядок колонок, систему координат сетки и шаг')

    col = col.astype(np.int64)
    row = row.astype(np.int64)
    col_min = col.min()
    row_max = row.max()
    col -= col_min
    # north-up: the first row is the northernmost
    row = row_max - row
    width = int(col.max()) + 1
    height = int(row.max()) + 1
    if width * height > MAX_CELLS:
        raise ValueError(
            f'Сетка {width}×{height} = {width * height} ячеек больше предела {MAX_CELLS}. '
            'Разбиение на листы пока не поддерживается')

    # one value per cell (S-102 4.4.2.1), choosing between points is processing
    index = row * width + col
    cells, counts = np.unique(index, return_counts=True)
    if (counts > 1).any():
        first, second = lines[index == cells[counts > 1][0]][:2]
        raise ValueError(
            f'Ячеек с несколькими точками: {np.count_nonzero(counts > 1)}, '
            f'например строки {first} и {second}')

    data = np.full((height, width), np.nan)
    data[row, col] = z
    # geotransform points to the outer corner of the north-west cell
    left = x0 + col_min * step_x - step_x / 2
    top = y0 + row_max * step_y + step_y / 2
    geotransform = (left, step_x, 0.0, top, 0.0, -step_y)
    return data, geotransform, float(offset.max())


def load_xyz(path, xyz):
    """Read an XYZ file and grid it with the settings of the xyz section"""
    epsg = xyz['grid_epsg']
    unit = '°' if epsg == 4326 else ' м'
    lon, lat, z, lines = read_xyz(path, xyz['columns'])
    x, y = project(lon, lat, epsg)
    data, geotransform, offset = make_grid(
        x, y, z, lines, xyz['step_x'], xyz['step_y'], xyz['tolerance'], unit)
    height, width = data.shape
    note = (f'{z.size} точек в сетке {width}×{height}, '
            f'отклонение от узлов до {offset:.3g}{unit}')
    return {'data': data, 'nodata': None, 'geotransform': geotransform,
            'epsg': epsg, 'warnings': [], 'note': note}
