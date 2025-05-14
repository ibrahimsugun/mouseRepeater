import sys
import time
import threading
import pyautogui
import keyboard
import warnings
import win32api
import win32con
import datetime
import configparser
import os
import json

# PyQt5 uyarılarını bastır
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QWidget, QLabel, QHBoxLayout, QMessageBox, QCheckBox,
                           QListWidget, QScrollArea, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QTimer, QEvent

# PyAutoGUI failsafe özelliğini devre dışı bırak
pyautogui.FAILSAFE = False

# Language texts
TEXTS = {
    'en': {
        'window_title': 'Mouse Recorder v0.3',
        'status_ready': 'Ready - Click "Record Clicks" to start recording',
        'status_recording': 'Recording... (Press B to stop)',
        'status_completed': 'Recording completed - You can play now',
        'status_playing': 'Playing...',
        'status_stopped': 'Playback stopped',
        'record_button': 'Record Clicks',
        'stop_record_button': 'Stop Recording (B)',
        'play_button': 'Play (C)',
        'stop_button': 'Stop (ESC)',
        'recorded_clicks': 'Recorded Clicks:',
        'profile_operations': 'Profile Operations:',
        'profile_name': 'Profile Name:',
        'save': 'Save',
        'load': 'Load',
        'reset': 'Reset',
        'playback_options': 'Playback Options:',
        'repeat_playback': 'Repeat Playback',
        'use_delays': 'Use Recorded Delays',
        'click_info': 'Program performs Left/Right clicks at recorded positions',
        'version': 'v0.4 - Added multi-language support',
        'keyboard_shortcuts': 'Keyboard Shortcuts:\nK - Start Recording\nB - Stop Recording\nC - Play\nESC - Stop',
        'language': 'Language:'
    },
    'tr': {
        'window_title': 'Fare Kaydedici v0.3',
        'status_ready': 'Hazır - Kaydetmek için "Tıklamaları Kaydet" butonuna basın',
        'status_recording': 'Kayıt yapılıyor... (Durdurmak için B tuşuna basın)',
        'status_completed': 'Kayıt tamamlandı - Oynatabilirsiniz',
        'status_playing': 'Oynatılıyor...',
        'status_stopped': 'Oynatma durduruldu',
        'record_button': 'Tıklamaları Kaydet',
        'stop_record_button': 'Kaydı Durdur (B)',
        'play_button': 'Oynat (C)',
        'stop_button': 'Durdur (ESC)',
        'recorded_clicks': 'Kaydedilen Tıklamalar:',
        'profile_operations': 'Profil İşlemleri:',
        'profile_name': 'Profil Adı:',
        'save': 'Kaydet',
        'load': 'Yükle',
        'reset': 'Sıfırla',
        'playback_options': 'Oynatma Seçenekleri:',
        'repeat_playback': 'Sürekli tekrarla',
        'use_delays': 'Kaydedilen tıklama gecikmelerini kullan',
        'click_info': 'Program kaydedilen konumlarda Sol/Sağ tıklama yapar',
        'version': 'v0.4 - Çoklu dil desteği eklendi',
        'keyboard_shortcuts': 'Klavye Kısayolları:\nK - Kaydı Başlat\nB - Kaydı Durdur\nC - Oynat\nESC - Durdur',
        'language': 'Dil:'
    }
}

# Klavye olaylarını işlemek için sinyal sınıfı
class KeyboardSignals(QObject):
    key_c_pressed = pyqtSignal()  # C tuşu - Oynat
    key_b_pressed = pyqtSignal()  # B tuşu - Kaydı Durdur
    key_k_pressed = pyqtSignal()  # K tuşu - Kaydı Başlat
    esc_pressed = pyqtSignal()    # ESC tuşu - Durdur

