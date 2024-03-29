import os
import sys
import json
import subprocess
import importlib
from PySide6.QtCore import (
    QThread, Signal, QUrl, Qt, QSize, QRect, QCoreApplication
)
from PySide6.QtGui import QIcon, QPixmap, QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QStatusBar,
    QLabel, QPlainTextEdit, QScrollArea,  QMenuBar, QMenu, QDockWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

from urllib.parse import quote_plus

from csilibs.utils import pathme, auditme, get_current_timestamp
from csilibs.networking import my_ip, my_tor_ip, CSIIPLocation, TorCheck

import qdarktheme

# REMOVED THE CASE DIRECTORY NEED TO KNOW IP BECAUSE IT'S NOT OF THE USE.
# YOU CAN USE THIS CODE IN ANOTHER CODE FOR LOGGING PURPOSES DURING CASE
# 
# if not os.path.exists("data/agency_data.json"):
#     try:
#         tool = pathme("Agency_Wizard.py")
#         subprocess.run(["python", tool])
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         sys.exit()

# agd = pathme("data/agency_data.json")
# with open(agd, "r") as file:
#     data = json.load(file)
#     cases_folder = data.get("cases_folder")
#     logo_path = pathme("assets/agencylogo.png")

csitoolname = "CSI: What is My IP?"
case_directory = ""
# case_directory = cases_folder
# current_dir = os.getcwd()  # Get the current working directory
# notes_file_path = os.path.join(case_directory, "External_Network.txt")

icon = pathme("assets/icons/csi_onion.ico")
Torico = pathme("assets/icons/csi_onion.ico")
TorVPNico = pathme("assets/icons/csi_tor_onion.ico")
Buttonico = pathme("assets/icons/exit.ico")

# if not os.path.isfile(notes_file_path):
#     with open(notes_file_path, 'a+') as f:
#         f.write("External IP Address Information:\n" + get_current_timestamp() + "\n\n")

def format_dict_to_str(dict_obj):
    return '\n'.join([f'{k}: {v}' for k, v in dict_obj.items()])

#---------------------------- For Relative Sizing(REQUIRED) -------------------------------#
def percentSize(object, width_percentage=100, height_percentage=100):
    # use 'app' to get desktop relative sizing, for others pass the object not string 
    if type(object) == str and  object.lower().endswith('app'):
        desktop_size = QGuiApplication.primaryScreen().availableGeometry()
        object = desktop_size

    width = int(object.width() * (width_percentage/100))
    height = int(object.height() * (height_percentage/100))
    return (width, height)


class Worker(QThread):
    data_fetched = Signal(str, dict)

    def __init__(self, main_window, ip_fetcher, location_fetcher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window = main_window
        self.ip_fetcher = ip_fetcher
        self.location_fetcher = location_fetcher

    def run(self):
        ip, istor = self.ip_fetcher()
        ip_info = self.location_fetcher(ip, istor)
        if ip_info is not None:
            self.data_fetched.emit(ip, ip_info)
        else:
            print("Failed to fetch IP info.")

class StartCSITorVPNThread(QThread):
    torvpn_started = Signal()

    def run(self):
        try:
            subprocess.run(["CSI_TorVPN"], check=True)
        except subprocess.CalledProcessError:
            print("CSI_TorVPN exited with a non-zero status")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            self.torvpn_started.emit()

class BaseCSIApplication(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



class CSIMainWindow(QMainWindow):
    def __init__(self, case_directory, window_title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case_directory = case_directory
        self.setWindowTitle(f"{window_title}")
        self.setWindowIcon(QIcon(icon))
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.application = None

        self.setGeometry(0,0, *percentSize("app",95,90))
        self.center()

        #-------------------------- MENU BAR --------------------------#
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, *percentSize("app",95,10)))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        # menu list
        self.menuList = QMenu(self.menubar)
        self.menuList.setTitle("Menu")
        
        self.themeMenu = QMenu(self.menubar)
        self.themeMenu.setTitle("Themes")
        
        # menu options within menu list
        self.fullscreenOption = QAction(self)
        self.fullscreenOption.setShortcut("Ctrl+F")
        self.fullscreenOption.setText("FullScreen Toggle")
        self.fullscreenOption.setStatusTip("Click to move to and from FullScreen")
    
        self.menuList.addAction(self.fullscreenOption)

        self.menubar.addAction(self.menuList.menuAction())

        self.darkTheme = QAction(self)
        self.darkTheme.setText("Dark Theme")
        self.darkTheme.setStatusTip("Enable Dark theme")
        self.themeMenu.addAction(self.darkTheme)
        self.lightTheme = QAction(self)
        self.lightTheme.setText("Light Theme")
        self.lightTheme.setStatusTip("Enable Light theme")
        self.themeMenu.addAction(self.lightTheme)

        self.menubar.addAction(self.themeMenu.menuAction())

        self.darkTheme.triggered.connect(lambda: self.theme_change("dark"))
        self.lightTheme.triggered.connect(lambda: self.theme_change("light"))
        print("fullscreen",self.isFullScreen())
        self.fullscreenOption.triggered.connect(lambda: self.showFullScreen() if not self.isFullScreen() else self.showNormal())

    def theme_change(self, theme_color):
        qdarktheme.setup_theme(theme_color)

    def center(self):
        qRect = self.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())

    def set_application(self, application):
        self.application = application

    def update_status(self, message):
        self.status_bar.showMessage(message)


