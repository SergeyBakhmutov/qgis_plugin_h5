from qgis.core import (
    Qgis,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
)

from .base_algorithm import S102Algorithm
from .codes import GRID_CRS, XYZ_COLUMNS, code_options

GRID_CODES = list(GRID_CRS)
COLUMN_CODES = list(XYZ_COLUMNS.values())


class XyzToS102(S102Algorithm):
    """Convert XYZ points lying on a regular grid to S-102"""

    INPUT = 'INPUT'
    COLUMNS = 'COLUMNS'
    GRID_EPSG = 'GRID_EPSG'
    STEP_X = 'STEP_X'
    STEP_Y = 'STEP_Y'
    TOLERANCE = 'TOLERANCE'

    def name(self):
        # part of the algorithm id, never change or translate
        return 'xyz_to_s102'

    def displayName(self):
        return 'XYZ'

    def shortHelpString(self):
        return ('Колонки: координаты WGS 84 в градусах и глубина. '
                'Разделитель , ; пробел или табуляция, заголовок пропускается.\n'
                'Каждая точка лежит в узле сетки с точностью до допуска, '
                'одна точка на ячейку, без интерполяции.\n'
                'Шаг и допуск: градусы для EPSG:4326, метры для остальных.')

    def createInstance(self):
        return XyzToS102()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            self.INPUT, 'Входной XYZ (WGS 84, градусы)',
            behavior=Qgis.ProcessingFileParameterBehavior.File,
            fileFilter='XYZ (*.xyz *.txt *.csv);;Все файлы (*)'))
        self.add_dataset_parameters()
        self.addParameter(QgsProcessingParameterEnum(
            self.COLUMNS, 'Порядок колонок', options=list(XYZ_COLUMNS), defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.GRID_EPSG, 'Система координат сетки', options=code_options(GRID_CRS)))
        for name, label, optional in (
                (self.STEP_X, 'Шаг по X', False),
                (self.STEP_Y, 'Шаг по Y (пусто = как по X)', True),
                (self.TOLERANCE, 'Допуск до узла (меньше половины шага)', False)):
            self.addParameter(QgsProcessingParameterNumber(
                name, label, type=Qgis.ProcessingNumberParameterType.Double, optional=optional))
        self.add_output_parameters()

    def processAlgorithm(self, parameters, context, feedback):
        input_path = self.parameterAsFile(parameters, self.INPUT, context)
        raw = self.read_dataset_settings(parameters, context)
        # same keys as the xyz section of settings.yaml, checked in core.config
        xyz = {
            'columns': COLUMN_CODES[self.parameterAsEnum(parameters, self.COLUMNS, context)],
            'grid_epsg': GRID_CODES[self.parameterAsEnum(parameters, self.GRID_EPSG, context)],
            'step_x': self.parameterAsDouble(parameters, self.STEP_X, context),
            'tolerance': self.parameterAsDouble(parameters, self.TOLERANCE, context),
        }
        # empty step_y falls back to step_x in apply_defaults
        if parameters.get(self.STEP_Y) not in (None, ''):
            xyz['step_y'] = self.parameterAsDouble(parameters, self.STEP_Y, context)
        raw['xyz'] = xyz
        return self.run_conversion(input_path, raw, parameters, context, feedback)
