# Nokta Kaydedici (Point Recorder) v0.1

Nokta Kaydedici, ekranda belirli noktaları kaydedip sonrasında bu noktalarda otomatik olarak sağ tıklama yapan basit bir otomasyon uygulamasıdır.

## Özellikler

- İki farklı ekran noktasını kaydetme
- Kaydedilen noktalarda otomatik sağ tıklama yapma
- Tek seferlik veya sürekli tekrarlama seçeneği
- Klavye kısayolları ile kolay kullanım
- Windows sistemlerde win32api ile gerçek sağ tıklama operasyonu

## Teknik Detaylar

Program PyQt5 kullanarak geliştirilmiş bir arayüze sahiptir ve şu özellikler ile çalışır:

- Klavye izleme için `keyboard` kütüphanesi kullanılır
- Sağ tıklama işlemleri için `win32api` kullanılır
- Ekran koordinatları ile çalışmak için `pyautogui` kullanılır
- Çoklu thread desteği sayesinde arayüz kilitlenmeden arka planda işlemler yapılabilir

## Kullanım

1. Uygulamayı başlatın
2. "1. Noktayı Kaydet" butonuna tıklayarak veya "1" tuşuna basarak ilk noktayı kaydedin
3. "2. Noktayı Kaydet" butonuna tıklayarak veya "2" tuşuna basarak ikinci noktayı kaydedin
4. İsterseniz "Sürekli tekrarla" seçeneğini işaretleyin
5. "Oynat" butonuna tıklayarak veya "C" tuşuna basarak kaydedilmiş noktaları oynatın
6. Durdurmak için "Durdur" butonunu kullanın veya "ESC" tuşuna basın

## Klavye Kısayolları

- **1** tuşu: 1. noktayı kaydet
- **2** tuşu: 2. noktayı kaydet
- **C** tuşu: Oynat
- **ESC** tuşu: Durdur

## Gereksinimler

- Python 3.6 veya üzeri
- PyQt5
- pyautogui
- keyboard
- pywin32

## Kurulum

```
pip install PyQt5 pyautogui keyboard pywin32
python point_recorder.py
```

## Notlar

- Program çalışırken kaydedilen noktalar arayüzde gösterilir
- Oynatma durdurulana kadar veya program kapatılana kadar devam eder
- Otomatik sağ tıklama yapıldığı için oynatma sırasında fareyi kullanmamaya dikkat edin

## Güvenlik

- `pyautogui.FAILSAFE = False` ile güvenlik önlemesi devre dışı bırakılmıştır, bu nedenle oynatma sırasında dikkatli olun
- Program sadece geliştirme ve test amaçlıdır, kötüye kullanımdan kullanıcı sorumludur

## Lisans

Bu yazılım açık kaynak olarak MIT lisansı altında dağıtılmaktadır.

## Geliştirici

Point Recorder ekibi tarafından geliştirilmiştir. 