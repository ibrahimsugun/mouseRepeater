import sys
import time
import threading
import pyautogui
import keyboard
import warnings
import win32api
import win32con

# PyQt5 uyarılarını bastır
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QWidget, QLabel, QHBoxLayout, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QTimer, QEvent

# PyAutoGUI failsafe özelliğini devre dışı bırak
pyautogui.FAILSAFE = False

# Klavye olaylarını işlemek için sinyal sınıfı
class KeyboardSignals(QObject):
    key1_pressed = pyqtSignal()
    key2_pressed = pyqtSignal()
    key_c_pressed = pyqtSignal()  # C tuşu için sinyal eklendi
    esc_pressed = pyqtSignal()

# Özel olay sınıfı
class StatusUpdateEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self):
        super(StatusUpdateEvent, self).__init__(self.EVENT_TYPE)

# Otomatik kapanan mesaj kutusu sınıfı
class AutoCloseMessageBox(QMessageBox):
    def __init__(self, *args, **kwargs):
        super(AutoCloseMessageBox, self).__init__(*args, **kwargs)
        # 2 saniye sonra kapanacak timer oluştur
        self.timeout = 2  # saniye
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(self.timeout * 1000)  # ms cinsinden
        
        # Timer'ın kalan süresini göster
        self.countdown_label = QLabel(f"Bu mesaj {self.timeout} saniye sonra kapanacak", self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.countdown_label, self.layout().rowCount(), 0, 1, self.layout().columnCount())

# Sağ tıklama fonksiyonu (win32api kullanarak)
def rightclick(x, y):
    """
    win32api kullanarak sağ tıklama yapar
    """
    try:
        # Fare imlecini konumlandır
        win32api.SetCursorPos((x, y))
        # Kısa bekleme
        time.sleep(0.05)
        # Sağ tuşa basma olayı
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
        # Basma ve bırakma arasında bekleme
        time.sleep(0.1)
        # Sağ tuşu bırakma olayı
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
        print(f"Sağ tıklama yapıldı: X:{x}, Y:{y}")
        return True
    except Exception as e:
        print(f"Sağ tıklama hatası: {e}")
        return False

# Otomatik kapanan bilgi mesajı göster
def show_auto_close_info(parent, title, message):
    msg_box = AutoCloseMessageBox(QMessageBox.Information, title, message, QMessageBox.Ok, parent)
    msg_box.exec_()
    
# Otomatik kapanan uyarı mesajı göster
def show_auto_close_warning(parent, title, message):
    msg_box = AutoCloseMessageBox(QMessageBox.Warning, title, message, QMessageBox.Ok, parent)
    msg_box.exec_()

