import sys
import cv2
import pickle
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QDialog, QHBoxLayout, QLabel, QSlider, QSpinBox, QLineEdit,
    QInputDialog, QComboBox, QColorDialog, QAction, QSplashScreen, QCheckBox, QMessageBox, QListWidget, QListWidgetItem, QScrollArea
)
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QTimer, QPointF, QByteArray, QBuffer, QIODevice, QRectF
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QTransform, QColor, QPen, QPainterPath, QFont, QImageWriter

class MergeDialog(QDialog):
    def __init__(self, objects):
        super().__init__()
        self.setWindowTitle("Select Images to Merge")
        self.setFixedSize(400, 300)

        self.selected_objects = []
        self.objects = objects

        layout = QVBoxLayout()

        # Instruction label
        layout.addWidget(QLabel("Select the images you want to merge:"))

        # List of images with checkboxes
        self.checkboxes = []
        for index, obj in enumerate(objects):
            checkbox = QCheckBox(f"Image {index + 1}")
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_selection)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def accept_selection(self):
        self.selected_objects = [
            obj for checkbox, obj in zip(self.checkboxes, self.objects) if checkbox.isChecked()
        ]
        self.accept()

class SplashScreen(QSplashScreen):
    def __init__(self, image_path, width=400, height=300):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            raise FileNotFoundError(f"Unable to load splash image: {image_path}")
        
        scaled_pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super(SplashScreen, self).__init__(scaled_pixmap)
        # Corrected the flag name
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)


class CanvasSettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create New Canvas")
        self.setWindowIcon(QIcon(r'fairy tail.png'))
        self.setFixedSize(300, 250)
        
        # Main layout
        layout = QVBoxLayout()

        # Project name input
        layout.addWidget(QLabel("Project Name:"))
        self.project_name_input = QLineEdit()
        layout.addWidget(self.project_name_input)

        # Width setting
        layout.addWidget(QLabel("Width:"))
        width_layout = QHBoxLayout()
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(100, 1600)
        self.width_slider.setValue(1200)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(100, 1600)
        self.width_spinbox.setValue(1200)
        self.width_slider.valueChanged.connect(self.width_spinbox.setValue)
        self.width_spinbox.valueChanged.connect(self.width_slider.setValue)
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_spinbox)
        layout.addLayout(width_layout)

        # Height setting
        layout.addWidget(QLabel("Height:"))
        height_layout = QHBoxLayout()
        self.height_slider = QSlider(Qt.Horizontal)
        self.height_slider.setRange(100, 1000)
        self.height_slider.setValue(800)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(100, 1000)
        self.height_spinbox.setValue(800)
        self.height_slider.valueChanged.connect(self.height_spinbox.setValue)
        self.height_spinbox.valueChanged.connect(self.height_slider.setValue)
        height_layout.addWidget(self.height_slider)
        height_layout.addWidget(self.height_spinbox)
        layout.addLayout(height_layout)

        # Create canvas button
        self.create_button = QPushButton("Create Canvas")
        self.create_button.clicked.connect(self.accept)
        layout.addWidget(self.create_button)

        self.setLayout(layout)

    def get_canvas_settings(self):
        project_name = self.project_name_input.text()
        width = self.width_spinbox.value()
        height = self.height_spinbox.value()
        return project_name, width, height