class BaseCSIWidget(QWidget):
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window = main_window
        self.main_window.update_status(f"Starting workers for data capture")

        self.clearnet_worker = Worker(main_window, my_ip, CSIIPLocation)
        self.clearnet_worker.data_fetched.connect(self.update_clearnet_ip_label)
        self.clearnet_worker.start()

        self.tor_worker = Worker(main_window, my_tor_ip, CSIIPLocation)
        self.tor_worker.data_fetched.connect(self.update_tor_ip_label)
        self.tor_worker.start()

        self.setWindowTitle(f"{csitoolname}")
        self.setWindowIcon(QIcon(icon))

        self.main_layout = QHBoxLayout()  # Use QHBoxLayout for controlled width layout
        #----------------------------------- LEFT DOCK -------------------------------------#
        self.leftDock = QDockWidget(main_window)
        self.leftDock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.leftDock.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.leftDock.setWindowTitle(QCoreApplication.translate("MainWindow", u"Data Variables", None))
        self.leftDock.setMinimumWidth(percentSize(main_window,20,0)[0])
        self.leftDockContent = QWidget()
        self.leftDockContent.setObjectName("leftDockContent")
        self.leftDock.setWidget(self.leftDockContent)
        main_window.addDockWidget(Qt.DockWidgetArea(1), self.leftDock)

        # Command layout
        self.cmd_widget = QWidget(self.leftDockContent)  # Create a QWidget
        self.leftDock.resizeEvent = lambda event: self.adjust_size(self.cmd_widget, self.leftDock)
        self.cmd_layout = QVBoxLayout()  # Set QVBoxLayout
        self.cmd_widget.setLayout(self.cmd_layout)  # Set layout to the widget

        scroll_area = QScrollArea()  # Create a scroll area widget
        scroll_widget = QWidget()  # Create a widget to hold the scrollable contents
        self.scroll_layout = QVBoxLayout(scroll_widget)  # Set QVBoxLayout for the scrollable contents

        # IP address and geolocation data

        self.clearnet_info_label = QLabel("{clearnetipinfo}")
        self.scroll_layout.addWidget(self.clearnet_info_label)

        scroll_area_2 = QScrollArea()  # Create a scroll area widget
        scroll_widget_2 = QWidget()  # Create a widget to hold the scrollable contents
        self.scroll_layout_2 = QVBoxLayout(scroll_widget_2)  # Set QVBoxLayout for the scrollable contents

        self.tor_ip_label = QLabel("{Torip}")
        self.scroll_layout_2.addWidget(self.tor_ip_label)

        scroll_area.setWidgetResizable(True)  # Allow the scroll area to resize its content widget
        scroll_area.setWidget(scroll_widget)  # Set the scrollable contents to the scroll area
        scroll_area_2.setWidgetResizable(True)  # Allow the scroll area to resize its content widget
        scroll_area_2.setWidget(scroll_widget_2)  # Set the scrollable contents to the scroll area

        self.clearnet_label = QLabel("<b>Clearnet IP</b>")
        self.clearnet_label.setAlignment(Qt.AlignCenter)
        self.cmd_layout.addWidget(self.clearnet_label)  # Add the scroll area to the cmd_layout
        self.cmd_layout.addWidget(scroll_area)  # Add the scroll area to the cmd_layout
        
        self.tor_label = QLabel("<b>Tor Darknet IP</b>")
        self.tor_label.setAlignment(Qt.AlignCenter)
        self.cmd_layout.addWidget(self.tor_label)  # Add the scroll area to the cmd_layout
        self.cmd_layout.addWidget(scroll_area_2)  # Add the scroll area to the cmd_layout
        # End Command Layout

        # View layout
        self.image_widget = QWidget()
        self.image_layout = QVBoxLayout()
        self.image_widget.setLayout(self.image_layout)

        self.browser_view = QWebEngineView()
        self.image_layout.addWidget(self.browser_view)
        # End View Layout

        # Case Note layout
        #----------------------------------- RIGHT DOCK -------------------------------------#
        self.rightDock = QDockWidget(main_window)
        self.rightDock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.rightDock.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.rightDock.setWindowTitle(QCoreApplication.translate("main_window", u"Case Notes", None))
        self.rightDock.setMinimumWidth(percentSize(main_window,15,0)[0])
        self.rightDockContent = QWidget()
        self.rightDockContent.setObjectName("rightDockContent")
        self.rightDock.setWidget(self.rightDockContent)
        main_window.addDockWidget(Qt.DockWidgetArea(2), self.rightDock)
        
        # Case Note layout
        self.sl2_widget = QWidget(self.rightDockContent)
        self.rightDock.resizeEvent = lambda event: self.adjust_size(self.sl2_widget,self.rightDock)
        self.sl2 = QVBoxLayout()
        self.case_notes_edit = QPlainTextEdit()
        self.sl2.addWidget(self.case_notes_edit)
        self.sl2_widget.setLayout(self.sl2)

        # Add the widgets to the main layout
        self.main_layout.addWidget(self.image_widget, 1)

        # Set the main layout as the widget's layout
        self.setLayout(self.main_layout)

        # if os.path.isfile(notes_file_path):
        #     with open(notes_file_path, "r") as f:
        #         existing_notes = f.read()
        #         self.case_notes_edit.setPlainText(existing_notes)

        self.sl2_button1 = QPushButton("New Tor Identity")
        self.sl2_button1.setProperty("button_state", False)
        self.sl2_button1.setIcon(QIcon(QPixmap(Torico)))
        self.sl2_button1.setIconSize(QSize(300, 35))
        self.sl2_button1.setToolTip("Get a new Tor Identity for the low low price of a button click")
        self.sl2_button1.clicked.connect(self.new_tor_identity)
        self.sl2.addWidget(self.sl2_button1)

        self.sl2_button2 = QPushButton("Start CSI TorVPN")
        self.sl2_button2.setProperty("button_state", False)
        self.sl2_button2.setIcon(QIcon(QPixmap(TorVPNico)))
        self.sl2_button2.setIconSize(QSize(300, 35))
        self.sl2_button2.setToolTip(
            "CSI TorVPN will push all your traffic through the Tor Proxy.  This minimizes the possibility of location leaks and protects like a VPN, but better."
        )
        self.sl2_button2.clicked.connect(self.start_csi_torvpn)
        self.sl2.addWidget(self.sl2_button2)

        self.close_button = QPushButton("Save & Close")
        self.close_button.setIcon(QIcon(QPixmap(Buttonico)))
        self.close_button.setIconSize(QSize(300, 35))
        self.close_button.setToolTip("Save and Close Tool.")
        # self.close_button.clicked.connect(self.save_case_notes)
        self.sl2.addWidget(self.close_button)
    
    def adjust_size(self, widget, dock):
        widget.resize(*percentSize(dock,100,95))

    def update_tor_ip_label(self, Torip, Toripinfo):
        # Store Toripinfo data with prefix
        Toripinfo_data = {}
        for key, value in Toripinfo.items():
            new_key = f"Toripinfo_{key}"
            Toripinfo_data[new_key] = value

        # Strip out the prefix from dictionary keys
        Toripinfo_data = {key.split('_')[1]: value for key, value in Toripinfo_data.items()}

        # Update the labels with the stored data
        self.tor_ip_label.setText(Torip)
        self.tor_ip_label.setText(format_dict_to_str(Toripinfo_data))
        self.main_window.update_status(f"Tor proxy is now {Torip}")

        # Update the case notes
        self.case_notes_edit.appendPlainText(
            get_current_timestamp()
            + f"\nTor Proxy IP Address: {Torip}\n{Toripinfo_data.get('org', '')}\n{Toripinfo_data.get('city', '')}, {Toripinfo_data.get('region', '')}\n"
        )

    def update_clearnet_ip_label(self, clearnetip, clearnetipinfo):
        # Store clearnetipinfo data with prefix
        clearnetipinfo_data = {}
        for key, value in clearnetipinfo.items():
            new_key = f"clearnetipinfo_{key}"
            clearnetipinfo_data[new_key] = value

        # Strip out the prefix from dictionary keys
        clearnetipinfo_data = {key.split('_')[1]: value for key, value in clearnetipinfo_data.items()}

        self.clearnet_info_label.setText(format_dict_to_str(clearnetipinfo_data))

        self.main_window.update_status(f"Updating map view")

        # Show clearnet IP location on OpenStreetMap
        if 'latitude' in clearnetipinfo_data and 'longitude' in clearnetipinfo_data:
            latitude = clearnetipinfo_data['latitude']
            longitude = clearnetipinfo_data['longitude']
            self.show_clearnet_location_on_map(latitude, longitude)

        # Update the case notes
        self.case_notes_edit.appendPlainText(
            get_current_timestamp()
            + f"\nClearnet IP Address: {clearnetip}\n{clearnetipinfo_data.get('org', '')}\n{clearnetipinfo_data.get('city', '')},     {clearnetipinfo_data.get('region', '')}\n"
        )

    def show_clearnet_location_on_map(self, latitude, longitude):
        url = f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=10/{latitude}/{longitude}"
        self.browser_view.load(QUrl(url))
        self.main_window.update_status(f"Map view opened")

    def new_tor_identity(self):
        self.case_notes_edit.appendPlainText(get_current_timestamp() + f"\nNew Tor identity requested")
        self.main_window.update_status("Requesting new Tor identity")
        TorCheck("newnym")
        new_tor_ip = my_tor_ip()
        self.main_window.update_status(f"New Tor IP address is: {new_tor_ip}")
        print(new_tor_ip)
        self.tor_worker = Worker(main_window, my_tor_ip, CSIIPLocation)
        self.tor_worker.data_fetched.connect(self.update_tor_ip_label)
        self.tor_worker.start()  # Start the worker thread
    def start_csi_torvpn(self):
        self.main_window.update_status(f"Starting the CSI TorVPN...")
        self.csi_torvpn_thread = StartCSITorVPNThread()
        self.csi_torvpn_thread.torvpn_started.connect(self.on_torvpn_started)
        self.csi_torvpn_thread.start()

    def on_torvpn_started(self):
        self.main_window.update_status(f"CSI TorVPN started successfully.")
        self.main_window.update_status(f"Sending the workers to get data...")

        try:
            self.clearnet_worker = Worker(main_window, my_ip, CSIIPLocation)
            self.clearnet_worker.data_fetched.connect(self.update_clearnet_ip_label)
            self.clearnet_worker.start()
        except Exception as e:
            print(f"An error occurred when starting clearnet_worker: {str(e)}")

        try:
            self.tor_worker = Worker(main_window, my_tor_ip, CSIIPLocation)
            self.tor_worker.data_fetched.connect(self.update_tor_ip_label)
            self.tor_worker.start()
        except Exception as e:
            print(f"An error occurred when starting tor_worker: {str(e)}")

        self.main_window.update_status(f"Verify location settings. Please be patient, this can take time...")

    # def save_case_notes(self):
    #     current_timestamp = get_current_timestamp()
    #     auditme(case_directory, f"{current_timestamp}: Saving Case Notes and Exiting {csitoolname}")
    #     case_notes_content = self.case_notes_edit.toPlainText()
    #     with open(notes_file_path, "w") as f:
    #         f.write(case_notes_content)
    #     self.main_window.close()

    def adjust_image_label_size(self):
        window_width = self.image_widget.width() - 50
        self.image_label.setFixedWidth(window_width)
        scroll_width2 = self.scroll_area2.width()
        scroll_content_width2 = self.scroll_content_widget2.width()
        scroll_content_offset2 = (scroll_width2 - scroll_content_width2) // 2
        self.scroll_area2.horizontalScrollBar().setValue(scroll_content_offset2)

if __name__ == "__main__":
    app = BaseCSIApplication([sys.argv[0], '--no-sandbox'])  # Corrected line
    qdarktheme.setup_theme('dark')
    main_window = CSIMainWindow(case_directory, csitoolname)
    widget = BaseCSIWidget(main_window, main_window)  # Pass main_window as an argument
    main_window.setCentralWidget(widget)
    main_window.set_application(app)
    
    if '_PYIBoot_SPLASH' in os.environ and importlib.util.find_spec("pyi_splash"):
        import pyi_splash
        pyi_splash.update_text('UI Loaded ...')
        pyi_splash.close()
        log.info('Splash screen closed.')    
        
    main_window.show()
    sys.exit(app.exec_())
