from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton


class ImagePathWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        
        self.path_label = QLabel("Изображение не выбрано")
        self.layout.addWidget(self.path_label)

        self.load_button = QPushButton("Загрузить изображение")
        self.load_button.clicked.connect(self.load_image)
        self.layout.addWidget(self.load_button)

        self.setLayout(self.layout)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Images (*.png *.xpm *.jpg *.bmp);;All Files (*)"
        )
        
        if file_path:
            self.path_label.setText(file_path)