# Fare olaylarını izlemek için sınıf
class MouseListener(QObject):
    """
    Class that listens for mouse clicks and emits signals
    """
    left_click = pyqtSignal(int, int)
    right_click = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.is_listening = False
        self.thread = None
    
    def start_listening(self):
        """
        Starts mouse listening
        """
        if self.is_listening:
            return
            
        self.is_listening = True
        self.thread = threading.Thread(target=self._listen_mouse, daemon=True)
        self.thread.start()
        print("Mouse listening started")
    
    def stop_listening(self):
        """
        Stops mouse listening
        """
        self.is_listening = False
        if self.thread and self.thread.is_alive():
            self.thread.join(1.0)  # Wait at most 1 second
        print("Mouse listening stopped")
    
    def _listen_mouse(self):
        """
        Main loop that listens for mouse clicks
        """
        # Left and right mouse button states
        left_button_state = False
        right_button_state = False
        
        while self.is_listening:
            try:
                # Left mouse button check
                if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0:
                    if not left_button_state:
                        x, y = win32api.GetCursorPos()
                        print(f"Left click detected: X:{x}, Y:{y}")
                        self.left_click.emit(x, y)
                        left_button_state = True
                else:
                    left_button_state = False
                
                # Right mouse button check
                if win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0:
                    if not right_button_state:
                        x, y = win32api.GetCursorPos()
                        print(f"Right click detected: X:{x}, Y:{y}")
                        self.right_click.emit(x, y)
                        right_button_state = True
                else:
                    right_button_state = False
                
                # Short sleep to prevent high CPU usage
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Mouse listening error: {e}")
                time.sleep(0.5)  # Longer sleep on error

# Özel olay sınıfı
class StatusUpdateEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self):
        super(StatusUpdateEvent, self).__init__(self.EVENT_TYPE)

# Otomatik kapanan mesaj kutusu sınıfı
class AutoCloseMessageBox(QMessageBox):
    def __init__(self, *args, **kwargs):
        super(AutoCloseMessageBox, self).__init__(*args, **kwargs)
        # Create timer to close after 2 seconds
        self.timeout = 2  # seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(self.timeout * 1000)  # in milliseconds
        
        # Show remaining time
        self.countdown_label = QLabel(f"This message will close in {self.timeout} seconds", self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.countdown_label, self.layout().rowCount(), 0, 1, self.layout().columnCount())

# Sağ tıklama fonksiyonu (win32api kullanarak)
def rightclick(x, y):
    """
    Performs a right click using win32api
    """
    try:
        # Position cursor
        win32api.SetCursorPos((x, y))
        # Short delay
        time.sleep(0.05)
        # Right button down event
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
        # Delay between press and release
        time.sleep(0.1)
        # Right button up event
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
        print(f"Right click performed: X:{x}, Y:{y}")
        return True
    except Exception as e:
        print(f"Right click error: {e}")
        return False

# Sol tıklama fonksiyonu (win32api kullanarak)
def leftclick(x, y):
    """
    Performs a left click using win32api
    """
    try:
        # Position cursor
        win32api.SetCursorPos((x, y))
        # Short delay
        time.sleep(0.05)
        # Left button down event
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        # Delay between press and release
        time.sleep(0.1)
        # Left button up event
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        print(f"Left click performed: X:{x}, Y:{y}")
        return True
    except Exception as e:
        print(f"Left click error: {e}")
        return False

# Otomatik kapanan bilgi mesajı göster
def show_auto_close_info(parent, title, message):
    msg_box = AutoCloseMessageBox(QMessageBox.Information, title, message, QMessageBox.Ok, parent)
    msg_box.exec_()
    
# Otomatik kapanan uyarı mesajı göster
def show_auto_close_warning(parent, title, message):
    msg_box = AutoCloseMessageBox(QMessageBox.Warning, title, message, QMessageBox.Ok, parent)
    msg_box.exec_()

# Tıklama türünü temsil eden sınıf
class ClickAction:
    """
    Class representing a mouse click
    """
    def __init__(self, x, y, is_right_click=False, timestamp=None, delay_after=0):
        self.x = x
        self.y = y
        self.is_right_click = is_right_click  # True=Right click, False=Left click
        self.timestamp = timestamp or datetime.datetime.now()
        self.delay_after = delay_after  # Delay after this click (ms)
    
    def __str__(self):
        click_type = "Right Click" if self.is_right_click else "Left Click"
        delay_info = f"Delay: {self.delay_after}ms" if self.delay_after > 0 else ""
        return f"{click_type} - X:{self.x}, Y:{self.y} - {self.timestamp.strftime('%H:%M:%S.%f')[:-3]} {delay_info}"

# Default location for INI file
CONFIG_FILE = "settings.ini"

