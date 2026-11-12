import os

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from .codes import VERTICAL_DATUMS, code_options
from .core.config import apply_defaults
from .core.converter import convert
from .core.writer import make_filename

DATUM_CODES = list(VERTICAL_DATUMS)


class GeoTiffToS102(QgsProcessingAlgorithm):
    """Convert a single band GeoTIFF with depths to S-102"""

    INPUT = 'INPUT'
    VERTICAL_DATUM = 'VERTICAL_DATUM'
    PRODUCER_CODE = 'PRODUCER_CODE'
    DATASET_NAME = 'DATASET_NAME'
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
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_DIR, 'Папка вывода'))
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT, 'Файл S-102'))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        datum = DATUM_CODES[self.parameterAsEnum(parameters, self.VERTICAL_DATUM, context)]
        # same keys as in settings.yaml, defaults and checks come from core.config
        settings = apply_defaults({
            'vertical_datum': datum,
            'producer_code': self.parameterAsString(parameters, self.PRODUCER_CODE, context).strip(),
            'dataset_name': self.parameterAsString(parameters, self.DATASET_NAME, context).strip(),
        })
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
