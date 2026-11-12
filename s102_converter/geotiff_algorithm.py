import os
from datetime import date

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from .codes import VERTICAL_DATUMS, code_options
from .core.config import apply_defaults
from .core.converter import convert
from .core.writer import make_filename

DATUM_CODES = list(VERTICAL_DATUMS)
INPUT_VALUE_OPTIONS = ['auto', 'depth', 'elevation']


class GeoTiffToS102(QgsProcessingAlgorithm):
    """Convert a single band GeoTIFF with depths to S-102"""

    INPUT = 'INPUT'
    VERTICAL_DATUM = 'VERTICAL_DATUM'
    PRODUCER_CODE = 'PRODUCER_CODE'
    DATASET_NAME = 'DATASET_NAME'
    ISSUE_DATE = 'ISSUE_DATE'
    ISSUE_TIME = 'ISSUE_TIME'
    INPUT_VALUES = 'INPUT_VALUES'
    HORIZONTAL_UNCERTAINTY = 'HORIZONTAL_UNCERTAINTY'
    VERTICAL_UNCERTAINTY = 'VERTICAL_UNCERTAINTY'
    OUTPUT_DIR = 'OUTPUT_DIR'
    OUTPUT = 'OUTPUT'

    def name(self):
        # part of the algorithm id, never change or translate
        return 'geotiff_to_s102'

    def displayName(self):
        return 'GeoTIFF'

    def shortHelpString(self):
        return ('Записывает S-102 ред. 3.0.0 из однослойного GeoTIFF с глубинами '
                'или высотами в метрах. Имя файла: 102 + код производителя + '
                'название набора + .H5')

    def createInstance(self):
        return GeoTiffToS102()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT, 'Входной GeoTIFF'))
        self.addParameter(QgsProcessingParameterEnum(
            self.VERTICAL_DATUM, 'Вертикальный датум',
            options=code_options(VERTICAL_DATUMS),
            defaultValue=DATUM_CODES.index(23)))
        self.addParameter(QgsProcessingParameterString(
            self.PRODUCER_CODE, 'Код производителя (4 символа A–Z, 0–9)'))
        self.addParameter(QgsProcessingParameterString(
            self.DATASET_NAME, 'Название набора (1–12 символов A–Z, 0–9, _)'))
        self.addParameter(QgsProcessingParameterString(
            self.ISSUE_DATE, 'Дата выпуска (ГГГГММДД)',
            defaultValue=date.today().strftime('%Y%m%d')))
        self.addParameter(QgsProcessingParameterString(
            self.ISSUE_TIME, 'Время выпуска (ччммссZ)', optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.INPUT_VALUES, 'Значения во входном файле',
            options=INPUT_VALUE_OPTIONS, defaultValue=0))
        # -1 means unknown (S-102 Table 10-4), range is checked in core.config
        for name, label in (
                (self.HORIZONTAL_UNCERTAINTY, 'Погрешность в плане, м (-1 = неизв.)'),
                (self.VERTICAL_UNCERTAINTY, 'Погрешность по глубине, м (-1 = неизв.)')):
            self.addParameter(QgsProcessingParameterNumber(
                name, label, type=Qgis.ProcessingNumberParameterType.Double, defaultValue=-1))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_DIR, 'Папка вывода'))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT, 'Файл S-102'))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        datum = DATUM_CODES[self.parameterAsEnum(parameters, self.VERTICAL_DATUM, context)]
        # same keys as in settings.yaml, defaults and checks come from core.config
        raw = {
            'vertical_datum': datum,
            'producer_code': self.parameterAsString(parameters, self.PRODUCER_CODE, context).strip(),
            'dataset_name': self.parameterAsString(parameters, self.DATASET_NAME, context).strip(),
            'issue_date': self.parameterAsString(parameters, self.ISSUE_DATE, context).strip(),
            'input_values': INPUT_VALUE_OPTIONS[self.parameterAsEnum(parameters, self.INPUT_VALUES, context)],
            'horizontal_position_uncertainty': self.parameterAsDouble(
                parameters, self.HORIZONTAL_UNCERTAINTY, context),
            'vertical_uncertainty': self.parameterAsDouble(parameters, self.VERTICAL_UNCERTAINTY, context),
        }
        # optional in S-102, written only when given (as in gui.py)
        issue_time = self.parameterAsString(parameters, self.ISSUE_TIME, context).strip()
        if issue_time:
            raw['issue_time'] = issue_time
        settings = apply_defaults(raw)
        output_dir = self.parameterAsFileOutput(parameters, self.OUTPUT_DIR, context)

        summary, log = convert(layer.source(), settings, output_dir, 'параметры')
        for source, errors, warnings in log:
            prefix = f'{source}: ' if source else ''
            for w in warnings:
                feedback.pushWarning(f'{prefix}{w}')
            for e in errors:
                feedback.reportError(f'{prefix}{e}')
        if summary is None:
            raise QgsProcessingException('Файл не создан или не прошёл проверку')

        feedback.pushInfo(summary)
        return {self.OUTPUT: os.path.join(output_dir, make_filename(settings))}
