import os
from datetime import date

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from .codes import GRID_CRS, QUALITY_FORM, VERTICAL_DATUMS, XYZ_COLUMNS, choices

INPUT_FILTERS = {
    'tiff': 'GeoTIFF (*.tif *.tiff);;Все файлы (*)',
    'xyz': 'XYZ (*.xyz *.txt *.csv);;Все файлы (*)',
}
# the format follows the extension of the chosen file
INPUT_EXTENSIONS = {'.tif': 'tiff', '.tiff': 'tiff', '.xyz': 'xyz', '.txt': 'xyz', '.csv': 'xyz'}
FILE_CRS = '4326 — WGS 84, градусы'


def parse_code(text):
    return int(text.split(' — ')[0]) if text else None


def make_field(values=None, default=''):
    """Return a combo box with values or a line edit"""
    if values:
        widget = QComboBox()
        widget.addItems(values)
        widget.setCurrentText(default)
    else:
        widget = QLineEdit(default)
    return widget


class ConverterDialog(QDialog):
    """Conversion form, same fields and checks as gui.py of s102_f_conv"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('S-102 Converter')
        self.formats = {}
        self.fields = {}
        self.quality_fields = {}

        layout = QGridLayout(self)
        layout.addWidget(self.build_files(), 0, 0, 1, 2)
        layout.addWidget(self.build_metadata(), 1, 0)
        layout.addWidget(self.build_xyz(), 2, 0)
        layout.addWidget(self.build_quality(), 1, 1, 2, 1)
        self.toggle_xyz()
        self.toggle_quality()

    def build_files(self):
        group = QGroupBox('Файлы')
        grid = QGridLayout(group)

        self.input = QgsFileWidget()
        self.input.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.input.fileChanged.connect(self.on_input_changed)
        self.output_dir = QgsFileWidget()
        self.output_dir.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        grid.addWidget(QLabel('Формат'), 0, 0)
        formats = QHBoxLayout()
        for value, text in (('tiff', 'GeoTIFF'), ('xyz', 'XYZ')):
            # radio buttons with the same parent are exclusive
            button = QRadioButton(text)
            formats.addWidget(button)
            self.formats[value] = button
        formats.addStretch()
        grid.addLayout(formats, 0, 1)
        self.formats['tiff'].setChecked(True)
        # connected after the default is set, the XYZ group does not exist yet
        for button in self.formats.values():
            button.toggled.connect(self.toggle_xyz)

        for row, (label, widget) in enumerate(
                (('Входной файл', self.input), ('Папка вывода', self.output_dir)), start=1):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        return group

    def build_metadata(self):
        group = QGroupBox('Данные файла')
        form = QFormLayout(group)
        rows = (
            ('vertical_datum', 'Вертикальный датум *', choices(VERTICAL_DATUMS), ''),
            ('producer_code', 'Код производителя *', None, ''),
            ('dataset_name', 'Название набора *', None, ''),
            ('issue_date', 'Дата выпуска (ГГГГММДД) *', None, date.today().strftime('%Y%m%d')),
            ('issue_time', 'Время выпуска (ччммссZ)', None, ''),
            ('input_values', 'Значения во входном файле',
             ['auto', 'depth', 'elevation'], 'auto'),
            ('horizontal_position_uncertainty', 'Погрешность в плане, м (-1 = неизв.)', None, '-1'),
            ('vertical_uncertainty', 'Погрешность по глубине, м (-1 = неизв.)', None, '-1'),
        )
        for name, label, values, default in rows:
            form.addRow(label, self.add_field(name, values, default))
        form.addRow(QLabel('* обязательные поля'))
        return group

    def build_xyz(self):
        self.xyz_group = QGroupBox('Параметры XYZ')
        form = QFormLayout(self.xyz_group)

        # points are always read as WGS 84 degrees
        file_crs = QComboBox()
        file_crs.addItem(FILE_CRS)
        file_crs.setEnabled(False)
        form.addRow('Система координат файла', file_crs)
        form.addRow('Порядок колонок',
                    self.add_field('columns', list(XYZ_COLUMNS), next(iter(XYZ_COLUMNS))))
        form.addRow('Система координат сетки *', self.add_field('grid_epsg', choices(GRID_CRS)))
        self.fields['grid_epsg'].currentTextChanged.connect(self.update_units)

        self.unit_labels = []
        rows = (
            ('step_x', 'Шаг по X *'),
            ('step_y', 'Шаг по Y (пусто = как по X)'),
            ('tolerance', 'Допуск до узла *'),
        )
        for name, label in rows:
            row = QHBoxLayout()
            row.addWidget(self.add_field(name))
            unit = QLabel()
            unit.setMinimumWidth(16)
            row.addWidget(unit)
            self.unit_labels.append(unit)
            form.addRow(label, row)
        return self.xyz_group

    def build_quality(self):
        group = QGroupBox('QualityOfBathymetryCoverage, п. 10.2.8')
        layout = QVBoxLayout(group)
        self.write_quality = QCheckBox('Добавить таблицу')
        self.write_quality.toggled.connect(self.toggle_quality)
        layout.addWidget(self.write_quality)

        # fields are enabled together by the checkbox
        self.quality_box = QWidget()
        form = QFormLayout(self.quality_box)
        form.setContentsMargins(0, 0, 0, 0)
        for key, label, codes in QUALITY_FORM:
            widget = make_field(choices(codes) if codes else None)
            self.quality_fields[key] = widget
            form.addRow(label, widget)
        layout.addWidget(self.quality_box)
        layout.addStretch()
        return group

    def add_field(self, name, values=None, default=''):
        """Create a field of the form and keep it by name"""
        self.fields[name] = make_field(values, default)
        return self.fields[name]

    def input_type(self):
        return 'xyz' if self.formats['xyz'].isChecked() else 'tiff'

    def toggle_xyz(self):
        self.input.setFilter(INPUT_FILTERS[self.input_type()])
        self.xyz_group.setEnabled(self.input_type() == 'xyz')

    def toggle_quality(self):
        self.quality_box.setEnabled(self.write_quality.isChecked())

    def update_units(self):
        # steps are in the units of the grid CRS (S-102 Table 10-6)
        epsg = parse_code(self.fields['grid_epsg'].currentText())
        unit = '' if epsg is None else '°' if epsg == 4326 else 'м'
        for label in self.unit_labels:
            label.setText(unit)

    def on_input_changed(self, path):
        """Switch the format by the extension of the chosen file"""
        ext = os.path.splitext(path)[1].lower()
        if ext in INPUT_EXTENSIONS:
            self.formats[INPUT_EXTENSIONS[ext]].setChecked(True)
