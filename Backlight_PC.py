from os.path import exists
from sys import argv, exit
from time import sleep, time
from math import sqrt, atan, pi
import serial
from serial.tools import list_ports
from threading import Thread
from pyautogui import screenshot
from numpy import array
from configparser import ConfigParser
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel, QSlider, QApplication, QStyleFactory


class Rgbcontrol:
    def __init__(self):
        self.frequency = 0
        self.brightness = 0
        self.ser = None
        self.image = None
        self.arduino_ports = None
        self.usb_connected = False
        self.run_update_rgb_thread = False
        self.arduino_connected_port = None
        self.run_keep_connection_thread = True

    def keep_connection(self):
        while self.run_keep_connection_thread:
            if not self.is_still_connected():
                self.usb_connected = False
                print("connection to arduino")
                self.connect_arduino()
            sleep(1)

    def is_still_connected(self):
        if not self.usb_connected:
            return False

        myports = [tuple(p) for p in list(list_ports.comports())]
        if self.arduino_ports not in myports:
            print("Arduino has been disconnected!")
            return False
        else:
            return True

    def connect_arduino(self):
        if not self.usb_connected:
            for i in range(30):
                try:
                    self.ser = serial.Serial("COM" + str(i), 9600, timeout=10)
                    self.arduino_connected_port = i
                    self.usb_connected = True
                    print("found USB on port: ", self.arduino_connected_port)
                    myports = [tuple(p) for p in list(list_ports.comports())]
                    self.arduino_ports = [port for port in myports if 'COM' + str(i) in port][0]
                    break

                except serial.SerialException:
                    # print("Could not find USB on port:", i)
                    sleep(0.05)

    @staticmethod
    def current_milli_time():
        return int(round(time() * 1000))

    def send_data(self, data_array):
        send_data = str(data_array[0]) + "," + \
                    str(data_array[1]) + "," + \
                    str(data_array[2]) + "," + \
                    str(self.frequency) + ","
        try:
            self.ser.write(str(send_data).encode('utf-8'))
            # print("send data: ", send_data)
        except serial.SerialException:
            print("cant send data")

    def update_rgb(self):
        previous_average_color = [0, 0, 0]
        while self.run_update_rgb_thread:
            if self.usb_connected:
                start_time = self.current_milli_time()
                try:
                    self.image = screenshot()
                except:
                    print("could not grab screen image")
                    return

                average_color = array(self.image).mean(axis=(0, 1), dtype=int)
                average_color = array(average_color * self.brightness, dtype=int)

                if average_color[0] != previous_average_color[0] or \
                   average_color[1] != previous_average_color[1] or \
                   average_color[2] != previous_average_color[2]:
                    previous_average_color = average_color
                    self.send_data(average_color)

                sleep_time = (1 / self.frequency) - (self.current_milli_time() - start_time) * 0.001
                if sleep_time > 0:
                    sleep(sleep_time)  # wake up ever so often and perform this ...
        if not self.run_keep_connection_thread:
            self.send_data([0, 0, 0])


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.title = "BackLight"
        self.RGB = Rgbcontrol()
        self.settings_path = "settings.ini"
        self.colorwheel_size = 250

        # open settings file, create a new one if it doesn't exist
        if not exists(self.settings_path):
            self.create_config(self.settings_path)
            print("creating new file")
        self.config = ConfigParser()
        self.config.read(self.settings_path)
        self.RGB.brightness = 0.01 * int(self.config["tab1"]["brightness"])
        self.RGB.frequency = int(self.config["tab1"]["frequency"])

        print(int(self.config["tab1"]["brightness"]))
        print(int(self.config["tab1"]["frequency"]))

        # Initialize tab screen
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabs.currentChanged.connect(self.on_change)  # changed!

        # Add tabs
        self.tabs.addTab(self.tab1, "Automatic")
        self.tabs.addTab(self.tab2, "Manual")

        # -----------------------------------------------------------------------------------------------------------
        # Create first tab
        self.tab1.layout = QVBoxLayout()

        # PowerButton
        self.powerButton = QPushButton("", self)
        self.powerButton.setCheckable(True)
        self.powerButton.setChecked(False)
        self.powerButton.clicked.connect(self.toggle_power)
        self.tab1.layout.addWidget(self.powerButton)
        self.toggle_power()

        # Brightness slider
        self.brightnessLabel1 = QLabel("brightness (" + self.config["tab1"]["brightness"] + " %)")
        self.brightnessControl1 = QSlider(Qt.Horizontal)
        self.brightnessControl1.setValue(int(self.config["tab1"]["brightness"]))
        self.brightnessControl1.setMinimum(1)
        self.brightnessControl1.setMaximum(100)
        self.brightnessControl1.setTickInterval(10)
        self.brightnessControl1.setTickPosition(QSlider.TicksBelow)
        self.brightnessControl1.valueChanged.connect(self.set_automatic_brightness)

        self.tab1.layout.addWidget(self.brightnessLabel1)
        self.tab1.layout.addWidget(self.brightnessControl1)

        # Frequency slider
        self.frequencyLabel = QLabel("frequency (" + self.config["tab1"]["frequency"] + " Hz)")
        self.frequencyControl = QSlider(Qt.Horizontal)
        self.frequencyControl.setValue(int(self.config["tab1"]["frequency"]))
        self.frequencyControl.setMinimum(1)
        self.frequencyControl.setMaximum(15)
        self.frequencyControl.setTickInterval(3)
        self.frequencyControl.setTickPosition(QSlider.TicksBelow)
        self.frequencyControl.valueChanged.connect(self.set_frequency)
        self.tab1.layout.addWidget(self.frequencyLabel)
        self.tab1.layout.addWidget(self.frequencyControl)

        # images to show if usb connection is working or not
        self.usb_connected_image = QPixmap("usb_connected.png")
        self.usb_not_connected_image = QPixmap("usb_not_connected.png")

        self.connection_box = QHBoxLayout()

        self.comLabel = QLabel()
        self.comLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.comLabel.setFont(QFont("Helvetica", 8, QFont.Medium))
        self.comLabel.setStyleSheet('color: gray')
        self.connection_box.addWidget(self.comLabel)

        self.connectLabel = QLabel()
        self.connectLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.connection_box.addWidget(self.connectLabel)

        self.tab1.layout.addLayout(self.connection_box)

        # set layout in first tab
        self.tab1.setLayout(self.tab1.layout)

        # -----------------------------------------------------------------------------------------------------------
        # Create second tab
        self.tab2.layout = QVBoxLayout()
        self.h = 0.0
        self.s = 0.0
        self.v = 0.0
        self.r = 0.0
        self.g = 0.0
        self.b = 0.0

        # colorwheel
        self.pixmap = QPixmap("HSVwheel.png")
        self.pixmap2 = self.pixmap.scaledToHeight(self.colorwheel_size)
        self.image = QLabel()
        self.image.setPixmap(self.pixmap2)
        self.image.setObjectName("HSVwheel")
        self.image.resize(self.colorwheel_size, self.colorwheel_size)
        self.image.hasMouseTracking()
        self.image.mousePressEvent = self.update_color
        self.tab2.layout.addWidget(self.image)

        # Brightness slider
        self.brightnessLabel2 = QLabel("brightness (" + self.config["tab2"]["brightness"] + " %)")
        self.brightnessControl2 = QSlider(Qt.Horizontal)
        self.brightnessControl2.setValue(int(self.config["tab2"]["brightness"]))
        self.brightnessControl2.setMinimum(1)
        self.brightnessControl2.setMaximum(100)
        self.brightnessControl2.setTickInterval(10)
        self.brightnessControl2.setTickPosition(QSlider.TicksBelow)
        self.brightnessControl2.valueChanged.connect(self.set_manual_brightness)
        self.tab2.layout.addWidget(self.brightnessLabel2)
        self.tab2.layout.addWidget(self.brightnessControl2)

        # set layout in second tab
        self.tab2.setLayout(self.tab2.layout)

        # -----------------------------------------------------------------------------------------------------------

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.setWindowTitle(self.title)
        self.setFixedSize(self.colorwheel_size + 46, self.colorwheel_size + 66)
        self.show()
        self.run_update_connect_image_thread = True
        Thread(target=self.update_connect_image, args=[]).start()
        Thread(target=self.RGB.keep_connection, args=[]).start()

    def update_connect_image(self):
        while self.run_update_connect_image_thread:
            if self.RGB.usb_connected:
                self.connectLabel.setPixmap(self.usb_connected_image)
                self.comLabel.setText(("Connected with COM " + str(self.RGB.arduino_connected_port)))
            else:
                self.connectLabel.setPixmap(self.usb_not_connected_image)
                self.comLabel.setText("")
            sleep(1)

    def write_to_config(self):
        with open(self.settings_path, "w") as config_file:
            self.config.write(config_file)

    @staticmethod
    def create_config(filename):
        """
        Create a config file
        """
        config = ConfigParser()
        config.add_section("tab1")
        config.set("tab1", "brightness", "50")
        config.set("tab1", "frequency", "5")
        config.add_section("tab2")
        config.set("tab2", "brightness", "50")
        with open(filename, "w") as config_file:
            config.write(config_file)

    def update_color(self, event):
        """
        Update color from the color wheel
        """
        if self.powerButton.isChecked():
            self.powerButton.setChecked(False)
            self.toggle_power()

        if event.pos().x() != 0:
            x = -((self.colorwheel_size * 0.5) - event.pos().x()) / self.colorwheel_size
        else:
            x = 0.0

        if event.pos().y() != 0:
            y = ((self.colorwheel_size * 0.5) - event.pos().y()) / self.colorwheel_size
        else:
            y = 0.0

        radius = min(sqrt(x ** 2 + y ** 2) * 2.5, 1.0)
        angle = 0
        if y != 0:
            angle = atan(x / y) / pi * 180
        if y > 0:
            if x < 0:
                angle = 360 + angle
        elif x < 0:
            angle += 180
        else:
            angle = 180 + angle

        self.h = angle
        self.s = radius
        self.set_manual_brightness()

    def convert_and_send_color(self):
        self.r, self.g, self.b = hsv_to_rgb(self.h / 360, self.s, self.RGB.brightness)
        # print("h:", format(h, '.1f'), "s:", format(s, '.1f'), "v:", v, "r:", r, "g:", g, "b:", b)
        if self.RGB.usb_connected:
            self.RGB.send_data([self.r, self.g, self.b])

    def on_change(self, i):
        if i == 1:
            self.setFixedSize(self.colorwheel_size + 46, self.colorwheel_size + 130)

        else:
            self.RGB.frequency = int(self.config["tab1"]["frequency"])
            self.setFixedSize(self.colorwheel_size + 46, self.colorwheel_size + 66)

    def toggle_power(self):
        if self.powerButton.isChecked() and self.RGB.usb_connected:
            self.powerButton.setStyleSheet('background-color:green')
            if self.brightnessControl1.value() != int(self.config["tab1"]["brightness"]):
                self.set_automatic_brightness()
            self.RGB.run_update_rgb_thread = True
            Thread(target=self.RGB.update_rgb, args=[]).start()

        else:
            self.powerButton.setStyleSheet('background-color:red')
            self.RGB.run_update_rgb_thread = False

    def set_frequency(self):
        if self.frequencyControl.value() > 0:
            self.RGB.frequency = self.frequencyControl.value()
            self.frequencyLabel.setText("frequency (" + str(self.frequencyControl.value()) + " Hz)")
            self.config["tab1"]["frequency"] = str(self.frequencyControl.value())
            self.write_to_config()

    def set_automatic_brightness(self):
        if 0 <= self.brightnessControl1.value() <= 100:
            self.RGB.brightness = self.brightnessControl1.value() / 100
            self.brightnessLabel1.setText("brightness (" + str(self.brightnessControl1.value()) + " %)")
            self.config["tab1"]["brightness"] = str(self.brightnessControl1.value())
            self.write_to_config()

    def set_manual_brightness(self):
        if 0 <= self.brightnessControl2.value() <= 100:
            self.RGB.brightness = self.brightnessControl2.value() / 100
            self.brightnessLabel2.setText("brightness (" + str(self.brightnessControl2.value()) + " %)")
            self.config["tab2"]["brightness"] = str(self.brightnessControl2.value())
            self.write_to_config()
            print("written to settings file")

            self.RGB.frequency = 1
            self.convert_and_send_color()

    def closeEvent(self, event):
        self.RGB.run_update_rgb_thread = False
        self.RGB.run_keep_connection_thread = False
        self.run_update_connect_image_thread = False
        self.RGB.send_data([0, 0, 0])
        sleep(0.5)
        event.accept()


def hsv_to_rgb(h, s, v):
    if s == 0.0:
        v *= 255
        return v, v, v
    i = int(h * 6.)  # XXX assume int() truncates!
    f = (h * 6.) - i
    p, q, t = int(255 * (v * (1. - s))), int(255 * (v * (1. - s * f))), int(255 * (v * (1. - s * (1. - f))))
    v *= 255
    i %= 6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q


app = QApplication(argv)
app.setStyle(QStyleFactory.create('Fusion'))
a_window = Window()
exit(app.exec_())