# Convert ClickAction to dictionary
def click_action_to_dict(action):
    """
    Converts ClickAction object to dictionary
    """
    return {
        'x': action.x,
        'y': action.y,
        'is_right_click': action.is_right_click,
        'timestamp': action.timestamp.isoformat(),
        'delay_after': action.delay_after
    }

# Create ClickAction from dictionary
def dict_to_click_action(data):
    """
    Creates ClickAction object from dictionary
    """
    return ClickAction(
        x=data['x'],
        y=data['y'],
        is_right_click=data['is_right_click'],
        timestamp=datetime.datetime.fromisoformat(data['timestamp']),
        delay_after=data['delay_after']
    )

class PointRecorderApp(QMainWindow):
    """ 
    Simple application that records and plays back mouse clicks
    """
    def __init__(self):
        super().__init__()
        
        # Application state
        self.click_actions = []  # List of ClickAction objects
        self.is_recording = False
        self.is_playing = False
        self.playback_thread = None
        self.repeat_playback = False  # Repeat option
        self.last_click_time = None   # Last click time
        self.use_recorded_delays = True  # Use recorded delays
        self.current_profile_name = "default"  # Default profile name
        self.current_language = 'en'  # Default language
        
        # Mouse listener
        self.mouse_listener = MouseListener()
        self.mouse_listener.left_click.connect(self.on_left_click)
        self.mouse_listener.right_click.connect(self.on_right_click)
        
        # Keyboard signals
        self.keyboard_signals = KeyboardSignals()
        self.keyboard_signals.key_c_pressed.connect(self.on_key_c_pressed)
        self.keyboard_signals.key_b_pressed.connect(self.on_key_b_pressed)
        self.keyboard_signals.key_k_pressed.connect(self.on_key_k_pressed)
        self.keyboard_signals.esc_pressed.connect(self.on_esc_pressed)
        
        # Keyboard event tracking last key press times
        self.last_key_c_press = 0
        self.last_key_b_press = 0
        self.last_key_k_press = 0
        self.last_esc_press = 0
        
        # Interface
        self.init_ui()
        
        # Start keyboard timer
        self.start_keyboard_timer()
        
        # Show language selection dialog
        self.show_language_dialog()
    
    def init_ui(self):
        """
        Creates the user interface
        """
        self.setWindowTitle(TEXTS[self.current_language]['window_title'])
        self.setGeometry(100, 100, 550, 650)
        
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # Status label
        self.status_label = QLabel(TEXTS[self.current_language]['status_ready'])
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)
        
        # Coordinate information
        self.coordinates_label = QLabel("Recorded clicks: 0")
        self.coordinates_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.coordinates_label)
        
        # Profile information
        self.profile_label = QLabel(f"Active Profile: {self.current_profile_name}")
        self.profile_label.setAlignment(Qt.AlignCenter)
        font = self.profile_label.font()
        font.setBold(True)
        self.profile_label.setFont(font)
        self.main_layout.addWidget(self.profile_label)
        
        # Keyboard shortcuts description
        self.keyboard_shortcuts_label = QLabel(TEXTS[self.current_language]['keyboard_shortcuts'])
        self.keyboard_shortcuts_label.setStyleSheet("color: #666; font-size: 10px;")
        self.main_layout.addWidget(self.keyboard_shortcuts_label)
        
        # Add spacing
        self.main_layout.addSpacing(10)
        
        # Record buttons
        self.record_layout = QHBoxLayout()
        
        # Start recording button
        self.record_button = QPushButton(TEXTS[self.current_language]['record_button'])
        self.record_button.setMinimumHeight(40)
        self.record_button.clicked.connect(self.start_recording)
        self.record_layout.addWidget(self.record_button)
        
        # Stop recording button
        self.stop_record_button = QPushButton(TEXTS[self.current_language]['stop_record_button'])
        self.stop_record_button.setMinimumHeight(40)
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.record_layout.addWidget(self.stop_record_button)
        
        self.main_layout.addLayout(self.record_layout)
        
        # Click list
        self.click_list_label = QLabel(TEXTS[self.current_language]['recorded_clicks'])
        self.click_list_label.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.click_list_label)
        
        self.click_list = QListWidget()
        self.click_list.setMinimumHeight(150)
        self.main_layout.addWidget(self.click_list)
        
        # Add spacing
        self.main_layout.addSpacing(10)
        
        # File Operations Group
        self.file_group_label = QLabel(TEXTS[self.current_language]['profile_operations'])
        self.file_group_label.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.file_group_label)
        
        # Profile name input
        self.profile_layout = QHBoxLayout()
        self.profile_name_label = QLabel(TEXTS[self.current_language]['profile_name'])
        self.profile_name_input = QLineEdit(self.current_profile_name)
        self.profile_layout.addWidget(self.profile_name_label)
        self.profile_layout.addWidget(self.profile_name_input)
        self.main_layout.addLayout(self.profile_layout)
        
        # File operation buttons
        self.file_buttons_layout = QHBoxLayout()
        
        # Save button
        self.save_button = QPushButton(TEXTS[self.current_language]['save'])
        self.save_button.clicked.connect(self.save_profile)
        self.file_buttons_layout.addWidget(self.save_button)
        
        # Load button
        self.load_button = QPushButton(TEXTS[self.current_language]['load'])
        self.load_button.clicked.connect(self.load_profile)
        self.file_buttons_layout.addWidget(self.load_button)
        
        # Reset button
        self.reset_button = QPushButton(TEXTS[self.current_language]['reset'])
        self.reset_button.clicked.connect(self.reset_recording)
        self.file_buttons_layout.addWidget(self.reset_button)
        
        self.main_layout.addLayout(self.file_buttons_layout)
        
        # Add spacing
        self.main_layout.addSpacing(10)
        
        # Playback Options group
        self.options_label = QLabel(TEXTS[self.current_language]['playback_options'])
        self.options_label.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.options_label)
        
        # Options layout
        self.options_layout = QVBoxLayout()
        
        # Repeat option
        self.repeat_checkbox = QCheckBox(TEXTS[self.current_language]['repeat_playback'])
        self.repeat_checkbox.setChecked(False)
        self.repeat_checkbox.stateChanged.connect(self.toggle_repeat)
        self.options_layout.addWidget(self.repeat_checkbox)
        
        # Use recorded delays option
        self.use_delays_checkbox = QCheckBox(TEXTS[self.current_language]['use_delays'])
        self.use_delays_checkbox.setChecked(True)
        self.use_delays_checkbox.stateChanged.connect(self.toggle_use_delays)
        self.options_layout.addWidget(self.use_delays_checkbox)
        
        self.main_layout.addLayout(self.options_layout)
        
        # Add spacing
        self.main_layout.addSpacing(10)
        
        # Playback buttons
        self.buttons_layout = QHBoxLayout()
        
        # Play button
        self.play_button = QPushButton(TEXTS[self.current_language]['play_button'])
        self.play_button.setMinimumHeight(40)
        self.play_button.clicked.connect(self.start_playback)
        self.buttons_layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton(TEXTS[self.current_language]['stop_button'])
        self.stop_button.setMinimumHeight(40)
        self.stop_button.clicked.connect(self.stop_playback)
        self.buttons_layout.addWidget(self.stop_button)
        
        self.main_layout.addLayout(self.buttons_layout)
        
        # Click description
        self.click_label = QLabel(TEXTS[self.current_language]['click_info'])
        self.click_label.setAlignment(Qt.AlignCenter)
        font = self.click_label.font()
        font.setBold(True)
        self.click_label.setFont(font)
        self.main_layout.addWidget(self.click_label)
        
        # Version information
        self.version_label = QLabel(TEXTS[self.current_language]['version'])
        self.version_label.setAlignment(Qt.AlignRight)
        self.main_layout.addWidget(self.version_label)
    
    def toggle_repeat(self, state):
        """
        Toggles repeat playback option
        """
        self.repeat_playback = state == Qt.Checked
        print(f"Repeat playback {'enabled' if self.repeat_playback else 'disabled'}")
    
    def start_keyboard_timer(self):
        """
        Starts timer for keyboard monitoring
        """
        self.keyboard_timer = QTimer(self)
        self.keyboard_timer.timeout.connect(self.check_keyboard)
        self.keyboard_timer.start(100)  # Check every 100ms
    
    def check_keyboard(self):
        """
        Checks keyboard keys and emits signals
        """
        try:
            current_time = time.time()
            
            # B key check (Stop Recording)
            if keyboard.is_pressed('b'):
                if current_time - self.last_key_b_press > 0.5:
                    self.last_key_b_press = current_time
                    self.keyboard_signals.key_b_pressed.emit()
            
            # C key check (Play)
            if keyboard.is_pressed('c'):
                if current_time - self.last_key_c_press > 0.5:
                    self.last_key_c_press = current_time
                    self.keyboard_signals.key_c_pressed.emit()
            
            # K key check (Start Recording)
            if keyboard.is_pressed('k'):
                if current_time - self.last_key_k_press > 0.5:
                    self.last_key_k_press = current_time
                    self.keyboard_signals.key_k_pressed.emit()
            
            # ESC key check (Stop)
            if keyboard.is_pressed('esc'):
                if current_time - self.last_esc_press > 0.5:
                    self.last_esc_press = current_time
                    self.keyboard_signals.esc_pressed.emit()
        
        except Exception as e:
            print(f"Keyboard check error: {e}")
    
    def on_left_click(self, x, y):
        """
        Called when left click is detected
        """
        if self.is_recording:
            # Create timestamp
            current_time = datetime.datetime.now()
            
            # Calculate delay if there was a previous click
            delay_after = 0
            if self.last_click_time:
                delay_after = int((current_time - self.last_click_time).total_seconds() * 1000)
            
            # Update last click time
            self.last_click_time = current_time
            
            # If this is not the first click, set the delay for the previous click
            if len(self.click_actions) > 0:
                self.click_actions[-1].delay_after = delay_after
                # Update list view
                self.update_click_list()
            
            # Save new click
            click_action = ClickAction(x, y, is_right_click=False, timestamp=current_time)
            self.click_actions.append(click_action)
            print(f"Left click recorded: X:{x}, Y:{y}, Delay from previous: {delay_after}ms")
            
            self.update_click_list()
            self.update_status()
    
    def on_right_click(self, x, y):
        """
        Called when right click is detected
        """
        if self.is_recording:
            # Create timestamp
            current_time = datetime.datetime.now()
            
            # Calculate delay if there was a previous click
            delay_after = 0
            if self.last_click_time:
                delay_after = int((current_time - self.last_click_time).total_seconds() * 1000)
            
            # Update last click time
            self.last_click_time = current_time
            
            # If this is not the first click, set the delay for the previous click
            if len(self.click_actions) > 0:
                self.click_actions[-1].delay_after = delay_after
                # Update list view
                self.update_click_list()
            
            # Save new click
            click_action = ClickAction(x, y, is_right_click=True, timestamp=current_time)
            self.click_actions.append(click_action)
            print(f"Right click recorded: X:{x}, Y:{y}, Delay from previous: {delay_after}ms")
            
            self.update_click_list()
            self.update_status()
    
    @pyqtSlot()
    def on_key_c_pressed(self):
        """
        Called when C key is pressed - Starts playback
        """
        print("C key pressed, starting playback")
        self.start_playback()
    
    @pyqtSlot()
    def on_key_b_pressed(self):
        """
        Called when B key is pressed - Stops recording
        """
        print("B key pressed, stopping recording")
        self.stop_recording()
    
    @pyqtSlot()
    def on_key_k_pressed(self):
        """
        Called when K key is pressed - Starts recording
        """
        print("K key pressed, starting recording")
        self.start_recording()
    
    @pyqtSlot()
    def on_esc_pressed(self):
        """
        Called when ESC key is pressed - Stops playback or recording
        """
        if self.is_playing:
            print("ESC key pressed, stopping playback")
            self.stop_playback()
        elif self.is_recording:
            print("ESC key pressed, stopping recording")
            self.stop_recording()
    
    def start_recording(self):
        """
        Starts recording mouse clicks
        """
        if self.is_recording or self.is_playing:
            return
        
        # Start recording mode
        self.is_recording = True
        self.last_click_time = None  # Reset last click time
        self.status_label.setText(TEXTS[self.current_language]['status_recording'])
        
        # Update button states
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
        self.play_button.setEnabled(False)
        
        # Start mouse listening
        self.mouse_listener.start_listening()
        
        # Show info message to user
        show_auto_close_info(self, "Recording Started", 
                           "Mouse clicks are being recorded...\n\n"
                           "All left and right clicks and delays between them will be recorded.\n\n"
                           "Press 'B' or click 'Stop Recording' to finish.")
    
    def stop_recording(self):
        """
        Stops recording mouse clicks
        """
        if not self.is_recording:
            return
            
        # Stop recording mode
        self.is_recording = False
        self.last_click_time = None  # Reset last click time
        self.status_label.setText(TEXTS[self.current_language]['status_completed'])
        
        # Stop mouse listening
        self.mouse_listener.stop_listening()
        
        # Show info message to user
        if len(self.click_actions) > 0:
            # Don't show delay info for last click
            if len(self.click_actions) > 0:
                self.click_actions[-1].delay_after = 0
                self.update_click_list()
                
            show_auto_close_info(self, "Recording Completed", 
                               f"Total {len(self.click_actions)} clicks and delays recorded.\n\n"
                               "Press 'C' or click 'Play' to start playback.")
        else:
            show_auto_close_warning(self, "Warning", 
                                  "No clicks recorded!\n\n"
                                  "Please try recording again.")
    
    def update_click_list(self):
        """
        Updates the click list view
        """
        self.click_list.clear()
        for i, action in enumerate(self.click_actions):
            self.click_list.addItem(f"{i+1}. {action}")
    
    def update_status(self):
        """
        Updates the interface status
        """
        self.coordinates_label.setText(f"Recorded clicks: {len(self.click_actions)}")
    
    def start_playback(self):
        """
        Starts playing back recorded clicks
        """
        # Check for valid clicks
        if len(self.click_actions) == 0:
            show_auto_close_warning(self, "Warning", "You need to record clicks before playing!")
            return
        
        if self.is_playing or self.is_recording:
            return
        
        self.is_playing = True
        
        delay_info = "with real delays" if self.use_recorded_delays else "with fixed delay"
        repeat_text = "repeating" if self.repeat_playback else "once"
        self.status_label.setText(f"Playing... ({repeat_text}, {delay_info})")
        
        # Show info message to user (auto-closing)
        show_auto_close_info(self, "Playback Started", 
                           f"{len(self.click_actions)} clicks will be performed in sequence.\n\n"
                           f"Playback mode: {'Repeating' if self.repeat_playback else 'Single play'}\n\n"
                           f"Delays: {'Using original recorded delays' if self.use_recorded_delays else 'Fixed 250ms'}\n\n"
                           "Press 'Stop' button or ESC key to stop.")
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self.play_actions, daemon=True)
        self.playback_thread.start()
    
    def play_actions(self):
        """
        Plays back recorded clicks
        """
        try:
            # Repeat or single play
            do_repeat = self.repeat_playback
            
            while self.is_playing:
                for i, action in enumerate(self.click_actions):
                    if not self.is_playing:
                        break
                    
                    try:
                        print(f"Performing click {i+1}: {'Right' if action.is_right_click else 'Left'} click ({action.x}, {action.y})")
                        
                        # Select function based on click type
                        if action.is_right_click:
                            success = rightclick(action.x, action.y)
                        else:
                            success = leftclick(action.x, action.y)
                        
                        if not success:
                            print(f"Click {i+1} failed")
                        
                        # Wait between actions - either recorded delay or fixed value
                        if self.use_recorded_delays and i < len(self.click_actions) - 1:
                            delay = action.delay_after
                            if delay > 0:
                                print(f"Waiting for recorded delay: {delay}ms")
                                time.sleep(delay / 1000.0)  # Convert ms to seconds
                            else:
                                # If delay is 0, use minimum wait
                                time.sleep(0.05)
                        else:
                            # Use fixed delay
                            time.sleep(0.25)  # 250ms
                    except Exception as e:
                        print(f"Click {i+1} error: {e}")
                
                # Check repeat option
                if not do_repeat:
                    print("Single play completed")
                    self.is_playing = False
                    # Update status in main thread
                    try:
                        QApplication.instance().postEvent(self, StatusUpdateEvent())
                    except Exception as e:
                        print(f"Status update error: {e}")
                    break
                
                # Wait before next cycle in repeat mode
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
    
    # Olay işleme (Event processing)
    def event(self, event):
        """
        Custom event handling
        """
        if event.type() == StatusUpdateEvent.EVENT_TYPE:
            self.status_label.setText(TEXTS[self.current_language]['status_completed'])
            return True
        return super().event(event)
    
    def stop_playback(self):
        """
        Stops playback
        """
        if self.is_playing:
            self.is_playing = False
            self.status_label.setText(TEXTS[self.current_language]['status_stopped'])
            print("Click playback stopped")
    
    def reset_recording(self):
        """
        Clears recorded clicks
        """
        if self.is_recording or self.is_playing:
            show_auto_close_warning(self, "Warning", "Cannot reset while recording or playing!")
            return
            
        if not self.click_actions:
            return  # Already empty
            
        result = QMessageBox.question(self, "Reset Confirmation", 
                                     "All click recordings will be deleted. Are you sure?",
                                     QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.No:
            return
            
        self.click_actions = []
        self.is_playing = False
        self.is_recording = False
        self.update_click_list()
        self.update_status()
        
        self.status_label.setText("All click recordings cleared")
        show_auto_close_info(self, "Reset Completed", "All click recordings have been cleared.")

    def toggle_use_delays(self, state):
        """
        Toggles use of recorded delays
        """
        self.use_recorded_delays = state == Qt.Checked
        print(f"Using recorded delays: {'enabled' if self.use_recorded_delays else 'disabled'}")

    def save_settings(self, profile_name=None):
        """
        Saves click data and settings to INI file
        """
        try:
            config = configparser.ConfigParser()
            
            # Read existing INI file if it exists
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
                
            # Set profile name
            if profile_name:
                self.current_profile_name = profile_name
                
            # General settings section
            if 'Settings' not in config:
                config['Settings'] = {}
                
            # Save last used profile name
            config['Settings']['last_profile'] = self.current_profile_name
            
            # Profile section
            section_name = f"Profile_{self.current_profile_name}"
            if section_name not in config:
                config[section_name] = {}
                
            # Convert click data to JSON format
            click_data = [click_action_to_dict(action) for action in self.click_actions]
            config[section_name]['click_data'] = json.dumps(click_data)
            
            # Save repeat setting
            config[section_name]['repeat'] = str(int(self.repeat_playback))
            
            # Save delay usage setting
            config[section_name]['use_delays'] = str(int(self.use_recorded_delays))
            
            # Save to file
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
                
            print(f"Settings saved to '{CONFIG_FILE}'. Profile: {self.current_profile_name}")
            return True
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            show_auto_close_warning(self, "Error", f"Could not save settings: {e}")
            return False

    def load_settings(self, profile_name=None):
        """
        Loads click data and settings from INI file
        """
        try:
            if not os.path.exists(CONFIG_FILE):
                print(f"'{CONFIG_FILE}' file not found.")
                return False
                
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            
            # Determine profile name
            if profile_name is None:
                # If no profile name specified, use last used profile
                if 'Settings' in config and 'last_profile' in config['Settings']:
                    profile_name = config['Settings']['last_profile']
                else:
                    profile_name = "default"
            
            # Check profile section
            section_name = f"Profile_{profile_name}"
            if section_name not in config:
                print(f"'{profile_name}' profile not found.")
                return False
                
            # Set profile name
            self.current_profile_name = profile_name
            
            # Load click data
            if 'click_data' in config[section_name]:
                click_data = json.loads(config[section_name]['click_data'])
                
                # Clear previous click data
                self.click_actions = []
                
                # Convert click data to objects
                for data in click_data:
                    self.click_actions.append(dict_to_click_action(data))
                
                # Update list view
                self.update_click_list()
                self.update_status()
            
            # Load repeat setting
            if 'repeat' in config[section_name]:
                self.repeat_playback = bool(int(config[section_name]['repeat']))
                self.repeat_checkbox.setChecked(self.repeat_playback)
            
            # Load delay usage setting
            if 'use_delays' in config[section_name]:
                self.use_recorded_delays = bool(int(config[section_name]['use_delays']))
                self.use_delays_checkbox.setChecked(self.use_recorded_delays)
                
            print(f"'{profile_name}' profile loaded successfully.")
            
            # Notify user
            click_count = len(self.click_actions)
            if click_count > 0:
                self.status_label.setText(f"'{profile_name}' profile loaded - {click_count} clicks")
                show_auto_close_info(self, "Profile Loaded", 
                                  f"'{profile_name}' profile loaded successfully.\n\n"
                                  f"Total {click_count} clicks loaded.")
            else:
                self.status_label.setText(f"'{profile_name}' profile loaded (empty)")
                
            return True
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            show_auto_close_warning(self, "Error", f"Could not load settings: {e}")
            return False

    def save_profile(self):
        """
        Saves click data and settings to a profile
        """
        profile_name = self.profile_name_input.text().strip()
        
        # Check profile name
        if not profile_name:
            show_auto_close_warning(self, "Warning", "Please enter a valid profile name.")
            return
            
        # Check data
        if not self.click_actions:
            result = QMessageBox.question(self, "Empty Profile", 
                                         "No clicks recorded. Save empty profile?",
                                         QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.No:
                return
        
        # Save settings
        if self.save_settings(profile_name):
            # Update profile label
            self.current_profile_name = profile_name
            self.profile_label.setText(f"Active Profile: {self.current_profile_name}")
            
            # Notify user
            self.status_label.setText(f"'{profile_name}' profile saved")
            show_auto_close_info(self, "Save Successful", 
                              f"'{profile_name}' profile saved successfully.\n\n"
                              f"Total {len(self.click_actions)} clicks saved.")
    
    def load_profile(self):
        """
        Loads click data and settings from specified profile
        """
        profile_name = self.profile_name_input.text().strip()
        
        # Check profile name
        if not profile_name:
            show_auto_close_warning(self, "Warning", "Please enter a valid profile name.")
            return
            
        # Ask if current data exists
        if self.click_actions:
            result = QMessageBox.question(self, "Current Data", 
                                         "Current clicks will be deleted. Continue?",
                                         QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.No:
                return
        
        # Load profile
        if self.load_settings(profile_name):
            # Update profile label
            self.profile_label.setText(f"Active Profile: {self.current_profile_name}")
        else:
            # Notify user if loading failed
            show_auto_close_warning(self, "Load Error", 
                                 f"Could not load '{profile_name}' profile or profile not found.")
            
    def show_language_dialog(self):
        """
        Shows language selection dialog
        """
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Language Selection / Dil Seçimi")
        dialog.setText("Please select your language / Lütfen dilinizi seçin")
        
        # Create buttons
        en_button = dialog.addButton("English", QMessageBox.ActionRole)
        tr_button = dialog.addButton("Türkçe", QMessageBox.ActionRole)
        
        dialog.exec_()
        
        # Set language based on button clicked
        if dialog.clickedButton() == en_button:
            self.current_language = 'en'
        else:
            self.current_language = 'tr'
            
        # Update UI with selected language
        self.update_language()

    def update_language(self):
        """
        Updates all UI elements with current language
        """
        texts = TEXTS[self.current_language]
        
        # Update window title
        self.setWindowTitle(texts['window_title'])
        
        # Update status label
        self.status_label.setText(texts['status_ready'])
        
        # Update buttons
        self.record_button.setText(texts['record_button'])
        self.stop_record_button.setText(texts['stop_record_button'])
        self.play_button.setText(texts['play_button'])
        self.stop_button.setText(texts['stop_button'])
        
        # Update labels
        self.click_list_label.setText(texts['recorded_clicks'])
        self.file_group_label.setText(texts['profile_operations'])
        self.profile_name_label.setText(texts['profile_name'])
        self.options_label.setText(texts['playback_options'])
        self.click_label.setText(texts['click_info'])
        self.version_label.setText(texts['version'])
        
        # Update buttons
        self.save_button.setText(texts['save'])
        self.load_button.setText(texts['load'])
        self.reset_button.setText(texts['reset'])
        
        # Update checkboxes
        self.repeat_checkbox.setText(texts['repeat_playback'])
        self.use_delays_checkbox.setText(texts['use_delays'])
        
        # Update keyboard shortcuts
        self.keyboard_shortcuts_label.setText(texts['keyboard_shortcuts'])

# --- ANA UYGULAMA BAŞLATMA BLOĞU ---
if __name__ == "__main__":
    try:
        print("Uygulama başlatılıyor...")
        app = QApplication(sys.argv)
        window = PointRecorderApp()
        window.show()
        print("Ana pencere gösterildi.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Başlatma hatası: {e}") 