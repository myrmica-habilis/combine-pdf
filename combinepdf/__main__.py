import json
import os
from types import SimpleNamespace

from PySide2 import QtWidgets, QtGui, QtCore

from . import constants, pdf_utils, utils, __version__


class FileBox(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setAutoFillBackground(True)
        self.default_bg = self.palette().color(self.palette().Window)

        self.filename = ''
        self.is_temporary_file = False
        # number of pages of the currently open PDF file
        self.pages = 0
        # list of tuples representing page ranges selected for output
        self.output_tuples = []
        self.output_page_count = 0

        # first row of widgets
        self.button_Browse = QtWidgets.QPushButton('Select PDF...')
        self.button_Browse.clicked.connect(self.open_pdf_file)

        self.button_Image = QtWidgets.QPushButton('Select image...')
        self.button_Image.clicked.connect(self.open_image_file)

        self.button_Blank = QtWidgets.QPushButton('Blank page')
        self.button_Blank.clicked.connect(self.add_blank_page)

        self.filename_label = QtWidgets.QLabel()
        self.filename_label.setVisible(False)

        self.pages_info = QtWidgets.QLabel()
        self.pages_info.setStyleSheet(constants.INFO_LABEL)

        self.button_Remove = QtWidgets.QPushButton()
        self.button_Remove.setIcon(QtGui.QIcon(constants.ICON_TRASH))
        self.button_Remove.setToolTip('Remove this file')
        self.button_Remove.setFixedWidth(30)
        self.button_Remove.clicked.connect(self.remove_file)
        self.button_Remove.setVisible(False)

        # second row of widgets
        self.rbutton_All = QtWidgets.QRadioButton('All')
        self.rbutton_All.toggled.connect(self.switch_radiobuttons)
        self.rbutton_All.setVisible(False)

        self.rbutton_Pages = QtWidgets.QRadioButton('Pages')
        self.rbutton_Pages.setVisible(False)

        self.rbutton_group = QtWidgets.QButtonGroup()
        self.rbutton_group.addButton(self.rbutton_All)
        self.rbutton_group.addButton(self.rbutton_Pages)

        self.page_select_edit = QtWidgets.QLineEdit()
        self.page_select_edit.setPlaceholderText('Example: 1, 3-5, 8')
        self.page_select_edit.textEdited.connect(self.update_select_info)
        self.page_select_edit.textEdited.connect(self.parent()
                                                 .update_main_button)
        self.page_select_edit.setVisible(False)

        self.page_select_info = QtWidgets.QLabel()
        self.page_select_info.setVisible(False)
        self.page_select_info.setStyleSheet(constants.INFO_LABEL)

        self.setLayout(self.get_layout())

    def get_layout(self):
        layout = QtWidgets.QGridLayout()

        layout.addWidget(self.button_Browse, 1, 0)
        layout.addWidget(self.button_Image, 1, 1)
        layout.addWidget(self.button_Blank, 1, 2)
        layout.addWidget(self.filename_label, 1, 2, 1, 3)
        layout.addWidget(self.pages_info, 1, 5)
        layout.addWidget(self.button_Remove, 1, 6)

        layout.addWidget(self.rbutton_All, 2, 2)
        layout.addWidget(self.rbutton_Pages, 2, 3)
        layout.addWidget(self.page_select_edit, 2, 4)
        layout.addWidget(self.page_select_info, 2, 5)
        layout.addItem(QtWidgets.QSpacerItem(30, 0), 2, 6)

        for column, stretch in zip((2, 3, 4, 5), (10, 10, 55, 25)):
            layout.setColumnStretch(column, stretch)

        return layout

    def open_pdf_file(self):
        filename = self.get_pdf_from_dialog()
        if not filename:
            return

        self.parent().config.open_path = os.path.dirname(filename)
        try:
            num_pages = pdf_utils.get_pdf_num_pages(filename)
        except Exception as err:
            message_box(
                icon=QtWidgets.QMessageBox.Warning,
                title='Warning',
                text='File could not be read.',
                detailed=f'File: {filename}\n\nError: {err!r}'
            )
        else:
            set_widget_background(self, constants.PDF_FILE_BGCOLOR)
            self.hide_pushbuttons()
            self.show_widgets()
            self.filename_label.setText(utils.trimmed_basename(filename))
            self.filename_label.setToolTip(filename)
            self.pages_info.setText(f'{utils.page_count_repr(num_pages)} total')
            self.rbutton_All.setChecked(True)
            self.page_select_edit.setText('')

            self.filename = filename
            self.pages = num_pages
            self.update_output([(0, num_pages)])
            self.parent().update_main_button()

    def get_pdf_from_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Open a PDF file',
            dir=self.parent().config.open_path,
            filter='PDF files (*.pdf)'
        )
        return filename

    def open_image_file(self):
        filename = self.get_image_from_dialog()
        if not filename:
            return

        self.parent().config.image_path = os.path.dirname(filename)
        temp_pdf_filename = utils.get_temporary_filename(suffix='.pdf')
        try:
            pdf_utils.save_image_as_pdf(filename, temp_pdf_filename)
        # PIL.UnidentifiedImageError is subclass of OSError
        except OSError as err:
            message_box(
                icon=QtWidgets.QMessageBox.Warning,
                title='Warning',
                text='Image to PDF conversion failed.',
                detailed=f'File: {filename}\n\nError: {err!r}'
            )
        else:
            set_widget_background(self, constants.IMG_FILE_BGCOLOR)
            self.hide_pushbuttons()
            self.show_widgets(show_all=False)
            self.filename_label.setText(utils.trimmed_basename(filename))
            self.filename_label.setToolTip(filename)

            self.filename = temp_pdf_filename
            self.is_temporary_file = True
            self.pages = 1
            self.update_output([(0, 1)])
            self.parent().update_main_button()

    def get_image_from_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Open an image file',
            dir=self.parent().config.image_path,
            filter='Image files (*.png *.jpg *.jpeg *.gif *.bmp)'
        )
        return filename

    def add_blank_page(self):
        set_widget_background(self, constants.BLANK_PAGE_BGCOLOR)
        self.hide_pushbuttons()
        self.show_widgets(show_all=False)
        self.filename_label.setText('BLANK PAGE')
        self.filename_label.setToolTip('')

        self.pages = 1
        self.output_page_count = 1
        self.parent().update_main_button()

    def remove_file(self):
        set_widget_background(self, self.default_bg)
        self.show_pushbuttons()
        self.hide_widgets()
        self.pages_info.setText('')

        if self.is_temporary_file:
            os.remove(self.filename)
            self.is_temporary_file = False
        self.filename = ''
        self.pages = 0
        self.update_output([])
        self.parent().update_main_button()

    def show_pushbuttons(self):
        self.button_Browse.setVisible(True)
        self.button_Image.setVisible(True)
        self.button_Blank.setVisible(True)

    def hide_pushbuttons(self):
        self.button_Browse.setVisible(False)
        self.button_Image.setVisible(False)
        self.button_Blank.setVisible(False)

    def show_widgets(self, show_all=True):
        self.filename_label.setVisible(True)
        self.button_Remove.setVisible(True)
        if show_all:
            self.rbutton_All.setVisible(True)
            self.rbutton_Pages.setVisible(True)
            self.page_select_edit.setVisible(True)

    def hide_widgets(self):
        self.filename_label.setVisible(False)
        self.button_Remove.setVisible(False)
        self.rbutton_All.setVisible(False)
        self.rbutton_Pages.setVisible(False)
        self.page_select_edit.setVisible(False)
        self.page_select_info.setVisible(False)

    def switch_radiobuttons(self):
        if self.rbutton_All.isChecked():
            self.update_output([(0, self.pages)])
            self.page_select_edit.setEnabled(False)
            self.page_select_info.setVisible(False)
        else:
            self.update_select_info()
            self.page_select_edit.setEnabled(True)
            self.page_select_edit.setFocus()
            self.page_select_info.setVisible(True)
        self.parent().update_main_button()

    def update_output(self, tuples):
        self.output_tuples = tuples
        self.output_page_count = sum(len(range(*tup)) for tup in tuples)

    def update_select_info(self):
        text = self.page_select_edit.text()
        try:
            ranges = utils.get_ranges(text, self.pages)
        except ValueError:
            ranges = []
        self.update_output(ranges)

        if self.output_tuples or text == '':
            self.page_select_edit.setStyleSheet('')
            self.page_select_info.setText(
                f'{utils.page_count_repr(self.output_page_count)} selected')
        else:
            self.page_select_info.setText('')
            self.page_select_edit.setStyleSheet(constants.INVALID)


