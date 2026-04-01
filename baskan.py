import os
import sys
import json
import time
import threading
import subprocess
import random
import traceback
import sqlite3
import signal
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from queue import Queue

# ==================== SÜRÜM ====================
VERSION = "2.6.0"

# ==================== KLASÖRLER ====================
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BASKAN_DIR = os.path.join(BASE_DIR, "Baskan")
HAFIZA_DIR = os.path.join(BASKAN_DIR, "Hafiza")
DENETIM_DIR = os.path.join(BASKAN_DIR, "Denetim")
SORULAR_DIR = os.path.join(BASKAN_DIR, "Sorular")
HEDEFLER_DIR = os.path.join(BASKAN_DIR, "Hedefler")
YARDIMCILAR_DIR = os.path.join(BASE_DIR, "Yardimcilar")
LOGS_DIR = os.path.join(BASE_DIR, "Loglar")
HATA_LOG_DIR = os.path.join(LOGS_DIR, "HataLoglari")
AKTIVITE_LOG_DIR = os.path.join(LOGS_DIR, "AktiviteLoglari")
RAPORLAR_DIR = os.path.join(LOGS_DIR, "Raporlar")
DENENEN_KODLAR_DIR = os.path.join(BASE_DIR, "DenenenKodlar")
BASARILI_KODLAR_DIR = os.path.join(DENENEN_KODLAR_DIR, "BasariKodlar")
BASARISIZ_KODLAR_DIR = os.path.join(DENENEN_KODLAR_DIR, "BasarisizKodlar")

# ==================== YENİ JSON KLASÖRLERİ ====================
SORULAR_JSON_DIR = os.path.join(BASE_DIR, "SORULAR")
BILGILER_JSON_DIR = os.path.join(BASE_DIR, "BILGILER")
HEDEFLER_JSON_DIR = os.path.join(BASE_DIR, "HEDEFLER")
DENENEN_KODLAR_JSON_DIR = os.path.join(BASE_DIR, "DENENEN_KODLAR")
BASARILI_KODLAR_JSON_DIR = os.path.join(BASE_DIR, "BASARILI_KODLAR")
BASARISIZ_KODLAR_JSON_DIR = os.path.join(BASE_DIR, "BASARISIZ_KODLAR")
LOGS_JSON_DIR = os.path.join(BASE_DIR, "LOGS")

# ==================== DOSYALAR ====================
PID_FILE = os.path.join(BASKAN_DIR, "baskan.pid")
DURUM_FILE = os.path.join(BASKAN_DIR, "durum.json")
AYAR_DOSYASI = os.path.join(BASKAN_DIR, "baskan_ayarlari.json")
AKTIF_BOTLAR = os.path.join(BASE_DIR, "aktif_botlar.json")
PERFORMANS_DB = os.path.join(DENETIM_DIR, "performans.db")
OGRENME_DB = os.path.join(HAFIZA_DIR, "ogrenme.db")
HEDEFLER_DB = os.path.join(HEDEFLER_DIR, "hedefler.json")
SON_RAPOR_TARIHI = os.path.join(RAPORLAR_DIR, "son_rapor.json")

# ==================== THREAD LOCK ====================
DB_LOCK = threading.Lock()
BOT_LOCK = threading.Lock()
KOD_LOCK = threading.Lock()
JSON_LOCK = threading.Lock()

# ==================== RENKLER ====================
class Renk:
    RESET = "\033[0m"
    KIRMIZI = "\033[91m"
    YESIL = "\033[92m"
    SARI = "\033[93m"
    MAVI = "\033[94m"
    MOR = "\033[95m"
    CYAN = "\033[96m"

def renkli_yaz(mesaj, renk=Renk.RESET):
    print(f"{renk}{mesaj}{Renk.RESET}")