class PointRecorderApp(QMainWindow):
    """
    Mouse tıklamalarını kaydeden ve oynatan basit uygulama
    """
    def __init__(self):
        super().__init__()
        
        # Uygulama durumu
        self.coordinates = []
        self.is_playing = False
        self.playback_thread = None
        self.repeat_playback = False  # Tekrarlama seçeneği
        
        # Klavye sinyalleri
        self.keyboard_signals = KeyboardSignals()
        self.keyboard_signals.key1_pressed.connect(self.on_key1_pressed)
        self.keyboard_signals.key2_pressed.connect(self.on_key2_pressed)
        self.keyboard_signals.key_c_pressed.connect(self.on_key_c_pressed)  # C tuşu için bağlantı
        self.keyboard_signals.esc_pressed.connect(self.on_esc_pressed)
        
        # Klavye olaylarını izleme için son tuş basma zamanları
        self.last_key1_press = 0
        self.last_key2_press = 0
        self.last_key_c_press = 0  # C tuşu için son basma zamanı
        self.last_esc_press = 0
        
        # Arayüz
        self.init_ui()
        
        # Klavye izleme için timer başlat
        self.start_keyboard_timer()
    
    def init_ui(self):
        """
        Kullanıcı arayüzünü oluşturur
        """
        self.setWindowTitle("Nokta Kaydedici")
        self.setGeometry(100, 100, 400, 380)
        
        # Ana widget ve layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # Durum etiketi
        self.status_label = QLabel("Hazır - Kaydetmek için butonları kullanın")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)
        
        # Koordinat bilgisi
        self.coordinates_label = QLabel("Kaydedilen noktalar: 0/2")
        self.coordinates_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.coordinates_label)
        
        # Kısayol açıklaması
        self.keyboard_label = QLabel("1 tuşu: 1. noktayı kaydet | 2 tuşu: 2. noktayı kaydet | C tuşu: Oynat")
        self.keyboard_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.keyboard_label)
        
        # Kayıt butonları
        self.record_layout = QHBoxLayout()
        
        # İlk nokta için kayıt butonu
        self.record1_button = QPushButton("1. Noktayı Kaydet (1)")
        self.record1_button.clicked.connect(lambda: self.record_point(0))
        self.record_layout.addWidget(self.record1_button)
        
        # İkinci nokta için kayıt butonu
        self.record2_button = QPushButton("2. Noktayı Kaydet (2)")
        self.record2_button.clicked.connect(lambda: self.record_point(1))
        self.record_layout.addWidget(self.record2_button)
        
        self.main_layout.addLayout(self.record_layout)
        
        # Tekrar seçeneği
        self.repeat_checkbox = QCheckBox("Sürekli tekrarla")
        self.repeat_checkbox.setChecked(False)
        self.repeat_checkbox.stateChanged.connect(self.toggle_repeat)
        self.main_layout.addWidget(self.repeat_checkbox)
        
        # Kontrol butonları
        self.buttons_layout = QHBoxLayout()
        
        # Oynat butonu
        self.play_button = QPushButton("Oynat (C)")
        self.play_button.clicked.connect(self.start_playback)
        self.buttons_layout.addWidget(self.play_button)
        
        # Durdur butonu
        self.stop_button = QPushButton("Durdur")
        self.stop_button.clicked.connect(self.stop_playback)
        self.buttons_layout.addWidget(self.stop_button)
        
        # Sıfırla butonu
        self.reset_button = QPushButton("Sıfırla")
        self.reset_button.clicked.connect(self.reset_coordinates)
        self.buttons_layout.addWidget(self.reset_button)
        
        self.main_layout.addLayout(self.buttons_layout)
        
        # Tıklama açıklaması
        self.click_label = QLabel("Program kaydedilen noktalarda otomatik SAĞ TIK yapar (win32api)")
        self.click_label.setAlignment(Qt.AlignCenter)
        font = self.click_label.font()
        font.setBold(True)
        self.click_label.setFont(font)
        self.main_layout.addWidget(self.click_label)
        
        # Klavye kısayolu açıklaması
        self.shortcut_label = QLabel("ESC tuşu programı durdurur")
        self.shortcut_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.shortcut_label)
    
    def toggle_repeat(self, state):
        """
        Tekrarlama seçeneğini açıp kapatır
        """
        self.repeat_playback = state == Qt.Checked
        print(f"Tekrarlama {'açık' if self.repeat_playback else 'kapalı'}")
    
    def start_keyboard_timer(self):
        """
        Klavye tuşlarını kontrol etmek için timer başlatır
        """
        self.keyboard_timer = QTimer(self)
        self.keyboard_timer.timeout.connect(self.check_keyboard)
        self.keyboard_timer.start(100)  # 100ms aralıklarla kontrol et
    
    def check_keyboard(self):
        """
        Klavye tuşlarını kontrol eder ve sinyalleri yayınlar
        """
        try:
            current_time = time.time()
            
            # 1 tuşu kontrolü
            if keyboard.is_pressed('1'):
                if current_time - self.last_key1_press > 0.5:
                    self.last_key1_press = current_time
                    self.keyboard_signals.key1_pressed.emit()
            
            # 2 tuşu kontrolü
            if keyboard.is_pressed('2'):
                if current_time - self.last_key2_press > 0.5:
                    self.last_key2_press = current_time
                    self.keyboard_signals.key2_pressed.emit()
            
            # C tuşu kontrolü
            if keyboard.is_pressed('c'):
                if current_time - self.last_key_c_press > 0.5:
                    self.last_key_c_press = current_time
                    self.keyboard_signals.key_c_pressed.emit()
            
            # ESC tuşu kontrolü
            if keyboard.is_pressed('esc'):
                if current_time - self.last_esc_press > 0.5:
                    self.last_esc_press = current_time
                    self.keyboard_signals.esc_pressed.emit()
        
        except Exception as e:
            print(f"Klavye kontrol hatası: {e}")
    
    @pyqtSlot()
    def on_key1_pressed(self):
        """
        1 tuşuna basılınca çağrılır
        """
        print("1 tuşuna basıldı, 1. nokta kaydediliyor")
        self.record_point(0)
    
    @pyqtSlot()
    def on_key2_pressed(self):
        """
        2 tuşuna basılınca çağrılır
        """
        print("2 tuşuna basıldı, 2. nokta kaydediliyor")
        self.record_point(1)
    
    @pyqtSlot()
    def on_key_c_pressed(self):
        """
        C tuşuna basılınca çağrılır - Oynatma başlatır
        """
        print("C tuşuna basıldı, oynatma başlatılıyor")
        self.start_playback()
    
    @pyqtSlot()
    def on_esc_pressed(self):
        """
        ESC tuşuna basılınca çağrılır
        """
        if self.is_playing:
            print("ESC tuşuna basıldı, oynatma durduruldu")
            self.stop_playback()
    
    def record_point(self, index):
        """
        Belirtilen indekste fare konumunu kaydeder
        """
        try:
            # Mevcut fare konumunu al
            x, y = win32api.GetCursorPos()  # win32api kullanarak fare konumunu al
            
            # Koordinat listesini boyutlandır
            while len(self.coordinates) <= index:
                self.coordinates.append(None)
            
            # Koordinatı kaydet
            self.coordinates[index] = (x, y)
            
            # Kullanıcıya bildir (otomatik kapanan mesaj kutusu ile)
            show_auto_close_info(self, "Nokta Kaydedildi", 
                               f"Nokta {index+1} kaydedildi: ({x}, {y})\n\n"
                               f"Bu noktada SAĞ TIK yapılacak.")
            
            # Durum etiketini güncelle
            self.update_status()
            
        except Exception as e:
            print(f"Kayıt hatası: {e}")
            show_auto_close_warning(self, "Hata", f"Kayıt sırasında hata: {e}")
    
    def update_status(self):
        """
        Arayüz durumunu günceller
        """
        count = sum(1 for c in self.coordinates if c is not None)
        self.coordinates_label.setText(f"Kaydedilen noktalar: {count}/2")
        
        if count == 0:
            self.status_label.setText("Hazır - Kaydetmek için butonları kullanın")
        elif count < 2:
            self.status_label.setText("1 nokta kaydedildi - İkinci noktayı kaydedin")
        else:
            self.status_label.setText("2 nokta kaydedildi - Oynat'a basabilirsiniz")
    
    def start_playback(self):
        """
        Kaydedilen koordinatlarda sağ tıklama yapmayı başlatır
        """
        # Geçerli koordinat kontrolü
        valid_coords = [c for c in self.coordinates if c is not None]
        if len(valid_coords) == 0:
            show_auto_close_warning(self, "Uyarı", "Oynatmak için en az bir nokta kaydedin!")
            return
        
        if self.is_playing:
            return
        
        self.is_playing = True
        
        tekrar_metni = "tekrarlı" if self.repeat_playback else "bir kez"
        self.status_label.setText(f"Oynatılıyor... SAĞ TIK ({tekrar_metni})")
        
        # Kullanıcıya bilgilendirme mesajı (otomatik kapanan)
        show_auto_close_info(self, "Oynatma Başladı", 
                           f"{len(valid_coords)} noktada sırayla SAĞ TIK yapılacak.\n\n"
                           f"Oynatma modu: {'Tekrarlı' if self.repeat_playback else 'Tek sefer'}\n\n"
                           f"Tıklama yöntemi: win32api (düşük seviyeli)\n\n"
                           "Durdurmak için 'Durdur' düğmesine veya ESC tuşuna basın.")
        
        # Oynatma thread'ini başlat
        self.playback_thread = threading.Thread(target=self.play_coordinates, 
                                              args=(valid_coords,), daemon=True)
        self.playback_thread.start()
    
    def play_coordinates(self, valid_coords):
        """
        Kaydedilen noktalarda sağ tıklama yapar
        """
        try:
            # Tekrarlı veya tek seferlik oynatma
            do_repeat = self.repeat_playback
            
            while self.is_playing:
                for i, (x, y) in enumerate(valid_coords):
                    if not self.is_playing:
                        break
                    
                    try:
                        print(f"Nokta {i+1}'de SAĞ TIK yapılıyor: ({x}, {y})")
                        
                        # win32api ile sağ tıklama yap
                        success = rightclick(x, y)
                        
                        if not success:
                            print(f"Nokta {i+1} için sağ tıklama başarısız oldu")
                        
                        # İşlemler arası bekleme
                        time.sleep(0.7)
                    except Exception as e:
                        print(f"Nokta {i+1} tıklama hatası: {e}")
                
                # Tekrarlama seçeneği kontrol edilir
                if not do_repeat:
                    print("Tek seferlik oynatma tamamlandı")
                    self.is_playing = False
                    # Ana thread'de durum güncelleme - Düzeltilmiş sürüm
                    try:
                        QApplication.instance().postEvent(self, StatusUpdateEvent())
                    except Exception as e:
                        print(f"Durum güncelleme hatası: {e}")
                    break
                
                # Tekrarlama durumunda bir sonraki döngüye geçmeden önce biraz bekle
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Oynatma hatası: {e}")
            self.is_playing = False
    
    # Olay işleme (Event processing)
    def event(self, event):
        """
        Özel olay işleme
        """
        if event.type() == StatusUpdateEvent.EVENT_TYPE:
            self.status_label.setText("Oynatma tamamlandı")
            return True
        return super().event(event)
    
    def stop_playback(self):
        """
        Oynatma işlemini durdurur
        """
        if self.is_playing:
            self.is_playing = False
            self.status_label.setText("Oynatma durduruldu")
            print("Sağ tıklama işlemi durduruldu")
    
    def reset_coordinates(self):
        """
        Kaydedilen noktaları temizler
        """
        self.coordinates = []
        self.is_playing = False
        self.update_status()
        
        show_auto_close_info(self, "Bilgi", "Tüm noktalar silindi")

# Ana uygulama
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = PointRecorderApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Hata oluştu: {e}") 