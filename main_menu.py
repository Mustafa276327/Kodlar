#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OtonomYZ Ana Menü Sistemi
Başkan sistemi ile entegre
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

# ==================== KLASÖR YAPISI ====================
BASE_DIR = "/storage/emulated/0/OtonomYZ"
BASKAN_DIR = os.path.join(BASE_DIR, "Baskan")
LOGS_DIR = os.path.join(BASE_DIR, "Loglar")
HATA_LOG_DIR = os.path.join(LOGS_DIR, "HataLoglari")
AKTIVITE_LOG_DIR = os.path.join(LOGS_DIR, "AktiviteLoglari")
YARDIMCILAR_DIR = os.path.join(BASE_DIR, "Yardimcilar")

# ==================== DOSYA YOLLARI ====================
DURUM_FILE = os.path.join(BASKAN_DIR, "durum.json")
PID_FILE = os.path.join(BASKAN_DIR, "baskan.pid")
AKTIF_BOTLAR = os.path.join(BASE_DIR, "aktif_botlar.json")
SISTEM_AYARLARI = os.path.join(BASE_DIR, "sistem_ayarlari.json")

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

def temiz_ekran():
    os.system('clear')

def log_kaydet(tur, mesaj):
    try:
        tarih = datetime.now().strftime("%Y%m%d")
        if tur == "hata":
            log_dir = HATA_LOG_DIR
        else:
            log_dir = AKTIVITE_LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, f"{tur}_{tarih}.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mesaj}\n")
    except:
        pass

def proses_calisiyor_mu():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
    except:
        pass
    return False

def baskan_durumu():
    try:
        if os.path.exists(DURUM_FILE):
            with open(DURUM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"durum": "durduruldu", "aktif_bot": 0, "toplam_bot": 0, "batarya": 100}

