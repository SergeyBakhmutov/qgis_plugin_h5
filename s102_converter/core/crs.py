import math

from osgeo import osr

# UPS with (N,E) axes; Table 5-1 lists the same CRS only as (E,N)
UPS_EN = {32661: 5041, 32761: 5042}
# max shift of grid points from the EPSG definition, about 1 mm
TOLERANCE_M = 1e-3
TOLERANCE_DEG = 1e-8


def is_allowed_epsg(code):
    """Return True if the EPSG code is permitted by S-102 Table 5-1"""
    if code is None:
        return False
    return (
            code in (4326, 5041, 5042)
            or (32601 <= code <= 32660)
            or (32701 <= code <= 32760))


def grid_points(geotransform, width, height):
    """Return corners, edge midpoints and centre of the grid"""
    x0, dx, _, y0, _, dy = geotransform
    return [(x0 + i * width * dx, y0 + j * height * dy)
            for i in (0, 0.5, 1) for j in (0, 0.5, 1)]


def max_shift(srs, code, points):
    """Return the largest shift of points moved from srs to the EPSG CRS"""
    source = srs.Clone()
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    target.ImportFromEPSG(code)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    try:
        transform = osr.CoordinateTransformation(source, target)
    except RuntimeError:
        return math.inf
    return max(math.dist(transform.TransformPoint(x, y)[:2], (x, y)) for x, y in points)


def find_epsg(srs, points):
    """Return the EPSG code permitted by S-102 Table 5-1 and warnings"""
    if srs is None:
        raise ValueError('В файле не задана система координат')

    if srs.GetAuthorityName(None) == 'EPSG':
        code = int(srs.GetAuthorityCode(None))
        code = UPS_EN.get(code, code)
        if not is_allowed_epsg(code):
            raise ValueError(f'EPSG:{code} ({srs.GetName()}) не разрешён в S-102 (табл. 5-1)')
        return code, []

    # no EPSG code in the file: match by definition
    codes = set()
    for candidate, _ in srs.FindMatches():
        if candidate.GetAuthorityName(None) != 'EPSG':
            continue
        code = int(candidate.GetAuthorityCode(None))
        code = UPS_EN.get(code, code)
        if is_allowed_epsg(code):
            codes.add(code)
    if not codes:
        raise ValueError(f'Система координат {srs.GetName()!r} не разрешена в S-102 (табл. 5-1)')

    # no user defined CRS in S-102 (Table 10-2, Note 2), so require equivalence
    shifts = {code: max_shift(srs, code, points) for code in codes}
    matched = [code for code, shift in shifts.items()
               if shift <= (TOLERANCE_DEG if code == 4326 else TOLERANCE_M)]
    if len(matched) > 1:
        raise ValueError(f'Не удалось однозначно определить EPSG, кандидаты: {sorted(matched)}')
    if not matched:
        code, shift = min(shifts.items(), key=lambda item: item[1])
        unit = '°' if code == 4326 else ' м'
        raise ValueError(f'Система координат похожа на EPSG:{code}, '
                         f'но расходится с ним на {shift:.3f}{unit}')

    code = matched[0]
    warnings = []
    datum = srs.GetAttrValue('DATUM') or ''
    if datum.lower().startswith('unknown'):
        warnings.append(f'Датум не указан, принят WGS 84 (EPSG:{code})')
    return code, warnings
