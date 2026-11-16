import os
from datetime import date

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
)

from .codes import VERTICAL_DATUMS, choices

INPUT_FILTERS = {
    'tiff': 'GeoTIFF (*.tif *.tiff);;Все файлы (*)',
    'xyz': 'XYZ (*.xyz *.txt *.csv);;Все файлы (*)',
}
# the format follows the extension of the chosen file
INPUT_EXTENSIONS = {'.tif': 'tiff', '.tiff': 'tiff', '.xyz': 'xyz', '.txt': 'xyz', '.csv': 'xyz'}


class ConverterDialog(QDialog):
    """Conversion form, same fields and checks as gui.py of s102_f_conv"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('S-102 Converter')
        self.formats = {}
        self.fields = {}

        layout = QGridLayout(self)
        layout.addWidget(self.build_files(), 0, 0, 1, 2)
        layout.addWidget(self.build_metadata(), 1, 0)

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
            button.toggled.connect(self.toggle_xyz)
            formats.addWidget(button)
            self.formats[value] = button
        formats.addStretch()
        grid.addLayout(formats, 0, 1)
        self.formats['tiff'].setChecked(True)

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

    def add_field(self, name, values=None, default=''):
        """Create a combo box with values or a line edit, keep it by name"""
        if values:
            widget = QComboBox()
            widget.addItems(values)
            widget.setCurrentText(default)
        else:
            widget = QLineEdit(default)
        self.fields[name] = widget
        return widget

    def input_type(self):
        return 'xyz' if self.formats['xyz'].isChecked() else 'tiff'

    def toggle_xyz(self):
        self.input.setFilter(INPUT_FILTERS[self.input_type()])

    def on_input_changed(self, path):
        """Switch the format by the extension of the chosen file"""
        ext = os.path.splitext(path)[1].lower()
        if ext in INPUT_EXTENSIONS:
            self.formats[INPUT_EXTENSIONS[ext]].setChecked(True)
