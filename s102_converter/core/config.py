import calendar
import yaml
import re
from datetime import date, datetime

from .crs import is_allowed_epsg

PRODUCER_CODE_RE = r'[A-Z0-9]{4}'
DATASET_NAME_RE = r'[A-Z0-9_]{1,12}'
ISSUE_TIME_RE = r'(?:[01]\d|2[0-3])[0-5]\d[0-5]\dZ'  # UTC only (S-102 5.4)
KNOWN_KEYS = (
    'input_values', 'units', 'vertical_datum', 'issue_date', 'issue_time',
    'horizontal_position_uncertainty', 'vertical_uncertainty',
    'producer_code', 'dataset_name', 'quality', 'xyz',
)
# grid of XYZ points: coordinates are WGS 84 in the given column order,
# the grid CRS is one of S-102 Table 5-1, steps and tolerance in its units
XYZ_KEYS = ('columns', 'grid_epsg', 'step_x', 'step_y', 'tolerance')
XYZ_COLUMNS = ('lat_lon', 'lon_lat')

# featureAttributeTable fields (S-102 Table 10-8); tuples are allowed codes,
# booleans are 0/1 (S-100 Part 10c Table 10c-1)
QUALITY_FIELDS = {
    'dataAssessment': (1, 2, 3),
    'featuresDetected.leastDepthOfDetectedFeaturesMeasured': (0, 1),
    'featuresDetected.significantFeaturesDetected': (0, 1),
    'featuresDetected.sizeOfFeaturesDetected': 'real',
    'featureSizeVar': 'real',
    'fullSeafloorCoverageAchieved': (0, 1),
    'bathyCoverage': (0, 1),
    'zoneOfConfidence.horizontalPositionUncertainty.uncertaintyFixed': 'real',
    'zoneOfConfidence.horizontalPositionUncertainty.uncertaintyVariableFactor': 'real',
    'surveyDateRange.dateStart': 'date',
    'surveyDateRange.dateEnd': 'date',
    'sourceSurveyID': 'text',
    'surveyAuthority': 'text',
    'typeOfBathymetricEstimationUncertainty': (1, 2, 3, 4),  # Table 10-9
}
# S100_TruncatedDate: YYYYMMDD, omitted parts as hyphens (S-100 Part 1 Table 1-2)
TRUNCATED_DATE_RE = r'(\d{4}|----)(\d{2}|--)(\d{2}|--)'


def read_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def format_date(value):
    """Convert YAML date or int to a YYYYMMDD string"""
    if isinstance(value, date):
        return value.strftime('%Y%m%d')
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


def normalize_quality(quality):
    """Cast YAML values to the types expected in the attribute table"""
    if not isinstance(quality, dict):
        return quality
    result = {}
    for key, value in quality.items():
        kind = QUALITY_FIELDS.get(key)
        if kind == 'date':
            value = format_date(value)
        elif kind == 'real' and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        elif isinstance(kind, tuple) and isinstance(value, bool):
            value = int(value)
        result[key] = value
    return result


def normalize_xyz(xyz):
    if not isinstance(xyz, dict):
        return xyz
    result = dict(xyz)
    result.setdefault('columns', 'lat_lon')
    if 'step_y' not in result and 'step_x' in result:
        result['step_y'] = result['step_x']
    for key in ('step_x', 'step_y', 'tolerance'):
        value = result.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            result[key] = float(value)
    return result


def apply_defaults(raw):
    settings = dict(raw)

    settings['input_values'] = settings.get('input_values', 'auto')
    settings['units'] = settings.get('units', 'metres')

    settings['issue_date'] = format_date(settings.get('issue_date', date.today()))

    settings['horizontal_position_uncertainty'] = float(settings.get('horizontal_position_uncertainty', -1))
    settings['vertical_uncertainty'] = float(settings.get('vertical_uncertainty', -1))

    settings['quality'] = normalize_quality(settings.get('quality') or {})
    if 'xyz' in settings:
        settings['xyz'] = normalize_xyz(settings['xyz'])

    return settings


def check_truncated_date(value):
    """Return an error text or None for an S100_TruncatedDate string"""
    match = re.fullmatch(TRUNCATED_DATE_RE, value) if isinstance(value, str) else None
    if not match or value == '--------':
        return 'нужно ГГГГММДД, неизвестные части заменяются дефисами (например 2020----)'
    year, month, day = (None if '-' in part else int(part) for part in match.groups())
    if month is not None and not 1 <= month <= 12:
        return 'месяц должен быть 01–12'
    if day is not None:
        # leap year when the year is omitted, so 29 February stays valid
        last_day = calendar.monthrange(year or 2000, month or 1)[1] if month else 31
        if not 1 <= day <= last_day:
            return 'такой даты не существует'
    return None