class MainWindow(QtWidgets.QWidget):
    def __init__(self, window_title, window_size):
        super().__init__()
        self.setWindowTitle(window_title)
        self.resize(QtCore.QSize(*window_size))

        self.config = get_config(constants.CONFIG_PATH)
        self.file_boxes = [FileBox(self)
                           for __ in range(self.config.num_items)]
        self.central_layout = self.get_central_layout()
        self.button_Combine = self.get_main_button()
        self.setLayout(self.get_master_layout())

    def get_top_layout(self):
        help_button = QtWidgets.QPushButton('Help')
        help_button.setIcon(QtGui.QIcon(constants.ICON_QUESTION))
        help_button.clicked.connect(self.help_message)

        about_button = QtWidgets.QPushButton('About')
        about_button.setIcon(QtGui.QIcon(constants.ICON_INFO))
        about_button.clicked.connect(self.about_message)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(help_button, 0, 1)
        layout.addWidget(about_button, 0, 2)

        for column, stretch in enumerate((10, 1, 1)):
            layout.setColumnStretch(column, stretch)

        return layout

    def get_central_layout(self):
        layout = QtWidgets.QVBoxLayout()
        for file_box in self.file_boxes:
            layout.addWidget(file_box)

        return layout

    def get_bottom_layout(self):
        add_button = QtWidgets.QPushButton('&Add')
        add_button.setIcon(QtGui.QIcon(constants.ICON_PLUS))
        add_button.setToolTip('Add another row (Alt+A)')
        add_button.clicked.connect(self.add_item)

        exit_button = QtWidgets.QPushButton('E&xit')
        exit_button.setIcon(QtGui.QIcon(constants.ICON_EXIT))
        exit_button.setFixedHeight(50)
        exit_button.setToolTip('Exit the application (Alt+X)')
        exit_button.clicked.connect(self.exit)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(add_button, 0, 0)
        layout.addWidget(self.button_Combine, 1, 2)
        layout.addWidget(exit_button, 1, 3)

        for column, stretch in enumerate((1, 1, 3, 1, 2)):
            layout.setColumnStretch(column, stretch)

        return layout

    def get_master_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.get_top_layout())
        layout.addLayout(self.central_layout)
        layout.addLayout(self.get_bottom_layout())

        return layout

    def get_main_button(self):
        button = QtWidgets.QPushButton('Combine && &Save')
        button.setIcon(QtGui.QIcon(constants.ICON_COMBINE))
        button.setFixedHeight(50)
        button.setToolTip('Save the combined PDF file (Alt+S)')
        button.clicked.connect(self.save_file)
        button.setEnabled(False)

        return button

    def save_file(self):
        output_filename = self.get_output_name_from_dialog()
        if not output_filename:
            return

        self.config.save_path, self.config.save_filename = os.path.split(output_filename)
        if output_filename in (f_box.filename for f_box in self.file_boxes):
            self.no_overwrite_message()
        else:
            pdf_utils.write_combined_pdf(self.file_boxes, output_filename)

    def get_output_name_from_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Save PDF file as...',
            dir=os.path.join(self.config.save_path, self.config.save_filename),
            filter='PDF files (*.pdf)'
        )
        return filename

    def update_main_button(self):
        total_pages = sum(f_box.output_page_count for f_box in self.file_boxes)
        if total_pages > 0:
            self.button_Combine.setText(
                f'Combine && &Save {utils.page_count_repr(total_pages)}')
            self.button_Combine.setEnabled(True)
        else:
            self.button_Combine.setText('Combine && &Save')
            self.button_Combine.setEnabled(False)

    def add_item(self):
        file_box = FileBox(self)
        self.file_boxes.append(file_box)
        self.central_layout.addWidget(file_box)

    @staticmethod
    def no_overwrite_message():
        message_box(icon=QtWidgets.QMessageBox.Warning, title='Warning',
                    text=constants.NO_OVERWRITE_TEXT)

    @staticmethod
    def help_message():
        message_box(icon=QtWidgets.QMessageBox.Information, title='Help',
                    text=constants.HELP_TEXT)

    @staticmethod
    def about_message():
        message_box(icon=QtWidgets.QMessageBox.Information, title='About',
                    text=constants.ABOUT_TEXT.format(__version__))

    def run(self, app):
        self.show()
        app.exec_()

    def exit(self):
        with open(constants.CONFIG_PATH, 'w') as config_file:
            json.dump(self.config.__dict__, config_file, indent=4)
        for file_box in self.file_boxes:
            if file_box.is_temporary_file:
                os.remove(file_box.filename)
                file_box.is_temporary_file = False
        self.close()


def get_config(file_path):
    result = dict(open_path=os.curdir, image_path=os.curdir,
                  save_path=os.curdir, save_filename='Combined.pdf',
                  num_items=3)

    try:
        with open(file_path) as config_file:
            result.update(json.load(config_file))
    # json.decoder.JSONDecodeError is subclass of ValueError
    except (FileNotFoundError, ValueError):
        pass

    return SimpleNamespace(**result)


def message_box(icon, title, text, detailed=None, informative=None):
    msg_box = QtWidgets.QMessageBox(icon, title, text)
    if detailed:
        msg_box.setDetailedText(detailed)
    if informative:
        msg_box.setInformativeText(informative)
    msg_box.exec_()


def set_widget_background(widget, color):
    palette = widget.palette()
    palette.setColor(palette.Window, QtGui.QColor(color))
    widget.setPalette(palette)


def main():
    app = QtWidgets.QApplication()
    app_window = MainWindow(constants.WINDOW_TITLE, constants.WINDOW_SIZE)
    app_window.run(app)


if __name__ == '__main__':
    main()