def baskan_baslat():
    baskan_path = os.path.join(BASKAN_DIR, "baskan.py")
    if not os.path.exists(baskan_path):
        return False, "Başkan sistemi bulunamadi"
    if proses_calisiyor_mu():
        return False, "Başkan zaten calisiyor"
    try:
        subprocess.Popen([sys.executable, baskan_path, "--daemon"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        start_new_session=True)
        time.sleep(2)
        if proses_calisiyor_mu():
            return True, "Başkan baslatildi"
        else:
            return False, "Başkan baslatilamadi"
    except:
        return False, "Hata"

def baskan_durdur():
    if not proses_calisiyor_mu():
        return False, "Başkan calismiyor"
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            time.sleep(2)
            return True, "Başkan durduruldu"
    except:
        pass
    return False, "Durdurulamadi"

def baslik_goster():
    temiz_ekran()
    print("\n" + "="*60)
    renkli_yaz("          OTONOMYZ ANA MENU", Renk.CYAN)
    renkli_yaz("          Baskan Bot Yonetim Sistemi", Renk.MAVI)
    print("="*60)
    print(f"  Tarih: {datetime.now().strftime('%d.%m.%Y')}  Saat: {datetime.now().strftime('%H:%M:%S')}")
    
    durum = baskan_durumu()
    if proses_calisiyor_mu():
        renkli_yaz(f"\n  Baskan: CALISIYOR", Renk.YESIL)
        renkli_yaz(f"  Aktif Bot: {durum.get('aktif_bot', 0)}", Renk.CYAN)
        renkli_yaz(f"  Toplam Bot: {durum.get('toplam_bot', 0)}", Renk.CYAN)
        renkli_yaz(f"  Batarya: %{durum.get('batarya', 100)}", Renk.CYAN)
    else:
        renkli_yaz(f"\n  Baskan: DURDURULDU", Renk.KIRMIZI)
    
    print("="*60)

def menu_goster():
    print("\n  1. Sistem Ayarlari")
    print("  2. Bot Yonetimi")
    print("  3. Yardimci Botlar")
    print("  4. Loglar")
    print("  5. Baskan Sistemi")
    print("  6. Gorev Ver")
    print("  7. Cikis")
    print("-"*60)

def bilgi_mesaji(mesaj, tip="info"):
    if tip == "info":
        renkli_yaz(f"\n[I] {mesaj}", Renk.MAVI)
    elif tip == "basarili":
        renkli_yaz(f"\n[+] {mesaj}", Renk.YESIL)
    elif tip == "hata":
        renkli_yaz(f"\n[-] {mesaj}", Renk.KIRMIZI)
    elif tip == "uyari":
        renkli_yaz(f"\n[!] {mesaj}", Renk.SARI)
    input("\nDevam icin Enter...")

def sistem_ayarlari():
    ayar_dosyasi = SISTEM_AYARLARI
    default_ayarlar = {"cpu_limit": 70, "ram_limit": 512, "performans_modu": "normal", "calisma_saati_baslangic": "09:00", "calisma_saati_bitis": "18:00"}
    
    try:
        if os.path.exists(ayar_dosyasi):
            with open(ayar_dosyasi, "r") as f:
                ayarlar = json.load(f)
        else:
            ayarlar = default_ayarlar.copy()
    except:
        ayarlar = default_ayarlar.copy()
    
    while True:
        temiz_ekran()
        print("\n" + "="*50)
        renkli_yaz("     SISTEM AYARLARI", Renk.MAVI)
        print("="*50)
        print(f"  1. CPU Limiti: %{ayarlar.get('cpu_limit', 70)}")
        print(f"  2. RAM Limiti: {ayarlar.get('ram_limit', 512)} MB")
        print(f"  3. Performans Modu: {ayarlar.get('performans_modu', 'normal')}")
        print(f"  4. Calisma Saati: {ayarlar.get('calisma_saati_baslangic', '09:00')} - {ayarlar.get('calisma_saati_bitis', '18:00')}")
        print("  5. Ana Menuye Don")
        print("="*50)
        
        secim = input("\nSecim (1-5): ").strip()
        
        if secim == "1":
            try:
                yeni = input(f"CPU limiti (1-100): ").strip()
                if yeni:
                    y = int(yeni)
                    if 1 <= y <= 100:
                        ayarlar['cpu_limit'] = y
                        renkli_yaz("Guncellendi", "basarili")
            except:
                renkli_yaz("Hatali giris", "hata")
        elif secim == "2":
            try:
                yeni = input(f"RAM limiti (128-4096 MB): ").strip()
                if yeni:
                    y = int(yeni)
                    if 128 <= y <= 4096:
                        ayarlar['ram_limit'] = y
                        renkli_yaz("Guncellendi", "basarili")
            except:
                renkli_yaz("Hatali giris", "hata")
        elif secim == "3":
            yeni = input("Mod (normal/performans/ekonomi): ").strip().lower()
            if yeni in ["normal", "performans", "ekonomi"]:
                ayarlar['performans_modu'] = yeni
                renkli_yaz("Guncellendi", "basarili")
        elif secim == "4":
            bas = input("Baslangic (HH:MM): ").strip()
            bit = input("Bitis (HH:MM): ").strip()
            if bas and ":" in bas:
                ayarlar['calisma_saati_baslangic'] = bas
            if bit and ":" in bit:
                ayarlar['calisma_saati_bitis'] = bit
            renkli_yaz("Guncellendi", "basarili")
        elif secim == "5":
            with open(ayar_dosyasi, "w") as f:
                json.dump(ayarlar, f, indent=2)
            break
        else:
            renkli_yaz("Gecersiz secim", "hata")
        
        if secim != "5":
            input("\nDevam icin Enter...")

def bot_yonetimi():
    while True:
        temiz_ekran()
        print("\n" + "="*50)
        renkli_yaz("     BOT YONETIMI", Renk.MAVI)
        print("="*50)
        
        try:
            if os.path.exists(AKTIF_BOTLAR):
                with open(AKTIF_BOTLAR, "r") as f:
                    botlar = json.load(f)
                print(f"\n  Toplam Bot: {len(botlar)}")
        except:
            pass
        
        print("\n  1. Botlari Listele")
        print("  2. Yeni Bot Ekle")
        print("  3. Ana Menuye Don")
        print("="*50)
        
        secim = input("\nSecim (1-3): ").strip()
        
        if secim == "1":
            try:
                if os.path.exists(AKTIF_BOTLAR):
                    with open(AKTIF_BOTLAR, "r") as f:
                        botlar = json.load(f)
                    if botlar:
                        print("\n  Bot Listesi:")
                        for bot in botlar:
                            print(f"    {bot.get('id')} - {bot.get('adi')} - Puan: {bot.get('kalite_puani', 0)}")
                    else:
                        print("\n  Bot yok")
            except:
                print("\n  Hata")
            input("\nDevam icin Enter...")
        elif secim == "2":
            ad = input("Bot adi: ").strip()
            tur = input("Bot turu: ").strip()
            try:
                if os.path.exists(AKTIF_BOTLAR):
                    with open(AKTIF_BOTLAR, "r") as f:
                        botlar = json.load(f)
                else:
                    botlar = []
                yeni = {"id": len(botlar)+1, "adi": ad, "tur": tur, "durum": "beklemede", "kalite_puani": 50, "basari_sayisi": 0, "hata_sayisi": 0}
                botlar.append(yeni)
                with open(AKTIF_BOTLAR, "w") as f:
                    json.dump(botlar, f, indent=2)
                renkli_yaz(f"{ad} eklendi", "basarili")
            except:
                renkli_yaz("Hata", "hata")
            input("\nDevam icin Enter...")
        elif secim == "3":
            break

def yardimci_botlar():
    temiz_ekran()
    print("\n" + "="*50)
    renkli_yaz("     YARDIMCI BOTLAR", Renk.MAVI)
    print("="*50)
    renkli_yaz("\n  Bu modul gelistirme asamasinda", Renk.SARI)
    print("="*50)
    input("\nDevam icin Enter...")

def loglar_menusu():
    while True:
        temiz_ekran()
        print("\n" + "="*50)
        renkli_yaz("     LOGLAR MENUSU", Renk.MAVI)
        print("="*50)
        print("  1. Aktivite Loglari")
        print("  2. Hata Loglari")
        print("  3. Ana Menuye Don")
        print("="*50)
        
        secim = input("\nSecim (1-3): ").strip()
        
        if secim == "1":
            if os.path.exists(AKTIVITE_LOG_DIR):
                loglar = sorted(os.listdir(AKTIVITE_LOG_DIR))[-5:]
                if loglar:
                    print("\n  Son 5 Aktivite Logu:")
                    for log in loglar:
                        print(f"\n  {log}")
                        try:
                            with open(os.path.join(AKTIVITE_LOG_DIR, log), "r") as f:
                                satir = f.read().split('\n')[-3:]
                                for s in satir:
                                    if s:
                                        print(f"    {s[:80]}")
                        except:
                            pass
            else:
                print("\n  Log yok")
            input("\nDevam icin Enter...")
        elif secim == "2":
            if os.path.exists(HATA_LOG_DIR):
                loglar = sorted(os.listdir(HATA_LOG_DIR))[-5:]
                if loglar:
                    print("\n  Son 5 Hata Logu:")
                    for log in loglar:
                        print(f"\n  {log}")
                        try:
                            with open(os.path.join(HATA_LOG_DIR, log), "r") as f:
                                satir = f.read().split('\n')[-3:]
                                for s in satir:
                                    if s:
                                        print(f"    {s[:80]}")
                        except:
                            pass
            else:
                print("\n  Log yok")
            input("\nDevam icin Enter...")
        elif secim == "3":
            break

def baskan_menusu():
    while True:
        temiz_ekran()
        print("\n" + "="*50)
        renkli_yaz("     BASKAN SISTEMI", Renk.MOR)
        print("="*50)
        
        durum = baskan_durumu()
        if proses_calisiyor_mu():
            renkli_yaz(f"\n  Durum: CALISIYOR", Renk.YESIL)
            renkli_yaz(f"  Aktif Bot: {durum.get('aktif_bot', 0)}", Renk.CYAN)
            renkli_yaz(f"  Toplam Bot: {durum.get('toplam_bot', 0)}", Renk.CYAN)
            renkli_yaz(f"  Batarya: %{durum.get('batarya', 100)}", Renk.CYAN)
        else:
            renkli_yaz(f"\n  Durum: DURDURULDU", Renk.KIRMIZI)
        
        print("\n  1. Baskani Baslat")
        print("  2. Baskani Durdur")
        print("  3. Durum Raporu")
        print("  4. Yeni Bot Uret")
        print("  5. Ana Menuye Don")
        print("="*50)
        
        secim = input("\nSecim (1-5): ").strip()
        
        if secim == "1":
            basarili, mesaj = baskan_baslat()
            bilgi_mesaji(mesaj, "basarili" if basarili else "hata")
        elif secim == "2":
            basarili, mesaj = baskan_durdur()
            bilgi_mesaji(mesaj, "basarili" if basarili else "hata")
        elif secim == "3":
            temiz_ekran()
            print("\n" + "="*60)
            renkli_yaz("     BASKAN DURUM RAPORU", Renk.MOR)
            print("="*60)
            d = baskan_durumu()
            renkli_yaz(f"\n  Durum: {d.get('durum', '?').upper()}", Renk.CYAN)
            renkli_yaz(f"  Aktif Bot: {d.get('aktif_bot', 0)}", Renk.CYAN)
            renkli_yaz(f"  Toplam Bot: {d.get('toplam_bot', 0)}", Renk.CYAN)
            renkli_yaz(f"  Batarya: %{d.get('batarya', 100)}", Renk.CYAN)
            print("\n" + "="*60)
            input("\nDevam icin Enter...")
        elif secim == "4":
            if not proses_calisiyor_mu():
                bilgi_mesaji("Once Baskani baslatin", "hata")
            else:
                amac = input("Bot amaci: ").strip()
                tur = input("Bot turu: ").strip()
                if amac and tur:
                    try:
                        istek = os.path.join(BASKAN_DIR, "yeni_bot_istegi.json")
                        with open(istek, "w") as f:
                            json.dump({"tur": tur, "amac": amac, "zaman": datetime.now().isoformat()}, f)
                        bilgi_mesaji("Bot uretim istegi gonderildi", "basarili")
                    except:
                        bilgi_mesaji("Hata", "hata")
                else:
                    bilgi_mesaji("Bot amaci ve turu girin", "hata")
        elif secim == "5":
            break

def cikis():
    renkli_yaz("\n  Iyi gunler!", Renk.CYAN)
    print("="*60)
    sys.exit(0)

def ana_menu():
    log_kaydet("aktivite", "Ana menu baslatildi")
    while True:
        try:
            baslik_goster()
            menu_goster()
            secim = input("\nSeciminiz (1-7): ").strip()
            if secim == "1":
                sistem_ayarlari()
            elif secim == "2":
                bot_yonetimi()
            elif secim == "3":
                yardimci_botlar()
            elif secim == "4":
                loglar_menusu()
            elif secim == "5":
                baskan_menusu()
            elif secim == "6":
                try:
                    import gorev_ver
                    gorev_ver.gorev_menu()
                except ImportError:
                    renkli_yaz("\n[!] Gorev sistemi bulunamadi!", Renk.KIRMIZI)
                    renkli_yaz("Lutfen once gorev_ver.py dosyasini olusturun.", Renk.SARI)
                except Exception as e:
                    renkli_yaz(f"\n[!] Gorev sistemi hatasi: {e}", Renk.KIRMIZI)
            elif secim == "7":
                cikis()
            else:
                bilgi_mesaji("Gecersiz secim 1-7", "hata")
        except KeyboardInterrupt:
            cikis()
        except Exception as e:
            bilgi_mesaji(f"Hata: {e}", "hata")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(BASKAN_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(HATA_LOG_DIR, exist_ok=True)
    os.makedirs(AKTIVITE_LOG_DIR, exist_ok=True)
    os.makedirs(YARDIMCILAR_DIR, exist_ok=True)
    
    if not os.path.exists(AKTIF_BOTLAR):
        with open(AKTIF_BOTLAR, "w") as f:
            json.dump([], f)
    
    ana_menu()