class CanvasWindow(QMainWindow):
    def __init__(self, width, height):
        super().__init__()
        self.setWindowTitle("Fairy Painting")
        self.setWindowIcon(QIcon(r'fairy tail.png'))
        self.setGeometry(0, 0, 2000, 1000)

        # Main widget without layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Background for the left-side buttons
        self.button_background = QLabel(self)
        self.button_background.setGeometry(0, 50, 160, 2600)
        self.button_background.setStyleSheet("background-color: purple; border-radius: 10px;")
        
        self.button_atas = QLabel(self)
        self.button_atas.setGeometry(-10, 25, 2600, 100)
        self.button_atas.setStyleSheet("background-color: purple; border-radius: 10px;")
        
        # Add Change Pixel Color button
        self.change_pixel_color_button = QPushButton("Change Pixel Color", self)
        self.change_pixel_color_button.setGeometry(1010, 30, 140, 40)  # Adjust position as needed
        self.change_pixel_color_button.setCheckable(True)  # Make the button checkable
        self.change_pixel_color_button.toggled.connect(self.toggle_change_color_mode)  # Connect the toggled signal
        
        self.setup_menu()
        self.selected_object=[]

        # Background for the canvas
        self.canvas_background = QLabel(main_widget)
        self.canvas_background.setFixedSize(width + 1500, height + 1000)
        self.canvas_background.move(20, 20)
        self.canvas_background.setStyleSheet("background-color: pink;")

        # Canvas area
        self.canvas_label = QLabel(main_widget)
        self.canvas_label.setFixedSize(width, height)
        self.canvas_label.move(200, 150)
        self.create_canvas(width, height)

        # List to keep track of objects on the canvas
        self.objects = []  # List of QRect for objects (images)
        self.selected_object = None  # Currently selected object
        self.drag_mode_active = False
        self.rotate_mode_active = False
        self.drag_start_pos = None
        self.rotation_start_angle = None
        
        self.last_point = None
        self.is_shape_mode = False
        self.elements = []  # To store all persistent elements on the canvas
        
        self.change_color_mode = False
        self.selected_color = QColor(Qt.black)  # Default color
        self.change_pixel_color_button.setCheckable(True)

        self.canvas_scale = 1.0  # Track the current scale of the canvas
        self.original_canvas = self.canvas.copy()  # Save the original canvas

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setGeometry(200, 150, 1200, 800)  # Set maximum possible canvas size
        self.scroll_area.setWidgetResizable(True)

        # Add the canvas QLabel inside the scroll area
        self.canvas_label = QLabel(self.scroll_area)
        self.canvas_label.setGeometry(0, 0, 1200, 800)  # Initial canvas size

        # Set the canvas QLabel as the scroll area's widget
        self.scroll_area.setWidget(self.canvas_label)

        # Initialize the canvas
        self.create_canvas(width, height)

        # Add the canvas QLabel inside the scroll area
        self.canvas_label = QLabel(self.scroll_area)
        self.scroll_area.setWidget(self.canvas_label)

        # Initialize the canvas
        self.create_canvas(width, height)

        # Upload Image Button
        self.upload_button = QPushButton(self)
        upload_icon = QIcon("upload.png")
        self.upload_button.setIcon(upload_icon)
        self.upload_button.setGeometry(160, 50, 60, 60)
        self.upload_button.setIconSize(self.upload_button.size())
        self.upload_button.clicked.connect(self.upload_image)
        
        # Drag Mode Button
        self.drag_button = QPushButton(self)
        drag_icon = QIcon("drag.png")
        self.drag_button.setIcon(drag_icon)
        self.drag_button.setGeometry(10, 100, 60, 60)
        self.drag_button.setIconSize(self.drag_button.size())
        self.drag_button.setCheckable(True)
        self.drag_button.clicked.connect(self.toggle_drag_mode)
        
        # State variables for crop mode
        self.crop_mode_active = False
        self.crop_start_pos = None
        self.crop_rect = None

        # Add a Crop Button
        self.crop_button = QPushButton(self)
        crop_icon = QIcon("crop.png")
        self.crop_button.setIcon(crop_icon)
        self.crop_button.setGeometry(80, 100, 60, 60)
        self.crop_button.setIconSize(self.crop_button.size())
        self.crop_button.setCheckable(True)
        self.crop_button.clicked.connect(self.toggle_crop_mode)
        
        # Add Flip Horizontal Button
        self.flip_horizontal_button = QPushButton(self)
        flip_horizontal_icon = QIcon("horizontal.png")
        self.flip_horizontal_button.setIcon(flip_horizontal_icon)
        self.flip_horizontal_button.setGeometry(10, 170, 60, 60)
        self.flip_horizontal_button.setIconSize(self.flip_horizontal_button.size())
        self.flip_horizontal_button.clicked.connect(self.flip_horizontal)

        # Add Flip Vertical Button
        self.flip_vertical_button = QPushButton(self)
        flip_vertical_icon = QIcon("vertical.png")
        self.flip_vertical_button.setIcon(flip_vertical_icon)
        self.flip_vertical_button.setGeometry(80, 170, 60, 60)
        self.flip_vertical_button.setIconSize(self.flip_vertical_button.size())
        self.flip_vertical_button.clicked.connect(self.flip_vertical)
        
        # Scale Slider
        self.scale_label = QLabel("Scale:", self)
        self.scale_label.setStyleSheet("color: white;")
        self.scale_label.setGeometry(10, 430, 120, 20)
        
        self.scale_slider = QSlider(Qt.Horizontal, self)
        self.scale_slider.setGeometry(10, 450, 140, 20)
        self.scale_slider.setRange(10, 300)  # Scaling from 10% to 300%
        self.scale_slider.setValue(100)  # Default scale is 100%
        self.scale_slider.valueChanged.connect(self.scale_selected_object)
        self.scale_slider.setEnabled(False)  # Disable until an object is selected

        # Enable mouse tracking on the canvas
        self.canvas_label.setMouseTracking(True)
        self.canvas_label.mousePressEvent = self.mouse_press_event
        self.canvas_label.mouseMoveEvent = self.mouse_move_event
        self.canvas_label.mouseReleaseEvent = self.mouse_release_event

        self.drag_start_pos = None  # Starting position for dragging
        
        # Buttons and UI for rotation
        self.rotation_button = QPushButton(self)
        rotate_icon = QIcon("rotate.png")
        self.rotation_button.setIcon(rotate_icon)
        self.rotation_button.setGeometry(10, 240, 60, 60)
        self.rotation_button.setIconSize(self.rotation_button.size())
        self.rotation_button.setCheckable(True)
        self.rotation_button.clicked.connect(self.toggle_rotation_mode)
        
        # Translation controls, lowered by 50 pixels
        self.translation_label = QLabel("Translation (x, y):", self)
        self.translation_label.setGeometry(10, 330, 120, 20)
        self.translation_label.setStyleSheet("color: white;")

        self.x_translation_slider = QSlider(Qt.Horizontal, self)
        self.x_translation_slider.setGeometry(10, 360, 120, 20)
        self.x_translation_slider.setMaximum(2000)
        self.x_translation_slider.valueChanged.connect(self.translate_image)

        self.y_translation_slider = QSlider(Qt.Horizontal, self)
        self.y_translation_slider.setGeometry(10, 390, 120, 20)
        self.y_translation_slider.setMaximum(2000)
        self.y_translation_slider.valueChanged.connect(self.translate_image)

        self.x_translation_input = QLineEdit(self)
        self.x_translation_input.setGeometry(80, 360, 50, 20)
        self.x_translation_input.setText("0")
        self.x_translation_input.returnPressed.connect(self.translate_image_from_input)

        self.y_translation_input = QLineEdit(self)
        self.y_translation_input.setGeometry(80, 390, 50, 20)
        self.y_translation_input.setText("0")
        self.y_translation_input.returnPressed.connect(self.translate_image_from_input)

        # Image Properties Button
        self.properties_button = QPushButton("Show Properties", self)
        self.properties_button.setGeometry(10, 480, 140, 40)  # Position below the slider
        self.properties_button.clicked.connect(self.show_image_properties)
        self.properties_button.hide()  # Initially hidden

        # Color Conversion Buttons
        self.rgb_button = QPushButton("RGB", self)
        self.rgb_button.setGeometry(10, 530, 60, 40)  # Position below properties button
        self.rgb_button.clicked.connect(lambda: self.convert_color("RGB"))
        self.rgb_button.hide()

        self.hsv_button = QPushButton("HSV", self)
        self.hsv_button.setGeometry(80, 530, 60, 40)
        self.hsv_button.clicked.connect(lambda: self.convert_color("HSV"))
        self.hsv_button.hide()

        self.gray_button = QPushButton("GRAY", self)
        self.gray_button.setGeometry(10, 580, 60, 40)
        self.gray_button.clicked.connect(lambda: self.convert_color("GRAY"))
        self.gray_button.hide()

        self.cie_button = QPushButton("CIE", self)
        self.cie_button.setGeometry(80, 580, 60, 40)
        self.cie_button.clicked.connect(lambda: self.convert_color("CIE"))
        self.cie_button.hide()

        self.hls_button = QPushButton("HLS", self)
        self.hls_button.setGeometry(10, 630, 60, 40)
        self.hls_button.clicked.connect(lambda: self.convert_color("HLS"))
        self.hls_button.hide()

        self.ycrcb_button = QPushButton("YCrCb", self)
        self.ycrcb_button.setGeometry(80, 630, 60, 40)
        self.ycrcb_button.clicked.connect(lambda: self.convert_color("YCrCb"))
        self.ycrcb_button.hide()
        
        self.gamma_button = QPushButton("Gamma Adjustment", self)
        self.gamma_button.setGeometry(10, 680, 140, 40)
        self.gamma_button.setVisible(False)
        self.gamma_button.clicked.connect(self.adjust_gamma)
        
        
        
        # Initialize drawing attributes
        self.is_drawing = False
        self.brush_size = 5
        self.brush_color = QColor(Qt.black)
        self.current_tool = "Brush"
        self.current_shape = None  # To store the selected shape
        self.start_point = None  # Starting point for drawing shapes

        # Drawing toggle button
        self.draw_button = QPushButton("Enable Drawing", self)
        self.draw_button.setGeometry(250, 30, 140, 40)
        self.draw_button.setCheckable(True)
        self.draw_button.clicked.connect(self.toggle_drawing_mode)

        # Brush size slider
        self.brush_size_label = QLabel("Brush Size:", self)
        self.brush_size_label.setStyleSheet("color: white;")
        self.brush_size_label.setGeometry(420, 70, 100, 20)
        self.brush_size_slider = QSlider(Qt.Horizontal, self)
        self.brush_size_slider.setGeometry(410, 90, 100, 20)
        self.brush_size_slider.setRange(1, 50)
        self.brush_size_slider.setValue(self.brush_size)
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        self.brush_size_spinbox = QSpinBox(self)
        self.brush_size_spinbox.setGeometry(520, 80, 60, 30)
        self.brush_size_spinbox.setRange(1, 50)
        self.brush_size_spinbox.setValue(self.brush_size)
        self.brush_size_spinbox.valueChanged.connect(self.update_brush_size)
        self.brush_size_slider.valueChanged.connect(self.brush_size_spinbox.setValue)

        # Tool selection dropdown
        self.tool_label = QLabel("Tool:", self)
        self.tool_label.setStyleSheet("color: white;")
        self.tool_label.setGeometry(250, 70, 50, 20)
        self.tool_dropdown = QComboBox(self)
        self.tool_dropdown.setGeometry(250, 90, 140, 30)
        self.tool_dropdown.addItems(["Brush", "Pen", "Marker", "Pencil", "Highlighter", "Eraser"])
        self.tool_dropdown.currentTextChanged.connect(self.update_tool)
        self.current_tool = "Brush"
        
        # Enable Shape Button
        self.shape_button = QPushButton("Enable Shape", self)
        self.shape_button.setGeometry(600, 30, 140, 40)
        self.shape_button.setCheckable(True)
        self.shape_button.clicked.connect(self.toggle_shape_mode)

        # Shape selection dropdown
        self.shape_dropdown = QComboBox(self)
        self.shape_dropdown.setGeometry(600, 80, 140, 40)
        self.shape_dropdown.addItems(["None", "Circle", "Rectangle", "Square", "Line", "Triangle"])
        self.shape_dropdown.currentTextChanged.connect(self.shape_tool)


        # Color picker button
        self.color_button = QPushButton(self)
        color_icon = QIcon("color.png")
        self.color_button.setIcon(color_icon)
        self.color_button.setGeometry(410, 30, 40, 40)
        self.color_button.setIconSize(self.color_button.size())
        self.color_button.clicked.connect(self.choose_color)
        
        # Save Button button
        self.save_button = QPushButton(self)
        save_icon = QIcon("savebutton.png")
        self.save_button.setIcon(save_icon)
        self.save_button.setGeometry(490, 30, 40, 40)
        self.save_button.setIconSize(self.color_button.size())
        self.save_button.clicked.connect(self.save_file)
        
        # Text tool attributes
        self.is_text_mode = False
        self.text_start_point = None
        self.current_text = ""

        # Bold, italic, and underline buttons
        self.bold_button = QPushButton("B", self)
        self.bold_button.setGeometry(960, 30, 40, 30)
        self.bold_button.setCheckable(True)
        self.bold_button.clicked.connect(self.toggle_bold)

        self.italic_button = QPushButton("I", self)
        self.italic_button.setGeometry(960, 70, 40, 30)
        self.italic_button.setCheckable(True)
        self.italic_button.clicked.connect(self.toggle_italic)

        self.underline_button = QPushButton("U", self)
        self.underline_button.setGeometry(910, 70, 40, 30)
        self.underline_button.setCheckable(True)
        self.underline_button.clicked.connect(self.toggle_underline)

        # Font size spinbox
        self.font_size_spinbox = QSpinBox(self)
        self.font_size_spinbox.setGeometry(900, 30, 50, 30)
        self.font_size_spinbox.setRange(8, 72)
        self.font_size_spinbox.setValue(12)

        # Font style dropdown
        self.font_style_dropdown = QComboBox(self)
        self.font_style_dropdown.setGeometry(750, 80, 150, 40)
        self.font_style_dropdown.addItems(["Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma"])

        # Enable text mode button
        self.text_button = QPushButton("Enable Text", self)
        self.text_button.setGeometry(750, 30, 140, 40)
        self.text_button.setCheckable(True)
        self.text_button.clicked.connect(self.toggle_text_mode)

        # Default text style attributes
        self.text_bold = False
        self.text_italic = False
        self.text_underline = False

        # Remove the slider and directly connect the spinbox
        self.rotation_spinbox = QSpinBox(self)
        self.rotation_spinbox.setGeometry(80, 260, 60, 20)
        self.rotation_spinbox.setRange(-180, 180)
        self.rotation_spinbox.valueChanged.connect(self.set_rotation_from_spinbox)
        
        # Add Merge Images button
        self.merge_button = QPushButton("Merge Images", self)
        self.merge_button.setGeometry(1010, 80, 140, 40)
        self.merge_button.clicked.connect(self.open_merge_dialog)
        
        # Thumbnail Panel
        self.thumbnail_panel = QListWidget(self)
        self.thumbnail_panel.setGeometry(1450, 150, 180, 800)  # Adjust size and position as needed
        self.thumbnail_panel.setViewMode(QListWidget.IconMode)
        self.thumbnail_panel.setIconSize(QSize(100, 100))  # Set thumbnail size
        self.thumbnail_panel.setResizeMode(QListWidget.Adjust)
        self.thumbnail_panel.itemClicked.connect(self.load_thumbnail_image)
        
        # Zoom In Button
        self.zoom_in_button = QPushButton(self)
        zoom_in_icon = QIcon("zoom-in.png")
        self.zoom_in_button.setIcon(zoom_in_icon)
        self.zoom_in_button.setIconSize(self.zoom_in_button.size())
        self.zoom_in_button.setGeometry(1170, 50, 60, 60)  # Adjust position
        self.zoom_in_button.clicked.connect(self.zoomin_canvas)

        # Zoom Out Button
        self.zoom_out_button = QPushButton(self)
        zoom_out_icon = QIcon("zoom-out.png")
        self.zoom_out_button.setIcon(zoom_out_icon)
        self.zoom_out_button.setIconSize(self.zoom_out_button.size())
        self.zoom_out_button.setGeometry(1240, 50, 60, 60)  # Adjust position
        self.zoom_out_button.clicked.connect(self.zoomout_canvas)

        # Reset Canvas Button
        self.reset_canvas_button = QPushButton(self)
        reset_icon = QIcon("reset.png")
        self.reset_canvas_button.setIcon(reset_icon)
        self.reset_canvas_button.setIconSize(self.reset_canvas_button.size())
        self.reset_canvas_button.setGeometry(1310, 50, 60, 60)  # Adjust position
        self.reset_canvas_button.clicked.connect(self.reset_canvas)
        
        # Buttons for selected object actions
        self.edit_button = QPushButton(self)
        edit_icon = QIcon("fill.png")
        self.edit_button.setIcon(edit_icon)
        self.edit_button.setIconSize(self.edit_button.size())
        self.edit_button.setGeometry(1380, 50, 60, 60)
        self.edit_button.clicked.connect(self.edit_selected_object)
        
        self.delete_button = QPushButton(self)
        delete_icon = QIcon("bin.png")
        self.delete_button.setIcon(delete_icon)
        self.delete_button.setIconSize(self.delete_button.size())
        self.delete_button.setGeometry(1450, 50, 60, 60)
        self.delete_button.clicked.connect(self.delete_selected_object)
        
        # Add a button to display the original image
        self.show_original_button = QPushButton("Show Original", self)
        self.show_original_button.setGeometry(1520, 60, 140, 40)  # Adjust position as needed
        self.show_original_button.clicked.connect(self.show_original_image)

        # Add a button for displaying the histogram
        self.histogram_button = QPushButton("Show Histogram", self)
        self.histogram_button.setGeometry(10, 730, 140, 40)  # Adjust position as needed
        self.histogram_button.clicked.connect(self.show_histogram)
        self.histogram_button.setVisible(False)  # Initially hidden
        
        # Add the bitwise dropdown button
        self.bitwise_dropdown = QComboBox(self)
        self.bitwise_dropdown.setGeometry(10, 780, 140, 40)  # Adjust position below the histogram button
        self.bitwise_dropdown.addItems(["Select Operation", "Bitwise AND", "Bitwise OR", "Bitwise XOR"])
        self.bitwise_dropdown.currentTextChanged.connect(self.perform_bitwise_operation)
        self.bitwise_dropdown.setVisible(False)  # Initially hidden
        
        # Add Negative Image Button
        self.negative_image_button = QPushButton("Negative Image", self)
        self.negative_image_button.setGeometry(10, 830, 140, 40)  # Adjust position as needed
        self.negative_image_button.clicked.connect(self.negative_image)
        self.negative_image_button.setVisible(False)  # Initially hidden


    def create_canvas(self, width, height):
        # Create a blank white canvas using QPixmap
        self.canvas = QPixmap(width, height)
        self.canvas.fill(Qt.white)
        self.canvas_label.setPixmap(self.canvas)
        
    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        save_action = QAction("Save File", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        load_action = QAction("Load File", self)
        load_action.triggered.connect(self.load_file)
        file_menu.addAction(load_action)
        
        # Export Image action
        export_action = QAction("Export as PNG", self)
        export_action.triggered.connect(self.export_as_image)
        file_menu.addAction(export_action)
        
        view_menu = menubar.addMenu("View")
        
        # Thumbnail toggle
        thumbnail_action = QAction("Toggle Thumbnails", self, checkable=True)
        thumbnail_action.triggered.connect(self.toggle_thumbnail_panel)
        view_menu.addAction(thumbnail_action)
        
        # Mini Canvas toggle
        mini_canvas_action = QAction("Toggle Mini Canvas", self, checkable=True)
        mini_canvas_action.triggered.connect(self.toggle_mini_canvas)
        view_menu.addAction(mini_canvas_action)
        
        zoom_in_action = QAction("Zoom In Canvas", self)
        zoom_in_action.triggered.connect(self.zoomin_canvas)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out Canvas", self)
        zoom_out_action.triggered.connect(self.zoomout_canvas)
        view_menu.addAction(zoom_out_action)

        reset_canvas_action = QAction("Reset Canvas", self)
        reset_canvas_action.triggered.connect(self.reset_canvas)
        view_menu.addAction(reset_canvas_action)
        
        
    def setup_ui(self):
        # Add Change Pixel Color button
        self.change_pixel_color_button.setCheckable(True)
        self.change_pixel_color_button.toggled.connect(self.toggle_change_color_mode)


        # Add a Color Picker button
        self.color_picker_button = QPushButton("Select Color", self)
        self.color_picker_button.setGeometry(900, 120, 140, 40)
        self.color_picker_button.clicked.connect(self.choose_color)

    def save_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Canvas File", "", "Canvas Files (*.canvas);;All Files (*)", options=options
        )
        if file_path:
            try:
                # Convert QPixmap objects to image byte arrays
                objects_data = []
                for obj in self.objects:
                    pixmap_bytes = QByteArray()
                    buffer = QBuffer(pixmap_bytes)
                    buffer.open(QIODevice.WriteOnly)
                    obj['pixmap'].save(buffer, "PNG")  # Save QPixmap as PNG
                    objects_data.append({
                        'pixmap': pixmap_bytes.data(),
                        'x': obj['x'],
                        'y': obj['y'],
                        'rect': (obj['rect'].x(), obj['rect'].y(), obj['rect'].width(), obj['rect'].height())
                    })

                # Serialize other data
                elements_data = []
                for element in self.elements:
                    if element['type'] == 'drawing':
                        pen_data = {
                            'color': element['pen'].color().getRgb(),
                            'width': element['pen'].width(),
                        }
                        path_data = [(point.x(), point.y()) for point in element['path'].toFillPolygon()]
                        elements_data.append({'type': 'drawing', 'pen': pen_data, 'path': path_data})
                    elif element['type'] == 'shape':
                        pen_data = {
                            'color': element['pen'].color().getRgb(),
                            'width': element['pen'].width(),
                        }
                        path_data = [(point.x(), point.y()) for point in element['path'].toFillPolygon()]
                        elements_data.append({'type': 'shape', 'pen': pen_data, 'path': path_data})
                    elif element['type'] == 'text':
                        font_data = {
                            'family': element['font'].family(),
                            'size': element['font'].pointSize(),
                            'bold': element['font'].bold(),
                            'italic': element['font'].italic(),
                            'underline': element['font'].underline(),
                        }
                        pen_data = {'color': element['pen'].color().getRgb()}
                        elements_data.append({
                            'type': 'text',
                            'font': font_data,
                            'pen': pen_data,
                            'position': (element['position'].x(), element['position'].y()),
                            'text': element['text'],
                        })

                data = {
                    'elements': elements_data,
                    'objects': objects_data,
                    'canvas_width': self.canvas.width(),
                    'canvas_height': self.canvas.height(),
                }

                # Save to file
                with open(file_path, 'wb') as file:
                    pickle.dump(data, file)
                print(f"Canvas saved to {file_path}")
            except Exception as e:
                print(f"Failed to save file: {e}")

    def load_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Canvas File", "", "Canvas Files (*.canvas);;All Files (*)", options=options
        )
        if file_path:
            try:
                with open(file_path, 'rb') as file:
                    data = pickle.load(file)

                    # Recreate elements from saved data
                    self.elements = []
                    for element_data in data.get('elements', []):
                        if element_data['type'] == 'drawing':
                            pen = QPen()
                            color = QColor()
                            color.setRgb(*element_data['pen']['color'])
                            pen.setColor(color)
                            pen.setWidth(element_data['pen']['width'])

                            path = QPainterPath()
                            for point in element_data['path']:
                                path.lineTo(QPointF(point[0], point[1]))

                            self.elements.append({'type': 'drawing', 'pen': pen, 'path': path})
                        elif element_data['type'] == 'shape':
                            pen = QPen()
                            color = QColor()
                            color.setRgb(*element_data['pen']['color'])
                            pen.setColor(color)
                            pen.setWidth(element_data['pen']['width'])

                            path = QPainterPath()
                            for point in element_data['path']:
                                path.lineTo(QPointF(point[0], point[1]))

                            self.elements.append({'type': 'shape', 'pen': pen, 'path': path})
                        elif element_data['type'] == 'text':
                            font = QFont()
                            font.setFamily(element_data['font']['family'])
                            font.setPointSize(element_data['font']['size'])
                            font.setBold(element_data['font']['bold'])
                            font.setItalic(element_data['font']['italic'])
                            font.setUnderline(element_data['font']['underline'])

                            pen = QPen()
                            color = QColor()
                            color.setRgb(*element_data['pen']['color'])
                            pen.setColor(color)

                            self.elements.append({
                                'type': 'text',
                                'font': font,
                                'pen': pen,
                                'position': QPointF(element_data['position'][0], element_data['position'][1]),
                                'text': element_data['text'],
                            })

                    # Recreate objects from saved data
                    self.objects = []
                    for obj_data in data.get('objects', []):
                        pixmap_bytes = obj_data['pixmap']
                        pixmap = QPixmap()
                        buffer = QBuffer()
                        buffer.setData(pixmap_bytes)
                        buffer.open(QIODevice.ReadOnly)
                        pixmap.loadFromData(buffer.data(), "PNG")
                        rect_data = obj_data['rect']
                        self.objects.append({
                            'pixmap': pixmap,
                            'x': obj_data['x'],
                            'y': obj_data['y'],
                            'rect': QRect(rect_data[0], rect_data[1], rect_data[2], rect_data[3]),
                        })

                    # Reinitialize canvas
                    canvas_width = data.get('canvas_width', 800)
                    canvas_height = data.get('canvas_height', 600)
                    self.create_canvas(canvas_width, canvas_height)
                    self.redraw_canvas()

                print(f"Canvas loaded from {file_path}")
            except Exception as e:
                print(f"Failed to load file: {e}")
                
    def add_thumbnail(self, pixmap, label="Image"):
        # Add a thumbnail for the uploaded or merged image
        thumbnail_item = QListWidgetItem(label)
        scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        thumbnail_item.setIcon(QIcon(scaled_pixmap))
        self.thumbnail_panel.addItem(thumbnail_item)
        
    def load_thumbnail_image(self, item):
    # Select the corresponding image when a thumbnail is clicked
        index = self.thumbnail_panel.row(item)
        if index < len(self.objects):
            self.selected_object = self.objects[index]
            self.redraw_canvas()  # Highlight or update the canvas to show the selected image

    def toggle_mini_canvas(self):
        if hasattr(self, "mini_canvas_dialog") and self.mini_canvas_dialog.isVisible():
            self.mini_canvas_dialog.close()
            return

        # Create a mini canvas dialog
        self.mini_canvas_dialog = QDialog(self)
        self.mini_canvas_dialog.setWindowTitle("Canvas Overview")
        self.mini_canvas_dialog.setGeometry(200, 200, 500, 400)  # Initial size

        # Use a fixed size for the QLabel within the dialog
        self.mini_canvas_label = QLabel(self.mini_canvas_dialog)
        self.mini_canvas_label.setAlignment(Qt.AlignCenter)

        # Create a layout and add the QLabel
        layout = QVBoxLayout(self.mini_canvas_dialog)
        layout.addWidget(self.mini_canvas_label)
        self.mini_canvas_dialog.setLayout(layout)

        # Connect resize event
        self.mini_canvas_dialog.resizeEvent = self.resize_mini_canvas

        # Initial update of the mini canvas
        self.update_mini_canvas()

        self.mini_canvas_dialog.show()
        
    def resize_mini_canvas(self, event):
        # Ensure the QLabel size matches the resized dialog
        if hasattr(self, "mini_canvas_label"):
            self.update_mini_canvas()
      
    def update_mini_canvas(self):
        if hasattr(self, "mini_canvas_label") and hasattr(self, "mini_canvas_dialog"):
            # Get the available size of the QLabel in the dialog
            label_size = self.mini_canvas_label.size()
            
            # Scale the canvas to fit the QLabel while maintaining aspect ratio
            scaled_pixmap = self.canvas.scaled(
                label_size.width(),
                label_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            
            # Set the scaled pixmap to the QLabel
            self.mini_canvas_label.setPixmap(scaled_pixmap)

                
    def export_as_image(self):
        # Open file dialog to get the save location
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as Image", "", "PNG Files (*.png);;All Files (*)", options=options
        )
        if file_path:
            if not file_path.endswith(".png"):
                file_path += ".png"  # Ensure the file has a .png extension
            try:
                # Save the current canvas as an image
                self.canvas.save(file_path, "PNG")
                print(f"Canvas exported as PNG to {file_path}")
            except Exception as e:
                print(f"Failed to export as PNG: {e}")
                
    def open_merge_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Images to Merge")
        dialog.setFixedSize(300, 200)

        layout = QVBoxLayout(dialog)

        # List selected objects
        selected_objects_list = QListWidget(dialog)
        for obj in self.objects:
            item = QListWidgetItem(f"Image {self.objects.index(obj) + 1}")
            item.setCheckState(Qt.Unchecked)
            selected_objects_list.addItem(item)
        layout.addWidget(selected_objects_list)

        # Add options for merge orientation
        orientation_label = QLabel("Merge Orientation:", dialog)
        layout.addWidget(orientation_label)

        orientation_dropdown = QComboBox(dialog)
        orientation_dropdown.addItems(["Side by Side", "Up and Down"])
        layout.addWidget(orientation_dropdown)

        # Add OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def handle_ok():
            selected_indices = [
                i for i in range(selected_objects_list.count())
                if selected_objects_list.item(i).checkState() == Qt.Checked
            ]
            selected_objects = [self.objects[i] for i in selected_indices]

            if not selected_objects:
                QMessageBox.warning(self, "Selection Error", "Please select at least two images to merge.")
                return

            merge_orientation = orientation_dropdown.currentText()
            self.merge_images(selected_objects, merge_orientation)
            dialog.accept()

        ok_button.clicked.connect(handle_ok)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def merge_images(self, selected_objects, orientation):
        # Extract image data from selected objects
        cv_images = []
        for obj in selected_objects:
            qt_image = obj['pixmap'].toImage()
            qt_image = qt_image.convertToFormat(QImage.Format_RGB32)
            width, height = qt_image.width(), qt_image.height()
            ptr = qt_image.bits()
            ptr.setsize(qt_image.byteCount())
            cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]  # Extract RGB channels (ignore alpha)
            cv_images.append(cv_image)

        # Normalize sizes based on orientation
        if orientation == "Side by Side":
            target_height = min(img.shape[0] for img in cv_images)
            resized_images = [
                cv2.resize(img, (int(img.shape[1] * target_height / img.shape[0]), target_height)) for img in cv_images
            ]
            try:
                merged_image = cv2.hconcat(resized_images)  # Merge horizontally
            except cv2.error as e:
                QMessageBox.critical(self, "Merge Error", f"Failed to merge images: {e}")
                return
        elif orientation == "Up and Down":
            target_width = min(img.shape[1] for img in cv_images)
            resized_images = [
                cv2.resize(img, (target_width, int(img.shape[0] * target_width / img.shape[1]))) for img in cv_images
            ]
            try:
                merged_image = cv2.vconcat(resized_images)  # Merge vertically
            except cv2.error as e:
                QMessageBox.critical(self, "Merge Error", f"Failed to merge images: {e}")
                return

        # Convert BGR (OpenCV) to RGB (PyQt)
        merged_image = cv2.cvtColor(merged_image, cv2.COLOR_BGR2RGB)

        # Convert back to QPixmap
        h, w, ch = merged_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(merged_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        # Add the merged image to the canvas
        self.objects.append({
            'pixmap': pixmap,
            'original_pixmap': pixmap,
            'x': 50,
            'y': 50,
            'rect': QRect(50, 50, pixmap.width(), pixmap.height())
        })
        
        self.add_thumbnail(pixmap, "Merged Image")
        self.redraw_canvas()
        
    def toggle_thumbnail_panel(self, checked):
        self.thumbnail_panel.setVisible(checked)

    def update_scroll_area(self):
        """Update the scroll area dimensions."""
        max_width = max(1300, self.canvas_label.width())
        max_height = max(900, self.canvas_label.height())
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setGeometry(200, 150, max_width+100, max_height+100)



    def zoomin_canvas(self):
        """Zoom in the entire canvas by increasing its scale."""
        self.canvas_scale *= 1.1  # Increase scale by 10%
        self.scale_canvas()

    def zoomout_canvas(self):
        """Zoom out the entire canvas by decreasing its scale."""
        self.canvas_scale /= 1.1  # Decrease scale by 10%
        self.scale_canvas()

    def reset_canvas(self):
        """Reset the canvas to its original size and scale."""
        self.canvas_scale = 1.0  # Reset scale
        self.canvas = self.original_canvas.copy()  # Restore the original canvas
        self.canvas_label.setPixmap(self.canvas)  # Update the display
        self.redraw_canvas()  # Refresh the canvas with all objects

    def scale_canvas(self):
        """Scale the canvas and all elements."""
        # Scale the canvas size
        new_width = int(self.original_canvas.width() * self.canvas_scale)
        new_height = int(self.original_canvas.height() * self.canvas_scale)

        # Scale the canvas pixmap
        scaled_canvas = self.original_canvas.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.canvas = scaled_canvas

        # Adjust canvas label size
        self.canvas_label.setPixmap(self.canvas)
        self.canvas_label.resize(new_width, new_height)

        # Scale all objects, shapes, and drawings
        for obj in self.objects:
            obj_width = int(obj['original_pixmap'].width() * self.canvas_scale)
            obj_height = int(obj['original_pixmap'].height() * self.canvas_scale)
            obj['pixmap'] = obj['original_pixmap'].scaled(obj_width, obj_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            obj['x'] = int(obj['x'] * self.canvas_scale)
            obj['y'] = int(obj['y'] * self.canvas_scale)
            obj['rect'] = QRect(obj['x'], obj['y'], obj_width, obj_height)

        # Scale shapes
        for shape in self.elements:
            if shape['type'] == 'shape':
                scaled_path = QPainterPath()
                for point in shape['path'].toFillPolygon():
                    scaled_point = QPointF(point.x() * self.canvas_scale, point.y() * self.canvas_scale)
                    if not scaled_path.elementCount():
                        scaled_path.moveTo(scaled_point)
                    else:
                        scaled_path.lineTo(scaled_point)
                shape['path'] = scaled_path

        # Scale text
        for text_element in self.elements:
            if text_element['type'] == 'text':
                text_element['position'] = QPointF(
                    text_element['position'].x() * self.canvas_scale,
                    text_element['position'].y() * self.canvas_scale,
                )
                font = text_element['font']
                font.setPointSize(int(font.pointSize() * self.canvas_scale))
                text_element['font'] = font

        self.redraw_canvas()


    def upload_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select an Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)", options=options
        )
        if file_path:
            image = cv2.imread(file_path)
            if image is not None:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = image.shape
                bytes_per_line = ch * w
                qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)

                scaled_image = QPixmap.fromImage(qt_image).scaled(
                    self.canvas_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

                # Store the image and its position
                # Store the image, original pixmap, and position
                self.objects.append({
                    'pixmap': scaled_image,
                    'original_pixmap': scaled_image,  # Store the original pixmap for reference
                    'x': 50,
                    'y': 50,
                    'rect': QRect(50, 50, scaled_image.width(), scaled_image.height())  # Store position and size
                })
                # Add thumbnail
                self.add_thumbnail(scaled_image, f"Image {len(self.objects)}")

                # Redraw canvas
                self.redraw_canvas()
                
    def toggle_rotation_mode(self):
        self.rotate_mode_active = self.rotation_button.isChecked()

    def set_rotation_from_slider(self, value):
        self.rotation_spinbox.setValue(value)
        self.apply_rotation(value)

    def set_rotation_from_spinbox(self, value):
        self.apply_rotation(value)


    def apply_rotation(self, angle):
        if self.selected_object:
            # Update the rotation angle for the selected object
            self.selected_object['rotation'] = angle
            self.redraw_canvas()
            
    def scale_selected_object(self):
        if self.selected_object:
            scale_percent = self.scale_slider.value() / 100.0  # Slider value as a percentage

            original_pixmap = self.selected_object['original_pixmap']
            new_width = int(original_pixmap.width() * scale_percent)
            new_height = int(original_pixmap.height() * scale_percent)

            # Create a scaled version of the original pixmap
            scaled_pixmap = original_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # Apply any color transformation
            if 'color_mode' in self.selected_object:
                scaled_pixmap = self.apply_color_transformation(scaled_pixmap, self.selected_object['color_mode'])

            # Update the pixmap with the scaled and transformed version
            self.selected_object['pixmap'] = scaled_pixmap
            # Update the rectangle to match the new size
            self.selected_object['rect'] = QRect(self.selected_object['rect'].x(), self.selected_object['rect'].y(), new_width, new_height)

            self.redraw_canvas()
            
    def translate_image(self):
        if self.selected_object:
            # Get values from sliders
            x = self.x_translation_slider.value()
            y = self.y_translation_slider.value()

            # Update the selected object's position
            self.selected_object['x'] = x
            self.selected_object['y'] = y

            # Update the QRect associated with the object
            self.selected_object['rect'].moveTo(x, y)

            # Redraw the canvas to reflect the changes
            self.redraw_canvas()

    def translate_image_from_input(self):
        if self.selected_object:
            try:
                # Get values from input fields
                x = int(self.x_translation_input.text())
                y = int(self.y_translation_input.text())
            except ValueError:
                print("Invalid input for translation. Please enter numeric values.")
                return  # Ignore invalid input

            # Update sliders to reflect input values
            self.x_translation_slider.setValue(x)
            self.y_translation_slider.setValue(y)

            # Update the object's position in `self.objects`
            for obj in self.objects:
                if obj == self.selected_object:  # Match the selected object
                    obj['x'] = x
                    obj['y'] = y
                    obj['rect'].moveTo(x, y)  # Update the QRect position
                    break

            # Redraw the canvas with the updated position
            self.redraw_canvas()


    def redraw_canvas(self):
        self.create_canvas(self.canvas.width(), self.canvas.height())
        painter = QPainter(self.canvas)
        
        # Draw all persistent elements
        for element in self.elements:
            if element['type'] == 'drawing':
                painter.setPen(element['pen'])
                painter.drawPath(element['path'])
            elif element['type'] == 'shape':
                painter.setPen(element['pen'])
                painter.drawPath(element['path'])
            elif element['type'] == 'text':
                painter.setFont(element['font'])
                painter.setPen(element['pen'])
                painter.drawText(element['position'], element['text'])

        # Draw all objects
        for obj in self.objects:
            transform = QTransform()
            transform.translate(obj['x'] + obj['pixmap'].width() / 2, obj['y'] + obj['pixmap'].height() / 2)
            transform.rotate(obj.get('rotation', 0))
            transform.translate(-obj['pixmap'].width() / 2, -obj['pixmap'].height() / 2)
            rotated_pixmap = obj['pixmap'].transformed(transform, Qt.SmoothTransformation)
            painter.drawPixmap(obj['x'], obj['y'], rotated_pixmap)

        if self.selected_object:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.drawRect(self.selected_object['rect'])

        # Draw the crop rectangle, if defined
        if self.crop_mode_active and self.crop_rect:
            painter.setPen(Qt.red)
            painter.drawRect(self.crop_rect)

        painter.end()
        self.canvas_label.setPixmap(self.canvas)
        
        # Update the mini canvas if open
        self.update_mini_canvas()

    def flip_horizontal(self):
        if self.selected_object:
            for obj in self.objects:
                if obj == self.selected_object:
                    # Flip the pixmap horizontally
                    flipped_pixmap = obj['pixmap'].transformed(QTransform().scale(-1, 1))
                    obj['pixmap'] = flipped_pixmap  # Update the object's pixmap
                    obj['original_pixmap'] = flipped_pixmap  # Update original_pixmap too if needed
                    break
            self.redraw_canvas()

    def flip_vertical(self):
        if self.selected_object:
            for obj in self.objects:
                if obj == self.selected_object:
                    # Flip the pixmap vertically
                    flipped_pixmap = obj['pixmap'].transformed(QTransform().scale(1, -1))
                    obj['pixmap'] = flipped_pixmap  # Update the object's pixmap
                    obj['original_pixmap'] = flipped_pixmap  # Update original_pixmap too if needed
                    break
            self.redraw_canvas()
            
    def toggle_drag_mode(self):
        self.drag_mode_active = self.drag_button.isChecked()
        self.redraw_canvas()
        
    def toggle_crop_mode(self):
        self.crop_mode_active = self.crop_button.isChecked()
        if not self.crop_mode_active:
            self.crop_rect = None  # Clear the crop rectangle if exiting crop mode
        self.redraw_canvas()
        
    def convert_color(self, color_mode):
        if not self.selected_object:
            return

        # Update the color mode for the selected object
        self.selected_object['color_mode'] = color_mode

        # Always start from the original pixmap
        original_pixmap = self.selected_object['original_pixmap']
        qt_image = original_pixmap.toImage()

        # Ensure QImage is in the correct format
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)

        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]

        # Convert color based on mode
        if color_mode == "RGB":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        elif color_mode == "HSV":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        elif color_mode == "GRAY":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            converted_image = cv2.cvtColor(converted_image, cv2.COLOR_GRAY2BGR)
        elif color_mode == "CIE":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2Lab)
        elif color_mode == "HLS":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HLS)
        elif color_mode == "YCrCb":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2YCrCb)
        else:
            return  # Invalid mode

        # Convert back to QPixmap
        h, w, ch = converted_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(converted_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        new_pixmap = QPixmap.fromImage(qt_image)

        # Scale the converted pixmap if scaling is active
        scale_percent = self.scale_slider.value() / 100.0  # Current scale
        scaled_pixmap = new_pixmap.scaled(
            int(new_pixmap.width() * scale_percent),
            int(new_pixmap.height() * scale_percent),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Update the selected object's pixmap and redraw
        self.selected_object['pixmap'] = scaled_pixmap
        self.redraw_canvas()

    def apply_color_transformation(self, pixmap, color_mode):
        qt_image = pixmap.toImage()
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)

        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]

        # Apply color transformation
        if color_mode == "RGB":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        elif color_mode == "HSV":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        elif color_mode == "GRAY":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            converted_image = cv2.cvtColor(converted_image, cv2.COLOR_GRAY2BGR)
        elif color_mode == "CIE":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2Lab)
        elif color_mode == "HLS":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HLS)
        elif color_mode == "YCrCb":
            converted_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2YCrCb)
        else:
            return pixmap  # Return unchanged if no valid color mode

        # Convert back to QPixmap
        h, w, ch = converted_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(converted_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)
        
    def adjust_gamma(self):
        if not self.selected_object:
            return

        # Prompt user for gamma value
        gamma, ok = QInputDialog.getDouble(self, "Gamma Adjustment", "Enter Gamma Value (e.g., 0.1 - 5.0):", 1.0, 0.1, 5.0, 2)
        if not ok:
            return  # User canceled

        # Get the original pixmap
        original_pixmap = self.selected_object['original_pixmap']
        qt_image = original_pixmap.toImage()

        # Convert QImage to OpenCV format
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)
        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]  # Extract RGB channels

        # Apply gamma correction
        inv_gamma = 1.0 / gamma
        table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype("uint8")
        gamma_corrected_image = cv2.LUT(cv_image, table)

        # Convert back from BGR to RGB for display
        gamma_corrected_image = cv2.cvtColor(gamma_corrected_image, cv2.COLOR_BGR2RGB)

        # Convert back to QPixmap
        h, w, ch = gamma_corrected_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(gamma_corrected_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        new_pixmap = QPixmap.fromImage(qt_image)

        # Update the selected object's pixmap and redraw
        self.selected_object['pixmap'] = new_pixmap
        self.redraw_canvas()
        
    def perform_bitwise_operation(self, operation):
        if not self.selected_object or operation == "Select Operation":
            return

        # Get the pixmap of the selected object
        pixmap = self.selected_object['pixmap']
        qt_image = pixmap.toImage()

        # Convert QImage to OpenCV format
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)
        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]  # Extract RGB channels

        # Prepare a grayscale version for the bitwise operation
        gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Perform the selected bitwise operation
        if operation == "Bitwise AND":
            result_image = cv2.bitwise_and(cv_image, cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR))
        elif operation == "Bitwise OR":
            result_image = cv2.bitwise_or(cv_image, cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR))
        elif operation == "Bitwise XOR":
            result_image = cv2.bitwise_xor(cv_image, cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR))
        else:
            return

        # Convert the result back to QPixmap
        result_image = cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB)
        h, w, ch = result_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(result_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        result_pixmap = QPixmap.fromImage(qt_image)

        # Update the selected object's pixmap and redraw
        self.selected_object['pixmap'] = result_pixmap
        self.redraw_canvas()
        
    def negative_image(self):
        if not self.selected_object:
            QMessageBox.warning(self, "Selection Error", "No object selected to apply the negative effect.")
            return

        # Get the pixmap of the selected object
        pixmap = self.selected_object['pixmap']
        qt_image = pixmap.toImage()

        # Convert QImage to OpenCV format
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)
        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]  # Extract RGB channels

        # Apply the negative effect
        cv_image_negative = 255 - cv_image

        # Convert back to QPixmap
        cv_image_negative = cv2.cvtColor(cv_image_negative, cv2.COLOR_BGR2RGB)
        h, w, ch = cv_image_negative.shape
        bytes_per_line = ch * w
        qt_image_negative = QImage(cv_image_negative.data, w, h, bytes_per_line, QImage.Format_RGB888)
        negative_pixmap = QPixmap.fromImage(qt_image_negative)

        # Update the pixmap of the selected object
        self.selected_object['pixmap'] = negative_pixmap
        self.redraw_canvas()

        
    def show_original_image(self):
        if self.selected_object:
            # Retrieve the original pixmap
            original_pixmap = self.selected_object.get('original_pixmap', None)
            if original_pixmap:
                # Create a dialog to display the image
                dialog = QDialog(self)
                dialog.setWindowTitle("Image")
                dialog.setFixedSize(original_pixmap.width() + 20, original_pixmap.height() + 20)
                
                layout = QVBoxLayout(dialog)
                label = QLabel(dialog)
                label.setPixmap(original_pixmap)
                layout.addWidget(label)

                # Add OK button to close the dialog
                ok_button = QPushButton("OK", dialog)
                ok_button.clicked.connect(dialog.accept)
                layout.addWidget(ok_button)

                dialog.setLayout(layout)
                dialog.exec_()
        
    def show_image_properties(self):
        if self.selected_object:
            pixmap = self.selected_object['pixmap']  # Get the selected object's pixmap
            file_name = "Unknown"  # If you save the file name during upload, fetch it here
            image_size = f"{pixmap.width()} x {pixmap.height()} px"
            image_resolution = "N/A"  # You can add logic to extract resolution if available
            image_type = "RGB"  # Assuming RGB for uploaded images

            # Show details in a message box
            from PyQt5.QtWidgets import QMessageBox
            details = (
                f"File Name: {file_name}\n"
                f"Image Size: {image_size}\n"
                f"Resolution: {image_resolution}\n"
                f"Image Type: {image_type}"
            )
            QMessageBox.information(self, "Image Properties", details)

    def mouse_press_event(self, event):
        if self.is_drawing and event.button() == Qt.LeftButton:
            self.last_point = event.pos()
        elif event.button() == Qt.MiddleButton:  # Use middle mouse button for panning
            self.scroll_area.setCursor(Qt.ClosedHandCursor)
            self.pan_start_pos = event.pos()
        elif self.change_color_mode and event.button() == Qt.LeftButton:
            self.apply_color_to_pixel_group(event.pos())
            self.change_color_mode = False  # Exit change color mode
            self.change_pixel_color_button.setChecked(False)
            self.change_pixel_color_button.setStyleSheet("")
        elif self.is_shape_mode and event.button() == Qt.LeftButton:
            self.start_point = event.pos()
        elif self.is_text_mode and event.button() == Qt.LeftButton:
            # Set the starting point for text input
            self.text_start_point = event.pos()
            self.current_text = ""  # Reset current text
            self.update_text_preview()
        elif self.crop_mode_active and event.button() == Qt.LeftButton:
            # Start defining the crop rectangle
            self.crop_start_pos = event.pos()
            self.crop_rect = QRect(self.crop_start_pos, QSize())
        elif self.drag_mode_active and event.button() == Qt.LeftButton:
            # Start dragging if an object is selected
            click_pos = event.pos()
            for obj in self.objects:
                rect = obj['rect']
                if rect.contains(click_pos):
                    self.selected_object = obj  # Select the object
                    self.scale_slider.setEnabled(True)  # Enable scale slider
                    self.drag_start_pos = event.pos()
                    return
        elif self.rotate_mode_active:
                for obj in self.objects:
                    if obj['rect'].contains(click_pos):
                        self.selected_object = obj
                        self.rotation_start_angle = self.rotation_spinbox.value()
                        self.redraw_canvas()
                        return

        elif event.button() == Qt.RightButton:
            click_pos = event.pos()

            # Right-click to select or deselect an object
            for obj in self.objects:
                if obj['rect'].contains(click_pos):
                    self.selected_object = obj if self.selected_object != obj else None
                    self.scale_slider.setEnabled(bool(self.selected_object))  # Enable or disable scaling
                    self.properties_button.setVisible(bool(self.selected_object))  # Show or hide the button
                    
                    # Show or hide color conversion buttons
                    is_selected = bool(self.selected_object)
                    self.rgb_button.setVisible(is_selected)
                    self.hsv_button.setVisible(is_selected)
                    self.gray_button.setVisible(is_selected)
                    self.cie_button.setVisible(is_selected)
                    self.hls_button.setVisible(is_selected)
                    self.ycrcb_button.setVisible(is_selected)
                    
                    self.gamma_button.setVisible(is_selected)
                    self.histogram_button.setVisible(is_selected)
                    self.bitwise_dropdown.setVisible(is_selected)
                    self.negative_image_button.setVisible(is_selected)
                    
                    
                    self.redraw_canvas()
                    return
            self.selected_object = None  # Deselect if no object was clicked
            self.redraw_canvas()

            # If no object is clicked, deselect everything
            self.selected_object = None
            self.scale_slider.setEnabled(False)
            self.properties_button.hide() 
            self.rgb_button.hide()
            self.hsv_button.hide()
            self.gray_button.hide()
            self.cie_button.hide()
            self.hls_button.hide()
            self.ycrcb_button.hide()
            self.gamma_button.hide()
            self.histogram_button.hide()
            self.bitwise_dropdown.hide()
            self.negative_image_button.hide()
            
            self.redraw_canvas()
            
    def edit_selected_object(self):
        if self.selected_object:
            color = QColorDialog.getColor(initial=self.selected_color, parent=self, title="Select New Color")
            if color.isValid():
                painter = QPainter(self.selected_object['pixmap'])
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawRect(self.selected_object['pixmap'].rect())
                painter.end()
                self.redraw_canvas()
                
    def delete_selected_object(self):
        if self.selected_object:
            self.objects.remove(self.selected_object)
            self.selected_object = None
            
            self.redraw_canvas()

    def toggle_change_color_mode(self, checked):
        self.change_color_mode = checked
        if checked:
            self.change_pixel_color_button.setStyleSheet("background-color: green;")
        else:
            self.change_pixel_color_button.setStyleSheet("")
            
    def apply_color_to_pixel_group(self, start_pos):
        # Get the canvas QImage
        qt_image = self.canvas.toImage()
        width, height = qt_image.width(), qt_image.height()

        # Convert the start position to QImage coordinates
        x, y = start_pos.x(), start_pos.y()

        # Get the color of the clicked pixel
        target_color = qt_image.pixelColor(x, y)

        # Open the color picker dialog
        new_color = QColorDialog.getColor(initial=self.selected_color, parent=self, title="Choose New Color")
        if not new_color.isValid():
            return  # User canceled the color selection

        # Use a stack for flood-fill
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if 0 <= cx < width and 0 <= cy < height and qt_image.pixelColor(cx, cy) == target_color:
                # Change the pixel color
                qt_image.setPixelColor(cx, cy, new_color)

                # Add neighboring pixels to the stack
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

        # Update the canvas with the modified image
        self.canvas = QPixmap.fromImage(qt_image)
        self.canvas_label.setPixmap(self.canvas)

            
    def modify_pixel_color(self, x, y, color):
        if not self.canvas:
            return

        # Convert QPixmap to QImage for direct pixel manipulation
        image = self.canvas.toImage()
        if not image.valid(x, y):
            return

        # Change a single pixel's color
        image.setPixelColor(x, y, color)

        # Update the canvas with the modified image
        self.canvas = QPixmap.fromImage(image)
        self.canvas_label.setPixmap(self.canvas)

    def modify_pixel_group(self, x_start, y_start, x_end, y_end, color):
        if not self.canvas:
            return

        # Convert QPixmap to QImage
        image = self.canvas.toImage()

        # Loop through the specified region
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                if image.valid(x, y):
                    image.setPixelColor(x, y, color)

        # Update the canvas
        self.canvas = QPixmap.fromImage(image)
        self.canvas_label.setPixmap(self.canvas)


    def mouse_move_event(self, event):
        if self.is_drawing:
            self.draw(event)
        elif event.buttons() & Qt.MiddleButton and hasattr(self, 'pan_start_pos'):
            delta = event.pos() - self.pan_start_pos
            self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().value() - delta.x())
            self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().value() - delta.y())
            self.pan_start_pos = event.pos()
        elif self.is_shape_mode and self.start_point:
            # Create a temporary pixmap to preview the shape
            temp_canvas = QPixmap(self.canvas)
            painter = QPainter(temp_canvas)
            pen = QPen(self.brush_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)

            end_point = event.pos()

            # Draw the selected shape on the temporary canvas
            if self.current_shape == "Circle":
                radius = int(((end_point.x() - self.start_point.x())**2 + (end_point.y() - self.start_point.y())**2)**0.5)
                painter.drawEllipse(self.start_point, radius, radius)
            elif self.current_shape == "Rectangle":
                painter.drawRect(QRect(self.start_point, end_point))
            elif self.current_shape == "Square":
                side = min(abs(end_point.x() - self.start_point.x()), abs(end_point.y() - self.start_point.y()))
                painter.drawRect(self.start_point.x(), self.start_point.y(), side, side)
            elif self.current_shape == "Line":
                painter.drawLine(self.start_point, end_point)
            elif self.current_shape == "Triangle":
                points = [
                    self.start_point,
                    QPoint(self.start_point.x(), end_point.y()),
                    QPoint(end_point.x(), end_point.y())
                ]
                painter.drawPolygon(*points)

            painter.end()

            # Display the temporary canvas on the QLabel
            self.canvas_label.setPixmap(temp_canvas)
        elif self.crop_mode_active and self.crop_start_pos:
            # Update the crop rectangle as the mouse is dragged
            end_pos = event.pos()
            self.crop_rect = QRect(self.crop_start_pos, end_pos).normalized()
            self.redraw_canvas()
        elif self.rotate_mode_active and self.selected_object:
            # Calculate rotation angle based on mouse movement
            dx = event.pos().x() - (self.selected_object['rect'].x() + self.selected_object['rect'].width() / 2)
            dy = event.pos().y() - (self.selected_object['rect'].y() + self.selected_object['rect'].height() / 2)
            angle = np.arctan2(dy, dx) * (180 / np.pi)
            self.apply_rotation(angle)

        elif self.drag_mode_active and self.drag_start_pos and self.selected_object:
            dx = event.pos().x() - self.drag_start_pos.x()
            dy = event.pos().y() - self.drag_start_pos.y()

            # Update the position of the selected object
            self.selected_object['rect'].moveTo(
                self.selected_object['rect'].x() + dx,
                self.selected_object['rect'].y() + dy
            )
            self.selected_object['x'] += dx
            self.selected_object['y'] += dy

            self.drag_start_pos = event.pos()
            self.redraw_canvas()


    def mouse_release_event(self, event):
        if self.crop_mode_active and event.button() == Qt.LeftButton:
            if self.crop_rect and not self.crop_rect.isEmpty():
                # Confirm crop and apply it
                self.apply_crop()
            self.crop_start_pos = None
        elif event.button() == Qt.MiddleButton:
            self.scroll_area.setCursor(Qt.ArrowCursor)
        elif self.drag_mode_active and event.button() == Qt.LeftButton:
            self.drag_start_pos = None
        elif self.rotate_mode_active and event.button() == Qt.LeftButton:
            self.rotation_start_angle = None
        elif self.is_drawing and event.button() == Qt.LeftButton:
            self.last_point = None
            
        elif self.is_shape_mode and self.start_point and event.button() == Qt.LeftButton:
            end_point = event.pos()
            path = QPainterPath()
            pen = QPen(self.selected_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

            # Create the shape
            if self.current_shape == "Circle":
                radius = int(((end_point.x() - self.start_point.x())**2 + (end_point.y() - self.start_point.y())**2)**0.5)
                path.addEllipse(self.start_point, radius, radius)
            elif self.current_shape == "Rectangle":
                # Use QRectF instead of QRect
                path.addRect(QRectF(self.start_point, end_point))
            elif self.current_shape == "Square":
                side = min(abs(end_point.x() - self.start_point.x()), abs(end_point.y() - self.start_point.y()))
                path.addRect(QRectF(self.start_point.x(), self.start_point.y(), side, side))
            elif self.current_shape == "Line":
                path.moveTo(self.start_point)
                path.lineTo(end_point)
            elif self.current_shape == "Triangle":
                points = [
                    self.start_point,
                    QPointF(self.start_point.x(), end_point.y()),
                    QPointF(end_point.x(), end_point.y())
                ]
                path.moveTo(points[0])
                path.lineTo(points[1])
                path.lineTo(points[2])
                path.closeSubpath()

            # Save the shape to elements list
            self.elements.append({'type': 'shape', 'pen': pen, 'path': path})

            # Draw the shape
            painter = QPainter(self.canvas)
            painter.setPen(pen)
            painter.drawPath(path)
            painter.end()

            # Update the canvas
            self.canvas_label.setPixmap(self.canvas)
            self.start_point = None

            
    def keyPressEvent(self, event):
        if self.is_text_mode and self.text_start_point:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # Save text to elements list
                font = QFont(self.font_style_dropdown.currentText(), self.font_size_spinbox.value())
                font.setBold(self.text_bold)
                font.setItalic(self.text_italic)
                font.setUnderline(self.text_underline)
                pen = QPen(self.selected_color)

                self.elements.append({'type': 'text', 'font': font, 'pen': pen, 'position': self.text_start_point, 'text': self.current_text})

                # Finalize text on canvas
                painter = QPainter(self.canvas)
                painter.setFont(font)
                painter.setPen(pen)
                painter.drawText(self.text_start_point, self.current_text)
                painter.end()

                # Update the canvas
                self.canvas_label.setPixmap(self.canvas)
                self.current_text = ""
                self.text_start_point = None  # Reset the start point for text

            elif event.key() == Qt.Key_Backspace:
                # Handle backspace
                self.current_text = self.current_text[:-1]
                self.update_text_preview()
            else:
                # Append typed character
                self.current_text += event.text()
                self.update_text_preview()

    def apply_crop(self):
        if not self.selected_object or not self.crop_rect:
            return  # No object selected or no crop rectangle defined

        obj = self.selected_object
        intersected_rect = self.crop_rect.translated(-obj['rect'].x(), -obj['rect'].y()).intersected(
            QRect(0, 0, obj['pixmap'].width(), obj['pixmap'].height())
        )

        if intersected_rect.isEmpty():
            return  # No valid crop area

        # Crop the pixmap
        cropped_pixmap = obj['pixmap'].copy(intersected_rect)
        obj['pixmap'] = cropped_pixmap
        obj['rect'] = QRect(obj['rect'].x() + intersected_rect.x(), obj['rect'].y() + intersected_rect.y(),
                            cropped_pixmap.width(), cropped_pixmap.height())

        # Clear crop state and redraw
        self.crop_rect = None
        self.redraw_canvas()
        
    def show_histogram(self):
        if not self.selected_object:
            return

        # Get the pixmap of the selected object
        pixmap = self.selected_object['pixmap']
        qt_image = pixmap.toImage()

        # Convert QImage to OpenCV format
        qt_image = qt_image.convertToFormat(QImage.Format_RGB32)
        width, height = qt_image.width(), qt_image.height()
        ptr = qt_image.bits()
        ptr.setsize(qt_image.byteCount())
        cv_image = np.array(ptr).reshape((height, width, 4))[:, :, :3]  # Extract RGB channels

        # Call the provided histogram function
        self.display_histogram(cv_image)

    def display_histogram(self, image):
        """Display histograms for the RGB channels of an image."""
        # Convert to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Calculate histograms
        hist1 = cv2.calcHist([image], [0], None, [256], [0, 256])  # Red
        hist2 = cv2.calcHist([image], [1], None, [256], [0, 256])  # Green
        hist3 = cv2.calcHist([image], [2], None, [256], [0, 256])  # Blue

        # Titles for plots
        titles = ["Original Image", "Red Histogram", "Green Histogram", "Blue Histogram", "All Channels"]
        
        # Create the plot
        plt.figure(figsize=(15, 5))
        
        # Display the image
        plt.subplot(1, 5, 1)
        plt.title(titles[0])
        plt.imshow(image)
        plt.axis("off")
        
        # Display histograms
        for i, (hist, color) in enumerate(zip([hist1, hist2, hist3], ['r', 'g', 'b']), start=2):
            plt.subplot(1, 5, i)
            plt.title(titles[i-1])
            plt.plot(hist, color=color)
            plt.xlim([0, 256])
        
        # Combined histogram
        plt.subplot(1, 5, 5)
        plt.title(titles[4])
        plt.plot(hist1, color='r')
        plt.plot(hist2, color='g')
        plt.plot(hist3, color='b')
        plt.xlim([0, 256])
        
        # Show the plot
        plt.tight_layout()
        plt.show()

            
    def update_text_preview(self):
        # Create a temporary canvas to overlay the text preview
        temp_canvas = QPixmap(self.canvas)
        painter = QPainter(temp_canvas)

        # Draw the text box as a rectangle
        if self.text_start_point:
            pen = QPen(Qt.gray, 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(QRect(self.text_start_point, QPoint(self.text_start_point.x() + 200, self.text_start_point.y()-20)))

        # Set up font style
        font = QFont(self.font_style_dropdown.currentText(), self.font_size_spinbox.value())
        font.setBold(self.text_bold)
        font.setItalic(self.text_italic)
        font.setUnderline(self.text_underline)
        painter.setFont(font)

        # Draw the preview text
        painter.drawText(self.text_start_point, self.current_text)
        painter.end()

        # Update the QLabel with the temporary canvas
        self.canvas_label.setPixmap(temp_canvas)
            
    def toggle_text_mode(self):
        self.is_text_mode = self.text_button.isChecked()
        if self.is_text_mode:
            self.text_button.setText("Disable Text")
            self.text_button.setStyleSheet("background-color: green;")
        else:
            self.text_button.setText("Enable Text")
            self.text_button.setStyleSheet("")
            self.text_start_point = None # Reset the starting point for text input

    def toggle_bold(self):
        self.text_bold = self.bold_button.isChecked()
        self.update_button_style(self.bold_button, self.text_bold)

    def toggle_italic(self):
        self.text_italic = self.italic_button.isChecked()
        self.update_button_style(self.italic_button, self.text_italic)

    def toggle_underline(self):
        self.text_underline = self.underline_button.isChecked()
        self.update_button_style(self.underline_button, self.text_underline)

    def update_button_style(self, button, is_active):
        if is_active:
            button.setStyleSheet("background-color: green;")
        else:
            button.setStyleSheet("")
            
    def update_tool(self, tool_name):
        self.current_tool = tool_name
        
    def toggle_shape_mode(self):
        self.is_shape_mode = self.shape_button.isChecked()
        if self.is_shape_mode:
            self.shape_button.setText("Disable Shape")
            self.shape_button.setStyleSheet("background-color: green;")
        else:
            self.shape_button.setText("Enable Shape")
            self.shape_button.setStyleSheet("")

    def shape_tool(self, shape_name):
        self.current_shape = shape_name
            
    def toggle_drawing_mode(self):
        self.is_drawing = not self.is_drawing
        if self.is_drawing:
            self.draw_button.setText("Disable Drawing")
            self.draw_button.setStyleSheet("background-color: green;")
        else:
            self.draw_button.setText("Enable Drawing")
            self.draw_button.setStyleSheet("")

    def update_brush_size(self, value):
        self.brush_size = value

    def choose_color(self):
        color = QColorDialog.getColor(initial=self.selected_color, parent=self, title="Select Color")
        if color.isValid():
            self.selected_color = color

    def start_drawing(self, event):
        if self.is_drawing:
            self.last_point = event.pos()

    def draw(self, event):
        if self.is_drawing and self.last_point:
            pen = QPen(self.brush_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

            # Handle different tools
            if self.current_tool == "Eraser":
                # Eraser behavior: use white color and a larger pen size
                pen.setColor(Qt.white)
            elif self.current_tool == "Pen":
                # Pen behavior: keep current brush color and small size
                pen.setWidth(self.brush_size)
                color = QColor(self.selected_color)
                pen.setColor(color)
            elif self.current_tool == "Marker":
                # Marker behavior: semi-transparent strokes
                pen.setWidth(self.brush_size * 2)
                color = QColor(self.selected_color)  # Copy the current brush color
                pen.setColor(color)
            elif self.current_tool == "Highlighter":
                # Highlighter behavior: larger and semi-transparent
                pen.setWidth(self.brush_size * 2)
                color = QColor(self.selected_color) # Copy the current brush color
                color.setAlpha(128)  # Semi-transparent
                pen.setColor(color)
            elif self.current_tool == "Pencil":
                # Pencil behavior: thin and dark gray
                pen.setWidth(self.brush_size // 2)
                pen.setColor(Qt.darkGray)

            # Create a QPainterPath for the drawing
            path = QPainterPath()
            path.moveTo(self.last_point)
            path.lineTo(event.pos())

            # Save the drawing to the elements list
            self.elements.append({'type': 'drawing', 'pen': pen, 'path': path})

            # Draw the current segment
            painter = QPainter(self.canvas)
            painter.setPen(pen)
            painter.drawPath(path)
            painter.end()

            # Update the canvas
            self.canvas_label.setPixmap(self.canvas)

            # Update the last point
            self.last_point = event.pos()

    def stop_drawing(self, event):
        self.last_point = None
        
    def highlight_selected_object(self):
        if self.selected_object:
            self.redraw_canvas()  # Redraw canvas with all objects and highlights


class CanvasApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.splash = None
        self.main_window = None

    def start(self):
        splash_image_path = "fairy tail.png"
        try:
            self.splash = SplashScreen(splash_image_path, width=600, height=500)
            self.splash.show()
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)

        QTimer.singleShot(3000, self.show_canvas_dialog)
        sys.exit(self.app.exec_())

    def show_canvas_dialog(self):
        if self.splash:
            self.splash.close()
            self.splash = None

        dialog = CanvasSettingsDialog()
        if dialog.exec_() == QDialog.Accepted:
            project_name, width, height = dialog.get_canvas_settings()
            self.show_main_window(width, height)
        else:
            sys.exit(0)

    def show_main_window(self, width, height):
        self.main_window = CanvasWindow(width, height)
        self.main_window.show()


if __name__ == "__main__":
    app = CanvasApp()
    app.start()