# ==================== HATA LOG ====================
def log_hata(modul, hata, ekstra=None):
    try:
        tarih = datetime.now().strftime("%Y%m%d")
        dosya = os.path.join(HATA_LOG_DIR, f"hata_{tarih}.log")
        os.makedirs(HATA_LOG_DIR, exist_ok=True)
        with open(dosya, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Tarih: {datetime.now().isoformat()}\n")
            f.write(f"Modul: {modul}\n")
            f.write(f"Hata Tipi: {type(hata).__name__}\n")
            f.write(f"Hata: {str(hata)}\n")
            if ekstra:
                f.write(f"Ekstra: {json.dumps(ekstra, ensure_ascii=False)}\n")
            f.write(traceback.format_exc())
    except:
        pass

def log_aktivite(mesaj, seviye="INFO", bot_adi=None):
    try:
        tarih = datetime.now().strftime("%Y%m%d")
        dosya = os.path.join(AKTIVITE_LOG_DIR, f"aktivite_{tarih}.log")
        os.makedirs(AKTIVITE_LOG_DIR, exist_ok=True)
        with open(dosya, "a", encoding="utf-8") as f:
            if bot_adi:
                f.write(f"[{datetime.now().isoformat()}] [{seviye}] [{bot_adi}] {mesaj}\n")
            else:
                f.write(f"[{datetime.now().isoformat()}] [{seviye}] {mesaj}\n")
    except:
        pass

# ==================== QWEN 2.5 7B ENTEGRASYONU ====================
class QwenClient:
    def __init__(self):
        self.model = "qwen2.5:7b"
        self.timeout = 30
        self.max_cevap_sayisi = 10
        self._check_ollama()
    
    def _check_ollama(self):
        try:
            result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
            if result.returncode != 0:
                log_aktivite("Ollama bulunamadi! Qwen kullanilamayacak.", "UYARI")
                renkli_yaz("[!] Ollama kurulu degil! 'pkg install ollama' ile kurun.", Renk.SARI)
        except:
            pass
    
    def _parse_json_cevap(self, raw_output):
        try:
            cevaplar = json.loads(raw_output.strip())
            if isinstance(cevaplar, list) and len(cevaplar) >= 3:
                return cevaplar[:self.max_cevap_sayisi]
        except:
            pass
        satirlar = raw_output.strip().split('\n')
        temiz = [s.strip() for s in satirlar if s.strip() and not s.startswith('{')]
        if len(temiz) >= 3:
            return temiz[:self.max_cevap_sayisi]
        return None
    
    def sor(self, soru, kategori="genel", context=None):
        try:
            prompt = f"""Soru: {soru}
Kategori: {kategori}
Context: {context or "Yok"}

Bu soru için 5-10 farklı, yaratıcı ve kullanışlı cevap üret. 
Her cevap farklı bir açıdan olmalı.
Cevapları JSON array formatında döndür.
Örnek format: ["cevap1", "cevap2", "cevap3"]

Sadece JSON array'ini döndür, başka bir şey yazma."""
            
            cmd = ['ollama', 'run', self.model, prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode == 0 and result.stdout:
                cevaplar = self._parse_json_cevap(result.stdout)
                if cevaplar:
                    return {
                        "cevaplar": cevaplar,
                        "basari_puani": 85,
                        "hata": None,
                        "kaynak": "qwen_coklu"
                    }
            
            return {
                "cevaplar": [f"{soru} hakkinda cevap veriyorum", f"Bu konuyu arastiriyorum", f"Biraz daha detay verir misiniz?"],
                "basari_puani": 50,
                "hata": result.stderr if result.stderr else None,
                "kaynak": "fallback"
            }
        except subprocess.TimeoutExpired:
            return {
                "cevaplar": ["Zaman asimi, tekrar dene", "Lutfen daha sonra tekrar dene", "Sistem yogun, bekleyin"],
                "basari_puani": 0,
                "hata": "Zaman asimi",
                "kaynak": "hata"
            }
        except Exception as e:
            return {
                "cevaplar": [f"Hata: {str(e)}", "Tekrar dene", "Sistem hatasi"],
                "basari_puani": 0,
                "hata": str(e),
                "kaynak": "hata"
            }
    
    def hata_coz(self, hata_detay, context=None):
        soru = f"Bu hatayi nasil cozerim? Hata: {hata_detay}"
        return self.sor(soru, "hata_cozumu", context)
    
    def bot_iyilestir(self, bot_adi, bot_amac, hata_sayisi, kalite_puani):
        soru = f"""Bot iyilestirme:
Bot Adi: {bot_adi}
Bot Amaci: {bot_amac}
Hata Sayisi: {hata_sayisi}
Kalite Puani: {kalite_puani}
Bu botu nasil iyilestirebilirim? 5 farkli oneri ver."""
        return self.sor(soru, "bot_iyilestirme")

# ==================== ÖĞRENME DB ====================
class OgrenmeDB:
    def __init__(self):
        self.db_path = OGRENME_DB
        self._init_db()
    
    def _init_db(self):
        with DB_LOCK:
            try:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS bilgiler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    soru TEXT UNIQUE,
                    cevaplar TEXT,
                    kategori TEXT,
                    kullanilma_sayisi INTEGER DEFAULT 0,
                    basari_puani INTEGER DEFAULT 0,
                    tarih TEXT
                )''')
                c.execute('''CREATE TABLE IF NOT EXISTS ogrenilenler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    konu TEXT,
                    icerik TEXT,
                    kaynak TEXT,
                    tarih TEXT
                )''')
                c.execute('''CREATE TABLE IF NOT EXISTS qwen_cevaplari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    soru TEXT,
                    cevap TEXT,
                    basari_puani INTEGER,
                    tarih TEXT
                )''')
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("OgrenmeDB", e)
    
    def bilgi_ara(self, soru):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("SELECT soru, cevaplar, kullanilma_sayisi FROM bilgiler WHERE soru LIKE ? ORDER BY kullanilma_sayisi DESC LIMIT 5", (f"%{soru}%",))
                sonuc = c.fetchall()
                conn.close()
                if sonuc:
                    tum_cevaplar = []
                    for row in sonuc:
                        cevaplar = json.loads(row[1])
                        if isinstance(cevaplar, list):
                            tum_cevaplar.extend(cevaplar)
                        else:
                            tum_cevaplar.append(cevaplar)
                    return tum_cevaplar if tum_cevaplar else None
                return None
            except Exception as e:
                log_hata("OgrenmeDB.bilgi_ara", e, {"soru": soru})
                return None
    
    def bilgi_ekle(self, soru, cevaplar, kategori="genel", basari_puani=70):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                cevaplar_json = json.dumps(cevaplar, ensure_ascii=False)
                c.execute("INSERT OR REPLACE INTO bilgiler (soru, cevaplar, kategori, basari_puani, tarih) VALUES (?, ?, ?, ?, ?)",
                          (soru, cevaplar_json, kategori, basari_puani, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                log_hata("OgrenmeDB.bilgi_ekle", e, {"soru": soru})
                return False
    
    def bilgi_kullan(self, soru):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("UPDATE bilgiler SET kullanilma_sayisi = kullanilma_sayisi + 1 WHERE soru = ?", (soru,))
                conn.commit()
                conn.close()
            except:
                pass
    
    def rastgele_cevap(self, soru):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("SELECT cevaplar FROM bilgiler WHERE soru LIKE ? ORDER BY RANDOM() LIMIT 1", (f"%{soru}%",))
                sonuc = c.fetchone()
                conn.close()
                if sonuc:
                    cevaplar = json.loads(sonuc[0])
                    if isinstance(cevaplar, list):
                        return random.choice(cevaplar)
                    return cevaplar
                return None
            except Exception as e:
                log_hata("OgrenmeDB.rastgele_cevap", e, {"soru": soru})
                return None
    
    def qwen_cevap_kaydet(self, soru, cevaplar, basari_puani):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                for cevap in cevaplar[:10]:
                    c.execute("INSERT INTO qwen_cevaplari (soru, cevap, basari_puani, tarih) VALUES (?, ?, ?, ?)",
                              (soru, cevap, basari_puani, datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("OgrenmeDB.qwen_cevap_kaydet", e)
    
    def ogrenilen_ekle(self, konu, icerik, kaynak="otonom"):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("INSERT INTO ogrenilenler (konu, icerik, kaynak, tarih) VALUES (?, ?, ?, ?)",
                          (konu, icerik, kaynak, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                log_hata("OgrenmeDB.ogrenilen_ekle", e)
                return False

# ==================== SİSTEM KAYNAK ====================
class SistemKaynak:
    _last_total = 0
    _last_idle = 0
    
    @staticmethod
    def cpu_kullanim():
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
                parts = line.split()
                if len(parts) > 4:
                    user = int(parts[1])
                    nice = int(parts[2])
                    system = int(parts[3])
                    idle = int(parts[4])
                    total = user + nice + system + idle
                    
                    if SistemKaynak._last_total == 0:
                        SistemKaynak._last_total = total
                        SistemKaynak._last_idle = idle
                        return 0
                    
                    total_diff = total - SistemKaynak._last_total
                    idle_diff = idle - SistemKaynak._last_idle
                    SistemKaynak._last_total = total
                    SistemKaynak._last_idle = idle
                    
                    if total_diff > 0:
                        return 100 * (total_diff - idle_diff) / total_diff
            return 0
        except:
            return 0
    
    @staticmethod
    def ram_kullanim():
        try:
            total = 0
            available = 0
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal:" in line:
                        total = int(line.split()[1])
                    elif "MemAvailable:" in line:
                        available = int(line.split()[1])
            if total > 0:
                return 100 - (available / total * 100)
            return 0
        except:
            return 0
    
    @staticmethod
    def batarya():
        try:
            result = subprocess.run(['termux-battery-status'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                return {
                    "seviye": data.get('percentage', 100),
                    "durum": data.get('status', 'unknown'),
                    "sicaklik": data.get('temperature', 0) / 10
                }
        except:
            pass
        return {"seviye": 100, "durum": "unknown", "sicaklik": 0}
    
    @staticmethod
    def hepsi():
        return {
            "cpu": SistemKaynak.cpu_kullanim(),
            "ram": SistemKaynak.ram_kullanim(),
            "batarya": SistemKaynak.batarya()["seviye"],
            "sicaklik": SistemKaynak.batarya()["sicaklik"],
            "batarya_durum": SistemKaynak.batarya()["durum"]
        }

# ==================== PERFORMANS DB ====================
class PerformansDB:
    def __init__(self):
        self.db_path = PERFORMANS_DB
        self._init_db()
    
    def _init_db(self):
        with DB_LOCK:
            try:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS bot_performans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_adi TEXT,
                    tarih TEXT,
                    kalite_puani INTEGER,
                    basari_sayisi INTEGER,
                    hata_sayisi INTEGER,
                    restart_sayisi INTEGER DEFAULT 0,
                    calisma_suresi REAL
                )''')
                c.execute('''CREATE TABLE IF NOT EXISTS sistem_performans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tarih TEXT,
                    cpu_kullanim REAL,
                    ram_kullanim REAL,
                    batarya INTEGER,
                    sicaklik REAL,
                    aktif_bot INTEGER,
                    kritik_uyari INTEGER DEFAULT 0
                )''')
                c.execute('''CREATE TABLE IF NOT EXISTS bot_calisma_saatleri (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_adi TEXT,
                    tarih TEXT,
                    calisma_suresi REAL,
                    dinlenme_suresi REAL,
                    gorev_sayisi INTEGER DEFAULT 0
                )''')
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("PerformansDB", e)
    
    def bot_kaydet(self, bot_adi, kalite, basari, hata, restart=0, sure=0):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("INSERT INTO bot_performans (bot_adi, tarih, kalite_puani, basari_sayisi, hata_sayisi, restart_sayisi, calisma_suresi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (bot_adi, datetime.now().isoformat(), kalite, basari, hata, restart, sure))
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("PerformansDB.bot_kaydet", e)
    
    def sistem_kaydet(self, cpu, ram, batarya, sicaklik, aktif, kritik=0):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("INSERT INTO sistem_performans (tarih, cpu_kullanim, ram_kullanim, batarya, sicaklik, aktif_bot, kritik_uyari) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (datetime.now().isoformat(), cpu, ram, batarya, sicaklik, aktif, kritik))
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("PerformansDB.sistem_kaydet", e)
    
    def bot_ortalama(self, bot_adi):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("SELECT AVG(kalite_puani) FROM bot_performans WHERE bot_adi = ? AND tarih >= date('now', '-7 days')", (bot_adi,))
                sonuc = c.fetchone()
                conn.close()
                return sonuc[0] if sonuc and sonuc[0] else 50
            except:
                return 50
    
    def bot_calisma_kaydet(self, bot_adi, calisma_suresi, dinlenme_suresi=0, gorev_sayisi=0):
        with DB_LOCK:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                c = conn.cursor()
                c.execute("INSERT INTO bot_calisma_saatleri (bot_adi, tarih, calisma_suresi, dinlenme_suresi, gorev_sayisi) VALUES (?, ?, ?, ?, ?)",
                          (bot_adi, datetime.now().isoformat(), calisma_suresi, dinlenme_suresi, gorev_sayisi))
                conn.commit()
                conn.close()
            except Exception as e:
                log_hata("PerformansDB.bot_calisma_kaydet", e)

# ==================== BOT THREAD SINIFI ====================
class BotThread(threading.Thread):
    def __init__(self, bot_adi, kod_dosyasi, timeout=60):
        super().__init__(daemon=True)
        self.bot_adi = bot_adi
        self.kod_dosyasi = kod_dosyasi
        self.timeout = timeout
        self.stop_event = threading.Event()
        self.result = None
        self.error = None
        self.calisma_suresi = 0
        self.dinlenme_suresi = 0
        self.gorev_sayisi = 0
    
    def run(self):
        try:
            log_aktivite(f"Bot thread baslatildi", "INFO", self.bot_adi)
            baslangic = time.time()
            
            p = subprocess.Popen(
                [sys.executable, self.kod_dosyasi],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = p.communicate(timeout=self.timeout)
                self.calisma_suresi = time.time() - baslangic
                self.gorev_sayisi += 1
                
                if p.returncode == 0:
                    self.result = stdout.strip() if stdout else "Basariyla tamamlandi"
                    log_aktivite(f"Bot basariyla tamamlandi ({self.calisma_suresi:.1f}s)", "INFO", self.bot_adi)
                else:
                    self.error = stderr.strip() if stderr else "Bilinmeyen hata"
                    log_aktivite(f"Bot hata verdi: {self.error}", "HATA", self.bot_adi)
                    
            except subprocess.TimeoutExpired:
                p.kill()
                self.error = "Zaman asimi"
                self.calisma_suresi = self.timeout
                log_aktivite(f"Bot zaman asimina ugradi", "HATA", self.bot_adi)
            
            saat = datetime.now().hour
            if 0 <= saat < 6:
                self.dinlenme_suresi = 120
            elif 6 <= saat < 12:
                self.dinlenme_suresi = 60
            elif 12 <= saat < 18:
                self.dinlenme_suresi = 90
            else:
                self.dinlenme_suresi = 60
            
            if self.dinlenme_suresi > 0:
                time.sleep(self.dinlenme_suresi)
                
        except Exception as e:
            self.error = str(e)
            log_hata("BotThread.run", e, {"bot": self.bot_adi})
        
        log_aktivite(f"Bot thread bitti", "INFO", self.bot_adi)
    
    def stop(self):
        self.stop_event.set()

# ==================== BOT ŞABLONLARI ====================
BOT_TEMPLATES = {
    "kodlama": '''#!/usr/bin/env python3
import os, json, random
from datetime import datetime
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BOT_ADI = "{bot_adi}"
LOG_DIR = os.path.join(BASE_DIR, "Loglar", "AktiviteLoglari")
KOD_DIR = os.path.join(BASE_DIR, "DenenenKodlar")
def log(m):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, f"{BOT_ADI}.log"), "a") as f:
            f.write(f"[{datetime.now()}] {m}\\n")
    except: pass
def kod_kaydet(kod, basarili):
    try:
        os.makedirs(KOD_DIR, exist_ok=True)
        klasor = os.path.join(KOD_DIR, "BasariKodlar" if basarili else "BasarisizKodlar")
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, f"{BOT_ADI}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"), "w") as f:
            f.write(kod)
    except: pass
def main():
    log("Kodlama botu baslatildi")
    cevaplar = ["Python kodu yaziyorum", "Hata ayikliyorum", "Yeni fonksiyon ekliyorum", "Kod optimizasyonu yapiyorum", "Dokumantasyon yaziyorum"]
    return random.choice(cevaplar)
if __name__ == "__main__":
    try:
        print(main())
    except Exception as e:
        log(str(e))
''',
    "sistem": '''#!/usr/bin/env python3
import os, json, random
from datetime import datetime
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BOT_ADI = "{bot_adi}"
LOG_DIR = os.path.join(BASE_DIR, "Loglar", "AktiviteLoglari")
def log(m):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, f"{BOT_ADI}.log"), "a") as f:
            f.write(f"[{datetime.now()}] {m}\\n")
    except: pass
def main():
    log("Sistem botu baslatildi")
    cevaplar = ["Sistem kaynaklari kontrol ediliyor", "CPU kullanimi izleniyor", "RAM temizleniyor", "Batarya optimizasyonu yapiliyor", "Sistem guncellemeleri kontrol ediliyor"]
    return random.choice(cevaplar)
if __name__ == "__main__":
    try:
        print(main())
    except Exception as e:
        log(str(e))
''',
    "analiz": '''#!/usr/bin/env python3
import os, json, random
from datetime import datetime
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BOT_ADI = "{bot_adi}"
LOG_DIR = os.path.join(BASE_DIR, "Loglar", "AktiviteLoglari")
def log(m):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, f"{BOT_ADI}.log"), "a") as f:
            f.write(f"[{datetime.now()}] {m}\\n")
    except: pass
def main():
    log("Analiz botu baslatildi")
    cevaplar = ["Veriler analiz ediliyor", "Rapor hazirlaniyor", "Trendler inceleniyor", "Istatistikler hesaplaniyor", "Anomaliler tespit ediliyor"]
    return random.choice(cevaplar)
if __name__ == "__main__":
    try:
        print(main())
    except Exception as e:
        log(str(e))
''',
    "ogrenme": '''#!/usr/bin/env python3
import os, json, random
from datetime import datetime
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BOT_ADI = "{bot_adi}"
LOG_DIR = os.path.join(BASE_DIR, "Loglar", "AktiviteLoglari")
def log(m):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, f"{BOT_ADI}.log"), "a") as f:
            f.write(f"[{datetime.now()}] {m}\\n")
    except: pass
def main():
    log("Ogrenme botu baslatildi")
    cevaplar = ["Yeni bilgi ogreniyorum", "Veri topluyorum", "Hafizaya kaydediyorum", "Qwen'e soru soruyorum", "Ogrenilenleri analiz ediyorum"]
    return random.choice(cevaplar)
if __name__ == "__main__":
    try:
        print(main())
    except Exception as e:
        log(str(e))
'''
}

# ==================== BAŞKAN SINIFI ====================
class Baskan:
    def __init__(self):
        self.calisiyor = False
        self.botlar = []
        self.aktif_botlar = []
        self.bot_threads = {}
        self.bot_restart_sayilari = defaultdict(int)
        self.bot_zamanlari = {}
        self.bot_calisma_sureleri = defaultdict(float)
        self.db = PerformansDB()
        self.ogrenme_db = OgrenmeDB()
        self.qwen = QwenClient()
        self.gorev_kuyrugu = Queue()
        self.ayarlar = self._ayarlari_yukle()
        self.hedefler = self._hedefleri_yukle()
        self._verileri_yukle()
        self._klasorleri_olustur()
        self._son_rapor_kontrol()
        log_aktivite(f"Baskan baslatildi v{VERSION}")
        renkli_yaz(f"[+] Baskan v{VERSION} hazir (Qwen 2.5 7B - Coklu Cevap - Thread Safe)", Renk.YESIL)
    
    def _klasorleri_olustur(self):
        klasorler = [
            BASKAN_DIR, HAFIZA_DIR, DENETIM_DIR, SORULAR_DIR, HEDEFLER_DIR,
            YARDIMCILAR_DIR, LOGS_DIR, HATA_LOG_DIR, AKTIVITE_LOG_DIR, RAPORLAR_DIR,
            DENENEN_KODLAR_DIR, BASARILI_KODLAR_DIR, BASARISIZ_KODLAR_DIR,
            SORULAR_JSON_DIR, BILGILER_JSON_DIR, HEDEFLER_JSON_DIR,
            DENENEN_KODLAR_JSON_DIR, BASARILI_KODLAR_JSON_DIR, BASARISIZ_KODLAR_JSON_DIR, LOGS_JSON_DIR
        ]
        for k in klasorler:
            os.makedirs(k, exist_ok=True)
    
    def _ayarlari_yukle(self):
        if os.path.exists(AYAR_DOSYASI):
            try:
                with open(AYAR_DOSYASI, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "max_bot": 3,
            "min_bot": 1,
            "batarya_limit": 20,
            "hata_duzelt": True,
            "yeni_bot_uret": True,
            "perf_suresi": 30,
            "rapor_suresi": 3600,
            "bot_timeout": 60,
            "qwen_kullan": True,
            "max_restart": 3,
            "max_cevap_sayisi": 10,
            "sistem_kayit_suresi": 300
        }
    
    def _ayarlari_kaydet(self):
        try:
            with open(AYAR_DOSYASI, "w") as f:
                json.dump(self.ayarlar, f, indent=2)
        except:
            pass
    
    def _hedefleri_yukle(self):
        if os.path.exists(HEDEFLER_DB):
            try:
                with open(HEDEFLER_DB, "r") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _hedefleri_kaydet(self):
        try:
            with open(HEDEFLER_DB, "w") as f:
                json.dump(self.hedefler, f, indent=2)
        except:
            pass
    
    def _hedef_ekle(self, hedef, oncelik=5):
        yeni_hedef = {
            "id": hashlib.md5(f"{hedef}{time.time()}".encode()).hexdigest()[:8],
            "hedef": hedef,
            "oncelik": oncelik,
            "durum": "aktif",
            "tarih": datetime.now().isoformat(),
            "tamamlanma": None
        }
        self.hedefler.append(yeni_hedef)
        self._hedefleri_kaydet()
        
        # JSON olarak da kaydet
        with JSON_LOCK:
            try:
                json_dosya = os.path.join(HEDEFLER_JSON_DIR, f"hedef_{yeni_hedef['id']}.json")
                with open(json_dosya, "w", encoding="utf-8") as f:
                    json.dump(yeni_hedef, f, ensure_ascii=False, indent=2)
            except:
                pass
        
        log_aktivite(f"Yeni hedef eklendi: {hedef}", "INFO")
        return yeni_hedef
    
    def _son_rapor_kontrol(self):
        try:
            if os.path.exists(SON_RAPOR_TARIHI):
                with open(SON_RAPOR_TARIHI, "r") as f:
                    data = json.load(f)
                son_tarih = datetime.fromisoformat(data.get("son_tarih", "2000-01-01"))
                if datetime.now().date() > son_tarih.date():
                    self._gunluk_rapor_olustur()
            else:
                self._gunluk_rapor_olustur()
        except:
            self._gunluk_rapor_olustur()
    
    def _gunluk_rapor_olustur(self):
        try:
            kaynak = SistemKaynak.hepsi()
            
            bot_performanslari = []
            with BOT_LOCK:
                for bot in self.botlar:
                    bot_performanslari.append({
                        "adi": bot.get("adi"),
                        "tur": bot.get("tur"),
                        "kalite_puani": bot.get("kalite_puani", 0),
                        "basari_sayisi": bot.get("basari_sayisi", 0),
                        "hata_sayisi": bot.get("hata_sayisi", 0),
                        "calisma_suresi": self.bot_calisma_sureleri.get(bot.get("adi"), 0)
                    })
            
            rapor = {
                "tarih": datetime.now().isoformat(),
                "surum": VERSION,
                "sistem": kaynak,
                "bot_sayisi": len(self.botlar),
                "aktif_bot": len(self.aktif_botlar),
                "ortalama_kalite": sum(b.get('kalite_puani',0) for b in self.botlar) / max(len(self.botlar), 1),
                "toplam_basari": sum(b.get('basari_sayisi',0) for b in self.botlar),
                "toplam_hata": sum(b.get('hata_sayisi',0) for b in self.botlar),
                "restartlar": dict(self.bot_restart_sayilari),
                "botlar": bot_performanslari,
                "hedefler": self.hedefler[:5]
            }
            
            dosya_adi = f"rapor_{datetime.now().strftime('%Y%m%d')}.json"
            with open(os.path.join(RAPORLAR_DIR, dosya_adi), "w", encoding="utf-8") as f:
                json.dump(rapor, f, ensure_ascii=False, indent=2)
            
            # JSON klasörüne de kaydet
            with open(os.path.join(LOGS_JSON_DIR, dosya_adi), "w", encoding="utf-8") as f:
                json.dump(rapor, f, ensure_ascii=False, indent=2)
            
            with open(SON_RAPOR_TARIHI, "w") as f:
                json.dump({"son_tarih": datetime.now().isoformat()}, f)
            
            log_aktivite("Gunluk rapor olusturuldu", "INFO")
            renkli_yaz(f"\n[📊] Gunluk rapor olusturuldu: {dosya_adi}", Renk.CYAN)
            
        except Exception as e:
            log_hata("gunluk_rapor", e)
    
    def _verileri_yukle(self):
        try:
            if os.path.exists(AKTIF_BOTLAR):
                with open(AKTIF_BOTLAR, "r") as f:
                    self.botlar = json.load(f)
            else:
                self.botlar = []
                self._botlari_kaydet()
        except:
            self.botlar = []
    
    def _botlari_kaydet(self):
        with BOT_LOCK:
            try:
                with open(AKTIF_BOTLAR, "w") as f:
                    json.dump(self.botlar, f, indent=2)
            except:
                pass
    
    def _soru_json_kaydet(self, soru, kategori, kaynak, bot_adi):
        """Soruyu JSON olarak kaydet"""
        with JSON_LOCK:
            try:
                dosya_adi = f"{bot_adi}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                dosya_yolu = os.path.join(SORULAR_JSON_DIR, dosya_adi)
                
                veri = {
                    "soru": soru,
                    "kategori": kategori,
                    "kaynak": kaynak,
                    "bot": bot_adi,
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(dosya_yolu, "w", encoding="utf-8") as f:
                    json.dump(veri, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                log_hata("soru_json_kaydet", e)
                return False
    
    def _bilgi_json_kaydet(self, cevap, bot_adi, kaynak="qwen"):
        """Öğrenilen bilgiyi JSON olarak kaydet"""
        with JSON_LOCK:
            try:
                dosya_adi = f"{bot_adi}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                dosya_yolu = os.path.join(BILGILER_JSON_DIR, dosya_adi)
                
                veri = {
                    "cevap": cevap,
                    "bot": bot_adi,
                    "kaynak": kaynak,
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(dosya_yolu, "w", encoding="utf-8") as f:
                    json.dump(veri, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                log_hata("bilgi_json_kaydet", e)
                return False
    
    def _kod_json_kaydet(self, bot_adi, kod, sonuc, basarili):
        """Denenen kodu JSON olarak kaydet"""
        with JSON_LOCK:
            try:
                klasor = BASARILI_KODLAR_JSON_DIR if basarili else BASARISIZ_KODLAR_JSON_DIR
                dosya_adi = f"{bot_adi}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                dosya_yolu = os.path.join(klasor, dosya_adi)
                
                veri = {
                    "bot": bot_adi,
                    "kod": kod,
                    "sonuc": sonuc,
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(dosya_yolu, "w", encoding="utf-8") as f:
                    json.dump(veri, f, ensure_ascii=False, indent=2)
                
                # DENENEN_KODLAR klasörüne de kaydet
                deneme_yolu = os.path.join(DENENEN_KODLAR_JSON_DIR, dosya_adi)
                with open(deneme_yolu, "w", encoding="utf-8") as f:
                    json.dump(veri, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                log_hata("kod_json_kaydet", e)
                return False
    
    def _kaynak_kontrol(self):
        kaynak = SistemKaynak.hepsi()
        if kaynak["batarya"] < self.ayarlar["batarya_limit"]:
            return 1
        saat = datetime.now().strftime("%H:%M")
        if "12:00" <= saat < "18:00":
            return 1
        elif "00:00" <= saat < "06:00":
            return self.ayarlar["max_bot"]
        else:
            return 2
    
    def _kalite_hesapla(self, bot):
        basari = bot.get("basari_sayisi", 0)
        hata = bot.get("hata_sayisi", 0)
        puan = 50 + (basari * 2) - (hata * 5)
        ortalama = self.db.bot_ortalama(bot["adi"])
        if ortalama:
            puan = (puan + ortalama) / 2
        return max(0, min(100, puan))
    
    def _bot_iyilestir_qwen(self, bot):
        if not self.ayarlar["qwen_kullan"]:
            return False
        
        renkli_yaz(f"\n[Q] Qwen'e soruluyor: {bot['adi']} nasil iyilestirilir?", Renk.MOR)
        
        sonuc = self.qwen.bot_iyilestir(
            bot["adi"],
            bot.get("amac", "Bilgi yok"),
            bot.get("hata_sayisi", 0),
            bot.get("kalite_puani", 50)
        )
        
        if sonuc.get("cevaplar") and not sonuc.get("hata"):
            for cevap in sonuc["cevaplar"][:3]:
                log_aktivite(f"Qwen onerisi: {cevap[:100]}", "INFO", bot["adi"])
                renkli_yaz(f"  Qwen onerisi: {cevap[:80]}...", Renk.CYAN)
                self._bilgi_json_kaydet(cevap, bot["adi"], "qwen_oneri")
            
            self.ogrenme_db.bilgi_ekle(
                f"{bot['adi']} iyilestirme",
                sonuc["cevaplar"],
                "bot_iyilestirme",
                sonuc.get("basari_puani", 50)
            )
            return True
        else:
            log_hata("Qwen.bot_iyilestir", Exception(sonuc.get("hata")), {"bot": bot["adi"]})
            return False
    
    def _performans_analiz(self):
        kaynak = SistemKaynak.hepsi()
        self.db.sistem_kaydet(kaynak["cpu"], kaynak["ram"], kaynak["batarya"], kaynak["sicaklik"], len(self.aktif_botlar))
        
        with BOT_LOCK:
            for bot in self.botlar:
                yeni = self._kalite_hesapla(bot)
                bot["kalite_puani"] = yeni
                self.db.bot_kaydet(bot["adi"], yeni, bot.get("basari_sayisi",0), bot.get("hata_sayisi",0), self.bot_restart_sayilari.get(bot["adi"],0), self.bot_zamanlari.get(bot["adi"], {}).get("son_sure",0))
                
                if yeni < 30 and self.ayarlar["hata_duzelt"]:
                    renkli_yaz(f"\n[!] {bot['adi']} kalite puani dusuk ({yeni}), iyilestiriliyor...", Renk.SARI)
                    self._bot_iyilestir_qwen(bot)
                    self._bot_iyilestir(bot)
        
        self._botlari_kaydet()
        renkli_yaz(f"\n[P] CPU:%{kaynak['cpu']:.0f} RAM:%{kaynak['ram']:.0f} Bat:%{kaynak['batarya']} Aktif:{len(self.aktif_botlar)}", Renk.CYAN)
    
    def _bot_uret(self, tur, amac):
        log_aktivite(f"Bot uretiliyor: {tur}")
        renkli_yaz(f"\n[B] Yeni bot: {amac}", Renk.MOR)
        
        yeni_id = len(self.botlar) + 1
        bot_adi = f"{tur}_{yeni_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        bot_klasor = os.path.join(YARDIMCILAR_DIR, bot_adi)
        os.makedirs(bot_klasor, exist_ok=True)
        
        template = BOT_TEMPLATES.get(tur, BOT_TEMPLATES["kodlama"])
        with open(os.path.join(bot_klasor, f"{bot_adi}.py"), "w") as f:
            f.write(template.format(bot_adi=bot_adi))
        
        yeni = {
            "id": yeni_id, "adi": bot_adi, "tur": tur, "amac": amac,
            "durum": "beklemede", "kalite_puani": 50,
            "basari_sayisi": 0, "hata_sayisi": 0,
            "kod_dosyasi": os.path.join(bot_klasor, f"{bot_adi}.py"),
            "olusturma": datetime.now().isoformat()
        }
        
        with BOT_LOCK:
            self.botlar.append(yeni)
            self._botlari_kaydet()
        
        renkli_yaz(f"[+] Bot olusturuldu: {bot_adi}", Renk.YESIL)
        return yeni
    
    def _ihtiyac_analizi(self):
        if not self.ayarlar["yeni_bot_uret"]:
            return None
        
        istek_dosya = os.path.join(BASKAN_DIR, "yeni_bot_istegi.json")
        if os.path.exists(istek_dosya):
            try:
                with open(istek_dosya, "r") as f:
                    istek = json.load(f)
                os.remove(istek_dosya)
                return {"tur": istek.get("tur","yardimci"), "amac": istek.get("amac","Yeni bot")}
            except:
                pass
        
        with BOT_LOCK:
            mevcut = [b.get("tur","") for b in self.botlar]
        
        turler = ["kodlama", "sistem", "analiz", "ogrenme"]
        amaclar = {
            "kodlama": "Kodlama tekniklerini ogrenip ogretmek",
            "sistem": "Sistem kaynaklarini optimize etmek",
            "analiz": "Performans verilerini analiz etmek",
            "ogrenme": "Yeni bilgiler toplayip kaydetmek"
        }
        for t in turler:
            if t not in mevcut:
                return {"tur": t, "amac": amaclar[t]}
        return None
    
    def _bot_baslat(self, bot):
        try:
            renkli_yaz(f"  {bot['adi'][:25]} baslatiliyor...", Renk.CYAN)
            basla = time.time()
            
            bot_thread = BotThread(bot['adi'], bot['kod_dosyasi'], self.ayarlar["bot_timeout"])
            bot_thread.start()
            
            with BOT_LOCK:
                self.bot_threads[bot['adi']] = bot_thread
            
            sure = time.time() - basla
            self.bot_zamanlari[bot['adi']] = {
                "son_sure": sure,
                "toplam_sure": self.bot_zamanlari.get(bot['adi'], {}).get("toplam_sure", 0) + sure
            }
            self.bot_calisma_sureleri[bot['adi']] += sure
            bot['durum'] = "calisiyor"
            
            with BOT_LOCK:
                self.aktif_botlar.append(bot)
            
            renkli_yaz(f"  + {bot['adi'][:25]} baslatildi", Renk.YESIL)
            self.db.bot_calisma_kaydet(bot['adi'], sure, 0, 1)
            
        except Exception as e:
            log_hata("bot_baslat", e, {"bot": bot.get("adi")})
            renkli_yaz(f"  x {bot['adi'][:25]} baslatilamadi", Renk.KIRMIZI)
            bot['hata_sayisi'] = bot.get('hata_sayisi', 0) + 1
    
    def _bot_durdur(self, bot):
        renkli_yaz(f"  {bot['adi'][:25]} durduruluyor...", Renk.SARI)
        bot['durum'] = "durduruldu"
        
        with BOT_LOCK:
            if bot in self.aktif_botlar:
                self.aktif_botlar.remove(bot)
            
            if bot['adi'] in self.bot_threads:
                self.bot_threads[bot['adi']].stop()
                del self.bot_threads[bot['adi']]
    
    def _bot_iyilestir(self, bot):
        renkli_yaz(f"\n[F] {bot['adi'][:25]} iyilestiriliyor...", Renk.SARI)
        bot['kalite_puani'] = min(bot.get('kalite_puani',50) + 15, 100)
        bot['hata_sayisi'] = max(0, bot.get('hata_sayisi',0) - 3)
        renkli_yaz(f"  + Yeni puan: {bot['kalite_puani']}", Renk.YESIL)
    
    def _botlari_yonet(self):
        max_bot = self._kaynak_kontrol()
        
        with BOT_LOCK:
            for bot_adi, thread in list(self.bot_threads.items()):
                if not thread.is_alive():
                    bot = next((b for b in self.botlar if b.get('adi') == bot_adi), None)
                    if bot:
                        if hasattr(thread, 'error') and thread.error:
                            log_aktivite(f"{bot_adi} hata verdi: {thread.error}", "HATA", bot_adi)
                            bot['hata_sayisi'] = bot.get('hata_sayisi', 0) + 1
                            self.bot_restart_sayilari[bot_adi] += 1
                            
                            self._kod_json_kaydet(bot_adi, thread.error, "Hata", False)
                            
                            if self.bot_restart_sayilari[bot_adi] <= self.ayarlar.get("max_restart", 3):
                                renkli_yaz(f"  [!] {bot_adi} restart ediliyor ({self.bot_restart_sayilari[bot_adi]}/3)", Renk.SARI)
                                bot['durum'] = "beklemede"
                            else:
                                renkli_yaz(f"  x {bot_adi} cok fazla hata, beklemeye alindi", Renk.KIRMIZI)
                                bot['durum'] = "hata"
                        else:
                            bot['basari_sayisi'] = bot.get('basari_sayisi', 0) + 1
                            if bot in self.aktif_botlar:
                                self.aktif_botlar.remove(bot)
                            
                            if hasattr(thread, 'result') and thread.result:
                                self._kod_json_kaydet(bot_adi, thread.result, "Basari", True)
                    
                    if bot_adi in self.bot_threads:
                        del self.bot_threads[bot_adi]
            
            if len(self.aktif_botlar) < max_bot:
                bekleyen = [b for b in self.botlar if b.get('durum') == "beklemede"]
                if bekleyen:
                    bekleyen.sort(key=lambda x: x.get('kalite_puani',0), reverse=True)
                    self._bot_baslat(bekleyen[0])
            
            if len(self.aktif_botlar) > max_bot:
                dusuk = min(self.aktif_botlar, key=lambda x: x.get('kalite_puani',0))
                self._bot_durdur(dusuk)
        
        self._durum_guncelle()
    
    def _durum_guncelle(self):
        kaynak = SistemKaynak.hepsi()
        try:
            with open(DURUM_FILE, "w") as f:
                json.dump({
                    "durum": "calisiyor",
                    "aktif_bot": len(self.aktif_botlar),
                    "toplam_bot": len(self.botlar),
                    "batarya": kaynak["batarya"],
                    "cpu": kaynak["cpu"],
                    "ram": kaynak["ram"],
                    "version": VERSION,
                    "son": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    def _sistem_performans_kayit(self):
        kaynak = SistemKaynak.hepsi()
        self.db.sistem_kaydet(
            kaynak["cpu"], kaynak["ram"], 
            kaynak["batarya"], kaynak["sicaklik"], 
            len(self.aktif_botlar)
        )
    
    def _ogren(self):
        try:
            konular = [
                "Python programlama", "Yapay zeka temelleri", "Sistem optimizasyonu",
                "Hata ayiklama teknikleri", "Otomasyon stratejileri", "Veri analizi",
                "Makine ogrenmesi", "Termux komutlari", "Android sistem yonetimi",
                "Thread yonetimi", "Subprocess kullanimi", "SQLite optimizasyonu"
            ]
            
            konu = random.choice(konular)
            soru = f"{konu} hakkinda 5 farkli kisa bilgi ver"
            
            if self.ayarlar["qwen_kullan"]:
                qwen_sonuc = self.qwen.sor(soru, "ogrenme")
                if qwen_sonuc.get("cevaplar") and not qwen_sonuc.get("hata"):
                    cevaplar = qwen_sonuc["cevaplar"]
                    for i, cevap in enumerate(cevaplar[:3]):
                        self.ogrenme_db.ogrenilen_ekle(f"{konu}_{i+1}", cevap, "qwen")
                        self._bilgi_json_kaydet(cevap, "baskan", "qwen")
                        renkli_yaz(f"\n[O] {konu} - {i+1}: {cevap[:60]}...", Renk.MOR)
                    log_aktivite(f"Yeni bilgi ogrenildi: {konu} ({len(cevaplar)} cevap)")
                    return
            
            yeni = f"{konu} ogrenildi - {datetime.now().strftime('%H:%M')}"
            self.ogrenme_db.ogrenilen_ekle(konu, yeni, "basit")
            self._bilgi_json_kaydet(yeni, "baskan", "basit")
            renkli_yaz(f"\n[O] {yeni}", Renk.MOR)
                
        except Exception as e:
            log_hata("ogren", e)
    
    def _soru_isle(self, soru, bot_adi):
        """Tek bir soruyu işle"""
        try:
            renkli_yaz(f"\n[?] {bot_adi}: {soru[:50]}", Renk.CYAN)
            
            self._soru_json_kaydet(soru, "genel", bot_adi, bot_adi)
            
            hafiza_cevaplar = self.ogrenme_db.bilgi_ara(soru)
            
            if hafiza_cevaplar:
                secilen = random.choice(hafiza_cevaplar)
                self.ogrenme_db.bilgi_kullan(soru)
                renkli_yaz(f"  > Hafizadan ({len(hafiza_cevaplar)} cevap) secilen: {secilen[:80]}", Renk.MAVI)
                cevap = secilen
            else:
                if self.ayarlar.get("qwen_kullan", True):
                    qwen_sonuc = self.qwen.sor(soru, "genel")
                    if qwen_sonuc.get("cevaplar") and not qwen_sonuc.get("hata"):
                        cevaplar = qwen_sonuc["cevaplar"]
                        self.ogrenme_db.bilgi_ekle(soru, cevaplar, "genel", qwen_sonuc.get("basari_puani", 70))
                        self.ogrenme_db.qwen_cevap_kaydet(soru, cevaplar, qwen_sonuc.get("basari_puani", 70))
                        secilen = random.choice(cevaplar)
                        renkli_yaz(f"  > Qwen'den {len(cevaplar)} cevap, secilen: {secilen[:80]}", Renk.SARI)
                        cevap = secilen
                        
                        for c in cevaplar:
                            self._bilgi_json_kaydet(c, bot_adi, "qwen")
                    else:
                        cevap = f"Bu konuyu ogreniyorum: {soru}"
                        self.ogrenme_db.bilgi_ekle(soru, [cevap], "genel", 30)
                        self._bilgi_json_kaydet(cevap, bot_adi, "fallback")
                else:
                    cevap = f"Bu konuyu ogreniyorum: {soru}"
                    self.ogrenme_db.bilgi_ekle(soru, [cevap], "genel", 30)
                    self._bilgi_json_kaydet(cevap, bot_adi, "fallback")
                renkli_yaz(f"  > Yeni ogreniliyor: {cevap[:80]}", Renk.SARI)
            
            return cevap
            
        except Exception as e:
            log_hata("soru_isle", e, {"soru": soru, "bot": bot_adi})
            return f"Hata: {str(e)}"
    
    def _sorulari_isle(self):
        if not os.path.exists(SORULAR_DIR):
            return
        
        for dosya in Path(SORULAR_DIR).glob("*.json"):
            try:
                with open(dosya, "r", encoding="utf-8") as f:
                    soru_data = json.load(f)
                
                soru = soru_data.get("soru", "")
                bot_adi = soru_data.get("bot", "bilinmiyor")
                
                cevap = self._soru_isle(soru, bot_adi)
                
                cevap_dosya = os.path.join(SORULAR_DIR, f"cevap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(cevap_dosya, "w", encoding="utf-8") as f:
                    json.dump({
                        "soru": soru,
                        "cevap": cevap,
                        "zaman": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                
                os.remove(dosya)
                log_aktivite(f"Soru cevaplandi: {soru[:50]}", "INFO", bot_adi)
                
            except json.JSONDecodeError as e:
                log_hata("soru_islem.json", e, {"dosya": str(dosya)})
                renkli_yaz(f"[!] JSON hatasi: {dosya}", Renk.KIRMIZI)
                try:
                    os.remove(dosya)
                except:
                    pass
            except Exception as e:
                log_hata("soru_islem", e, {"dosya": str(dosya)})
    
    def _bot_gorev_yap(self, bot):
        """Bot görev yap - EKLENDI"""
        try:
            log_aktivite(f"Bot gorev yapiyor", "INFO", bot.get("adi"))
            
            soru = f"{bot.get('tur')} botu olarak gorevin nedir?"
            cevap = self._soru_isle(soru, bot.get("adi"))
            
            log_aktivite(f"Bot gorev tamamlandi: {cevap[:100]}", "INFO", bot.get("adi"))
            
        except Exception as e:
            log_hata("bot_gorev_yap", e, {"bot": bot.get("adi")})
    
    def _hata_yonet(self, hata_detay, context=None):
        log_hata("Baskan._hata_yonet", Exception(hata_detay), context)
        
        if self.ayarlar.get("qwen_kullan", True):
            cozumler = self.qwen.hata_coz(hata_detay, context)
            if cozumler.get("cevaplar"):
                renkli_yaz(f"[!] Hata cozumu onerileri:", Renk.SARI)
                for i, c in enumerate(cozumler["cevaplar"][:3]):
                    renkli_yaz(f"    {i+1}. {c[:100]}", Renk.CYAN)
                    self._bilgi_json_kaydet(c, "baskan", "hata_cozumu")
                return cozumler["cevaplar"][0] if cozumler["cevaplar"] else None
        
        renkli_yaz(f"[!] Hata: {hata_detay[:100]}", Renk.KIRMIZI)
        return None
    
    def main_loop(self):
        renkli_yaz("\n[+] Ana dongu baslatiliyor", Renk.YESIL)
        
        son_perf = time.time()
        son_ogren = time.time()
        son_bot = time.time()
        son_rapor = time.time()
        son_sistem_kayit = time.time()
        son_rapor_kontrol = time.time()
        
        try:
            while self.calisiyor:
                self._botlari_yonet()
                self._sorulari_isle()
                
                if time.time() - son_perf > self.ayarlar["perf_suresi"]:
                    self._performans_analiz()
                    son_perf = time.time()
                
                if time.time() - son_ogren > 60:
                    self._ogren()
                    son_ogren = time.time()
                
                if time.time() - son_bot > 120:
                    ihtiyac = self._ihtiyac_analizi()
                    if ihtiyac:
                        self._bot_uret(ihtiyac["tur"], ihtiyac["amac"])
                    son_bot = time.time()
                
                if time.time() - son_rapor > self.ayarlar["rapor_suresi"]:
                    self._rapor_olustur()
                    son_rapor = time.time()
                
                if time.time() - son_sistem_kayit > self.ayarlar["sistem_kayit_suresi"]:
                    self._sistem_performans_kayit()
                    son_sistem_kayit = time.time()
                
                if time.time() - son_rapor_kontrol > 3600:
                    if datetime.now().hour == 0 and datetime.now().minute < 5:
                        self._gunluk_rapor_olustur()
                    son_rapor_kontrol = time.time()
                
                time.sleep(3)
                
        except KeyboardInterrupt:
            renkli_yaz("\n[!] Kesinti alindi", Renk.SARI)
            self.durdur()
        except Exception as e:
            self._hata_yonet(str(e), {"modul": "main_loop"})
            self.durdur()
    
    def _rapor_olustur(self):
        try:
            kaynak = SistemKaynak.hepsi()
            with BOT_LOCK:
                rapor = {
                    "tarih": datetime.now().isoformat(),
                    "bot_sayisi": len(self.botlar),
                    "aktif_bot": len(self.aktif_botlar),
                    "ortalama_kalite": sum(b.get('kalite_puani',0) for b in self.botlar) / max(len(self.botlar),1),
                    "toplam_basari": sum(b.get('basari_sayisi',0) for b in self.botlar),
                    "toplam_hata": sum(b.get('hata_sayisi',0) for b in self.botlar),
                    "restartlar": dict(self.bot_restart_sayilari),
                    "calisma_sureleri": dict(self.bot_calisma_sureleri),
                    "sistem": kaynak
                }
            with open(os.path.join(RAPORLAR_DIR, f"rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
                json.dump(rapor, f, indent=2)
            
            with open(os.path.join(LOGS_JSON_DIR, f"rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
                json.dump(rapor, f, indent=2)
            
            log_aktivite("Rapor olusturuldu")
        except Exception as e:
            log_hata("rapor", e)
    
    def calistir(self):
        renkli_yaz("\n" + "="*60, Renk.CYAN)
        renkli_yaz("     OTONOMYZ BASKAN BASLATILIYOR", Renk.MOR)
        renkli_yaz(f"     Surum {VERSION} (Qwen 2.5 7B - Coklu Cevap - Thread Safe)", Renk.CYAN)
        renkli_yaz("="*60, Renk.CYAN)
        
        self.calisiyor = True
        
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        self._durum_guncelle()
        self.main_loop()
    
    def durdur(self):
        renkli_yaz("\n" + "="*60, Renk.SARI)
        renkli_yaz("     BASKAN DURDURULUYOR", Renk.KIRMIZI)
        renkli_yaz("="*60, Renk.SARI)
        
        self.calisiyor = False
        
        with BOT_LOCK:
            for bot in self.aktif_botlar[:]:
                self._bot_durdur(bot)
            self._botlari_kaydet()
        
        self._ayarlari_kaydet()
        self._hedefleri_kaydet()
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        
        try:
            with open(DURUM_FILE, "w") as f:
                json.dump({
                    "durum": "durduruldu",
                    "aktif_bot": 0,
                    "toplam_bot": len(self.botlar),
                    "son": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
        
        renkli_yaz("\n[+] Baskan durduruldu", Renk.YESIL)
        log_aktivite("Baskan sistemi durduruldu")
    
    def rapor_goster(self):
        kaynak = SistemKaynak.hepsi()
        print("\n" + "="*60)
        renkli_yaz("     BASKAN RAPORU", Renk.MOR)
        print("="*60)
        print(f"  Surum: {VERSION}")
        print(f"  CPU: %{kaynak['cpu']:.0f} | RAM: %{kaynak['ram']:.0f}")
        print(f"  Batarya: %{kaynak['batarya']} | Sicaklik: {kaynak['sicaklik']:.0f}C")
        print(f"  Toplam Bot: {len(self.botlar)} | Aktif: {len(self.aktif_botlar)}")
        print("\n  Botlar:")
        for bot in self.botlar[:5]:
            p = bot.get('kalite_puani',0)
            if p >= 70: s = "***"
            elif p >= 40: s = "**"
            else: s = "*"
            print(f"    {s} {bot['adi'][:25]}: {p} puan")
        print("\n  Hedefler:")
        for h in self.hedefler[:3]:
            print(f"    • {h.get('hedef', '')[:50]}")
        print("\n" + "="*60)

# ==================== ANA ====================
def tek_instance_kontrol():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                return False
            except OSError:
                os.remove(PID_FILE)
    except:
        pass
    return True

def proses_calisiyor():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
    except:
        pass
    return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        if not tek_instance_kontrol():
            renkli_yaz("[!] Baskan zaten calisiyor!", Renk.SARI)
            sys.exit(1)
        b = Baskan()
        b.calistir()
    else:
        while True:
            os.system('clear')
            print("\n" + "="*60)
            renkli_yaz("     OTONOMYZ BASKAN SISTEMI", Renk.MOR)
            print("="*60)
            
            if proses_calisiyor():
                renkli_yaz("\n  Durum: CALISIYOR", Renk.YESIL)
                try:
                    if os.path.exists(DURUM_FILE):
                        with open(DURUM_FILE, "r") as f:
                            durum = json.load(f)
                        renkli_yaz(f"  Aktif Bot: {durum.get('aktif_bot', 0)}", Renk.CYAN)
                        renkli_yaz(f"  Toplam Bot: {durum.get('toplam_bot', 0)}", Renk.CYAN)
                except:
                    pass
            else:
                renkli_yaz("\n  Durum: DURDURULDU", Renk.KIRMIZI)
            
            print("\n  1. Baskani Baslat")
            print("  2. Baskani Durdur")
            print("  3. Durum Raporu")
            print("  4. Yeni Bot Uret")
            print("  5. Yeni Hedef Ekle")
            print("  6. Cikis")
            print("="*60)
            
            secim = input("\nSecim (1-6): ").strip()
            
            if secim == "1":
                if proses_calisiyor():
                    renkli_yaz("Zaten calisiyor!", Renk.SARI)
                else:
                    subprocess.Popen([sys.executable, __file__, "--daemon"], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL,
                                   start_new_session=True)
                    time.sleep(3)
                    if proses_calisiyor():
                        renkli_yaz("Baskan baslatildi! (Qwen 2.5 7B - Coklu Cevap - Thread Safe)", Renk.YESIL)
                    else:
                        renkli_yaz("Baskan baslatilamadi!", Renk.KIRMIZI)
                input("Enter...")
            elif secim == "2":
                if proses_calisiyor():
                    try:
                        with open(PID_FILE, "r") as f:
                            pid = int(f.read().strip())
                        os.kill(pid, 15)
                        time.sleep(2)
                        renkli_yaz("Baskan durduruldu!", Renk.YESIL)
                    except:
                        renkli_yaz("Hata!", Renk.KIRMIZI)
                else:
                    renkli_yaz("Calismiyor!", Renk.SARI)
                input("Enter...")
            elif secim == "3":
                if proses_calisiyor():
                    b = Baskan()
                    b.rapor_goster()
                else:
                    renkli_yaz("Baskan calismiyor!", Renk.SARI)
                input("Enter...")
            elif secim == "4":
                if proses_calisiyor():
                    amac = input("Bot amaci: ")
                    tur = input("Tur (kodlama/sistem/analiz/ogrenme): ")
                    with open(os.path.join(BASKAN_DIR, "yeni_bot_istegi.json"), "w") as f:
                        json.dump({"tur": tur, "amac": amac}, f)
                    renkli_yaz("Istek gonderildi!", Renk.YESIL)
                else:
                    renkli_yaz("Once Baskani baslatin!", Renk.SARI)
                input("Enter...")
            elif secim == "5":
                if proses_calisiyor():
                    hedef = input("Yeni hedef: ")
                    if hedef:
                        b = Baskan()
                        b._hedef_ekle(hedef)
                        renkli_yaz("Hedef eklendi!", Renk.YESIL)
                else:
                    renkli_yaz("Once Baskani baslatin!", Renk.SARI)
                input("Enter...")
            elif secim == "6":
                break

if __name__ == "__main__":
    os.makedirs(BASKAN_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    main()