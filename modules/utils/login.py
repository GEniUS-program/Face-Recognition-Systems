from PyQt6 import QtWidgets, QtGui
from modules.utils.communicator import Communicate


class LoginWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.setWindowTitle("Вход")
        self.setFixedSize(400, 350)

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.stacked_widget)

        self.login_signal_com = Communicate()
        self.login_signal = self.login_signal_com.signal

        self.register_signal_com = Communicate()
        self.register_signal = self.register_signal_com.signal

        self.login_view = self.create_login_view()
        self.stacked_widget.addWidget(self.login_view)

        self.registration_view = self.create_registration_view()
        self.stacked_widget.addWidget(self.registration_view)

        self.show_login_view()

    def create_login_view(self):
        login_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        self.username_label = QtWidgets.QLabel("Логин:")
        self.username_input = QtWidgets.QLineEdit()
        self.password_label = QtWidgets.QLabel("Пароль:")
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        
        self.error_text = QtWidgets.QLabel()
        self.error_text.setStyleSheet("color: red;")
        self.error_text.setWordWrap(True)
        self.error_text.hide()

        self.login_button = QtWidgets.QPushButton("Войти")
        self.login_button.clicked.connect(self.clicked_login_button)

        self.register_button = QtWidgets.QPushButton("Регистрация")
        self.register_button.clicked.connect(self.show_registration_view)

        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.error_text)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)

        login_widget.setLayout(layout)
        return login_widget

    def create_registration_view(self):
        registration_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        self.username_label_reg = QtWidgets.QLabel("Логин:")
        self.username_input_reg = QtWidgets.QLineEdit()

        self.email_label_reg = QtWidgets.QLabel("Электронная почта")
        self.email_input = QtWidgets.QLineEdit()

        self.password_label_reg = QtWidgets.QLabel("Пароль:")
        self.password_input_reg = QtWidgets.QLineEdit()
        self.password_input_reg.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password)

        self.confirm_password_label = QtWidgets.QLabel("Подтвердите пароль:")
        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password)

        self.error_text = QtWidgets.QLabel()
        self.error_text.setStyleSheet("color: red;")
        self.error_text.setWordWrap(True)
        self.error_text.hide()

        self.register_submit_button = QtWidgets.QPushButton(
            "Зарегистрироваться")
        self.register_submit_button.clicked.connect(
            self.clicked_register_button)

        self.switch_to_login_button = QtWidgets.QPushButton("Вход")
        self.switch_to_login_button.clicked.connect(self.show_login_view)

        layout.addWidget(self.username_label_reg)
        layout.addWidget(self.username_input_reg)
        layout.addWidget(self.email_label_reg)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_label_reg)
        layout.addWidget(self.password_input_reg)
        layout.addWidget(self.confirm_password_label)
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(self.error_text)
        layout.addWidget(self.register_submit_button)
        layout.addWidget(self.switch_to_login_button)

        registration_widget.setLayout(layout)
        return registration_widget

    def clicked_login_button(self):
        if self.username_input.text() == '' or self.password_input.text() == '':
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Заполните все поля!")
            return  
        
        self.login_signal.emit(
            [self.username_input.text(), self.password_input.text()])

    def clicked_register_button(self):
        if self.password_input_reg.text() == self.confirm_password_input.text() and self.username_input_reg.text() != '' and self.password_input_reg.text() != '' and self.email_input.text() != '':
            self.register_signal.emit(
                [self.username_input_reg.text(), self.password_input_reg.text(), self.email_input.text()])
        else:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Произошла ошибка, проверьте правильность введенных данных")

    def show_registration_view(self):
        self.stacked_widget.setCurrentWidget(self.registration_view)

    def show_login_view(self):
        self.stacked_widget.setCurrentWidget(self.login_view)