def check_quality(quality):
    """Return errors for the featureAttributeTable record (S-102 Table 10-8)"""
    if not isinstance(quality, dict):
        return ['quality должен содержать поля таблицы качества']
    errors = []
    for key, value in quality.items():
        kind = QUALITY_FIELDS.get(key)
        if kind is None:
            errors.append(f'quality.{key}: такого поля нет в S-102 (табл. 10-8)')
        elif isinstance(kind, tuple):
            if type(value) is not int or value not in kind:
                codes = ', '.join(map(str, kind))
                errors.append(f'quality.{key} = {value!r}: допустимо {codes}')
        elif kind == 'real' and type(value) is not float:
            errors.append(f'quality.{key} = {value!r}: нужно число')
        elif kind == 'text' and not isinstance(value, str):
            errors.append(f'quality.{key} = {value!r}: нужна строка')
        elif kind == 'date':
            error = check_truncated_date(value)
            if error:
                errors.append(f'quality.{key} = {value!r}: {error}')

    # Table 10-8 Note 6
    if quality.get('fullSeafloorCoverageAchieved') == 0 and quality.get('bathyCoverage') == 1:
        errors.append('quality: при fullSeafloorCoverageAchieved = 0 bathyCoverage тоже должен быть 0')

    start = quality.get('surveyDateRange.dateStart')
    end = quality.get('surveyDateRange.dateEnd')
    if all(isinstance(d, str) and re.fullmatch(r'\d{8}', d) for d in (start, end)) and start > end:
        errors.append(f'quality: дата начала съёмки {start} позже даты окончания {end}')

    return errors


def check_xyz(xyz):
    """Return errors for the grid parameters of XYZ input"""
    if not isinstance(xyz, dict):
        return ['xyz должен содержать параметры сетки']
    errors = []
    for key in xyz:
        if key not in XYZ_KEYS:
            errors.append(f'xyz.{key}: неизвестный параметр')
    if xyz['columns'] not in XYZ_COLUMNS:
        errors.append(f'xyz.columns = {xyz['columns']!r}: допустимо lat_lon или lon_lat')

    epsg = xyz.get('grid_epsg')
    if epsg is None:
        errors.append('xyz.grid_epsg: укажите систему координат сетки')
    elif type(epsg) is not int or not is_allowed_epsg(epsg):
        errors.append(f'xyz.grid_epsg = {epsg!r}: допустимы коды из табл. 5-1 S-102')

    steps = []
    for key in ('step_x', 'step_y'):
        value = xyz.get(key)
        if value is None:
            errors.append(f'xyz.{key}: укажите шаг сетки')
        elif type(value) is not float or not value > 0:
            errors.append(f'xyz.{key} = {value!r}: нужно число больше 0')
        else:
            steps.append(value)

    tolerance = xyz.get('tolerance')
    if tolerance is None:
        errors.append('xyz.tolerance: укажите допуск')
    elif type(tolerance) is not float or not tolerance > 0:
        errors.append(f'xyz.tolerance = {tolerance!r}: нужно число больше 0')
    elif len(steps) == 2 and tolerance >= min(steps) / 2:
        # otherwise a point may be equally close to two nodes
        errors.append(f'xyz.tolerance = {tolerance:g}: должен быть меньше половины шага '
                      f'({min(steps) / 2:g})')
    return errors


def check_settings(settings):
    errors = []
    warnings = []

    if settings['input_values'] not in ('auto', 'depth', 'elevation'):
        errors.append(f'input_values = {settings['input_values']!r}: допустимо auto, depth или elevation')
    if settings['units'] != 'metres':
        errors.append(f'units = {settings['units']!r}: поддерживаются только metres')
    if 'vertical_datum' not in settings:
        errors.append('укажите обязательное значение vertical_datum')
    elif not isinstance(settings['vertical_datum'], int):
        errors.append(f'vertical_datum = {settings['vertical_datum']!r}: введите целочисленное значение')
    elif not (1 <= settings['vertical_datum'] <= 30 or settings['vertical_datum'] == 44):
        errors.append(f'vertical_datum = {settings['vertical_datum']}: допустимы 1–30 или 44')

    for key in ('horizontal_position_uncertainty', 'vertical_uncertainty'):
        value = settings[key]
        if value != -1 and value < 0:
            errors.append(f'{key} = {value}: допустимо -1 (неизвестно) или число ≥ 0')
    if 'producer_code' not in settings:
        errors.append('producer_code обязательное поле')
    elif not isinstance(settings['producer_code'], str):
        errors.append('producer_code должен быть строкой')
    elif not re.fullmatch(PRODUCER_CODE_RE, settings['producer_code']):
        errors.append(f'producer_code = {settings['producer_code']!r}: нужно ровно 4 символа A–Z, 0–9')

    if 'dataset_name' not in settings:
        errors.append('dataset_name обязательное поле')
    elif not isinstance(settings['dataset_name'], str):
        errors.append('dataset_name должен быть строкой')
    elif not re.fullmatch(DATASET_NAME_RE, settings['dataset_name']):
        errors.append(f'dataset_name = {settings['dataset_name']!r}: от 1 до 12 символов A–Z, 0–9 и _')
    for key in settings:
        if key not in KNOWN_KEYS:
            warnings.append(f'Поле {key!r}. Возможна опечатка в названии')
    issue_date = settings['issue_date']
    if not re.fullmatch(r'\d{8}', str(issue_date)):
        errors.append(f'issue_date = {issue_date!r}: нужно 8 цифр ГГГГММДД')
    else:
        try:
            datetime.strptime(issue_date, '%Y%m%d')
        except ValueError:
            errors.append(f'issue_date = {issue_date!r}: такой даты не существует')

    if 'issue_time' in settings and not re.fullmatch(ISSUE_TIME_RE, str(settings['issue_time'])):
        errors.append(f'issue_time = {settings['issue_time']!r}: нужно ччммссZ (UTC)')

    errors.extend(check_quality(settings['quality']))
    if 'xyz' in settings:
        errors.extend(check_xyz(settings['xyz']))

    return errors, warnings


def load_settings(path):
    raw = read_yaml(path)
    return apply_defaults(raw)
