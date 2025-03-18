# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets
from modules.utils.image_utils.image_path import ImagePathWidget
from modules.utils.database_worker import DataBaseWorker
from modules.utils.simple_dialog import DialogWindow
from modules.utils.communicator import Communicate
import logging


class DataBaseView(QtWidgets.QWidget):
    def __init__(self):
        super(DataBaseView, self).__init__()
        self.db_worker = DataBaseWorker()
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QHBoxLayout()

        self.left_panel_layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.left_panel_layout)

        # Set up the database info table
        self.database_info_table = QtWidgets.QTableWidget()
        self.database_info_table.setColumnCount(3)  # Set the number of columns
        self.database_info_table.setHorizontalHeaderLabels(
            ['ФИО', 'Ур. доступа', 'Лицо'])  # Set header labels
        self.database_info_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.database_info_table.itemClicked.connect(self.on_row_selected)
        self.layout.addWidget(self.database_info_table)

        self.db_status_label = QtWidgets.QLabel("Database Status: Ready")
        self.left_panel_layout.addWidget(self.db_status_label)

        self.column_layout = QtWidgets.QVBoxLayout()

        # Name input and add button
        self.name_add_layout = QtWidgets.QHBoxLayout()
        self.name_field = QtWidgets.QLineEdit()
        self.name_field.setPlaceholderText('ФИО')
        self.add_button = QtWidgets.QPushButton('Добавить')
        self.add_button.clicked.connect(self.add_gate_action)
        self.name_add_layout.addWidget(self.name_field)
        self.name_add_layout.addWidget(self.add_button)
        self.column_layout.addLayout(self.name_add_layout)

        # Clearance input and edit button
        self.clearance_edit_layout = QtWidgets.QHBoxLayout()
        self.clearance_field = QtWidgets.QLineEdit()
        self.clearance_field.setPlaceholderText('Ур. доступа')
        self.edit_button = QtWidgets.QPushButton('Редактировать')
        self.edit_button.clicked.connect(self.edit_action)
        self.clearance_edit_layout.addWidget(self.clearance_field)
        self.clearance_edit_layout.addWidget(self.edit_button)
        self.column_layout.addLayout(self.clearance_edit_layout)

        # Face image input and delete button
        self.face_delete_layout = QtWidgets.QHBoxLayout()
        self.face_image_field = ImagePathWidget()
        self.delete_button = QtWidgets.QPushButton('Удалить')
        self.delete_button.clicked.connect(self.delete_action)
        self.face_delete_layout.addWidget(self.face_image_field)
        self.face_delete_layout.addWidget(self.delete_button)
        self.column_layout.addLayout(self.face_delete_layout)

        # Add the actions layout to the left panel layout
        self.left_panel_layout.addLayout(self.column_layout)

        # Search bar at the bottom
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText('Поиск по базе данных')
        self.left_panel_layout.addWidget(self.search_bar)
        # Set the layout for this widget
        self.setLayout(self.layout)

        self.update_db_table()

    def add_gate_action(self):
        dialog = DialogWindow('Вы уверены, что хотите добавить новую запись в базу данных?')
        dialog.dialog_signal.connect(lambda x: self.add_action(x))
        dialog.exec()

    def add_action(self, answer):
        if answer == 'a':
            try:
                self.db_worker.add(self.name_field.text(
                ), self.clearance_field.text(), self.face_image_field.path_label.text())
            except Exception as e:
                logging.error(
                    f'An error occured when adding data to database. Error details: {e}')
                logging.warning('Database worker is not ready to add data.')

            self.update_db_table()
        else:
            logging.info('Adding data cancelled.')

    def edit_action(self):
        line_index = self.database_info_table.currentRow()

        logging.info(f"Editing data in line {line_index} of database...")

        try:
            self.db_worker.edit(self.name_field.text(), self.clearance_field.text(
            ), self.face_image_field.path_label.text(), line_index)
        except Exception as e:
            logging.error(
                f'An error occured when editing data in database. Error details: {e}')
            logging.warning('Database worker is not ready to edit data.')

        self.update_db_table()

    def delete_action(self):
        logging.info("Deleting data from database...")
        try:
            self.db_worker.delete(self.name_field.text(
            ), self.clearance_field.text(), self.face_image_field.path_label.text())
        except Exception as e:
            logging.error(
                f'An error occured when deleting data from database. Error details: {e}')
            logging.warning('Database worker is not ready to delete data.')
        self.update_db_table()

    def update_db_table(self):
        logging.info("Updating database table...")
        db_worker = DataBaseWorker()

        # Clear existing data
        self.database_info_table.setRowCount(0)

        # Set the number of rows based on the database content
        self.database_info_table.setRowCount(len(db_worker.names))
        for i, (name, clearance, facepath) in enumerate(zip(db_worker.names, db_worker.clearances, db_worker.faces)):
            self.database_info_table.setItem(
                i, 0, QtWidgets.QTableWidgetItem(name))
            self.database_info_table.setItem(
                i, 1, QtWidgets.QTableWidgetItem(clearance))
            self.database_info_table.setItem(
                i, 2, QtWidgets.QTableWidgetItem(facepath))

    def on_row_selected(self):
        print("Selected row in database table...")
        line_index = self.database_info_table.currentRow()
        try:
            self.face_image_field.path_label.setText(
                self.database_info_table.item(line_index, 2).text())
            self.name_field.setText(
                self.database_info_table.item(line_index, 0).text())
            self.clearance_field.setText(
                self.database_info_table.item(line_index, 1).text())
        except:
            pass
