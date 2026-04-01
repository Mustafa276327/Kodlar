#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OtonomYZ Gorev Yonetim Sistemi
"""

import os
import json
import time
from datetime import datetime

BASE_DIR = "/storage/emulated/0/OtonomYZ"
GOREVLER_DIR = os.path.join(BASE_DIR, "gorevler")
LOG_DIR = os.path.join(BASE_DIR, "loglar")

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

BOTLAR = ["yazilim_bot", "yapayzeka_bot", "analiz_bot", "bilgi_bot", "duzenleyici_bot"]

def log_yaz(mesaj):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "gorev_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mesaj}\n")
    except:
        pass

def gorev_ekle():
    print("\n" + "="*50)
    renkli_yaz("     GOREV EKLE", Renk.MOR)
    print("="*50)
    
    print("\nBot secin:")
    for i, bot in enumerate(BOTLAR, 1):
        print(f"  {i}. {bot}")
    
    try:
        bot_secim = int(input("\nSecim (1-5): ").strip())
        if 1 <= bot_secim <= len(BOTLAR):
            bot = BOTLAR[bot_secim-1]
        else:
            renkli_yaz("Gecersiz secim!", Renk.KIRMIZI)
            return
    except:
        renkli_yaz("Gecersiz giris!", Renk.KIRMIZI)
        return
    
    baslik = input("Gorev basligi: ").strip()
    if not baslik:
        renkli_yaz("Baslik bos olamaz!", Renk.KIRMIZI)
        return
    
    print("\nGorev aciklamasi (cok satir icin sonra Enter'a 2 kez basin):")
    satirlar = []
    while True:
        satir = input()
        if satir == "":
            if satirlar:
                break
        else:
            satirlar.append(satir)
    aciklama = "\n".join(satirlar)
    
    if not aciklama:
        renkli_yaz("Aciklama bos olamaz!", Renk.KIRMIZI)
        return
    
    print("\nOncelik:")
    print("  1. dusuk")
    print("  2. orta")
    print("  3. yuksek")
    oncelik_secim = input("Secim (1-3): ").strip()
    oncelik_map = {"1": "dusuk", "2": "orta", "3": "yuksek"}
    oncelik = oncelik_map.get(oncelik_secim, "orta")
    
    son_tarih = input("Son tarih (YYYY-MM-DD) [opsiyonel]: ").strip()
    if not son_tarih:
        son_tarih = None
    
    gorev_id = f"{bot}_{int(time.time())}"
    
    gorev = {
        "id": gorev_id,
        "bot": bot,
        "baslik": baslik,
        "aciklama": aciklama,
        "oncelik": oncelik,
        "durum": "bekliyor",
        "olusturma_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "son_tarih": son_tarih
    }
    
    os.makedirs(GOREVLER_DIR, exist_ok=True)
    dosya_yolu = os.path.join(GOREVLER_DIR, f"{bot}.json")
    
    try:
        if os.path.exists(dosya_yolu):
            with open(dosya_yolu, "r", encoding="utf-8") as f:
                gorevler = json.load(f)
        else:
            gorevler = []
        
        for g in gorevler:
            if g.get("baslik") == baslik and g.get("durum") == "bekliyor":
                renkli_yaz("\n[!] Ayni baslikta bekleyen gorev zaten var!", Renk.SARI)
                return
        
        gorevler.append(gorev)
        
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(gorevler, f, ensure_ascii=False, indent=2)
        
        renkli_yaz(f"\n[+] Gorev eklendi! ID: {gorev_id}", Renk.YESIL)
        log_yaz(f"{bot} -> Yeni gorev eklendi: {baslik}")
        
    except Exception as e:
        renkli_yaz(f"\n[-] Hata: {e}", Renk.KIRMIZI)

def gorevleri_listele():
    print("\n" + "="*50)
    renkli_yaz("     GOREVLERI LISTELE", Renk.MAVI)
    print("="*50)
    
    os.makedirs(GOREVLER_DIR, exist_ok=True)
    gorev_bulundu = False
    
    for bot in BOTLAR:
        dosya_yolu = os.path.join(GOREVLER_DIR, f"{bot}.json")
        if os.path.exists(dosya_yolu):
            try:
                with open(dosya_yolu, "r", encoding="utf-8") as f:
                    gorevler = json.load(f)
                
                if gorevler:
                    gorev_bulundu = True
                    renkli_yaz(f"\n[{bot.upper()}]", Renk.CYAN)
                    print("-"*40)
                    
                    for g in gorevler:
                        if g.get("durum") == "tamamlandi":
                            durum_simge = "✅"
                            durum_renk = Renk.YESIL
                        elif g.get("durum") == "calisiyor":
                            durum_simge = "🔄"
                            durum_renk = Renk.SARI
                        elif g.get("durum") == "bekliyor":
                            durum_simge = "⏳"
                            durum_renk = Renk.MAVI
                        else:
                            durum_simge = "❌"
                            durum_renk = Renk.KIRMIZI
                        
                        print(f"\n  {durum_simge} {g.get('id')}")
                        print(f"     Baslik: {g.get('baslik')}")
                        print(f"     Oncelik: {g.get('oncelik')}")
                        renkli_yaz(f"     Durum: {g.get('durum')}", durum_renk)
                        print(f"     Tarih: {g.get('olusturma_tarihi')}")
                        if g.get("son_tarih"):
                            print(f"     Son Tarih: {g.get('son_tarih')}")
                            
            except Exception as e:
                renkli_yaz(f"\n[-] {bot} okunamadi: {e}", Renk.KIRMIZI)
    
    if not gorev_bulundu:
        renkli_yaz("\n  Hiç görev bulunmuyor.", Renk.SARI)
    
    input("\nDevam icin Enter...")

def gorev_guncelle():
    print("\n" + "="*50)
    renkli_yaz("     GOREV DURUMU GUNCELLE", Renk.MOR)
    print("="*50)
    
    gorev_id = input("Gorev ID: ").strip()
    if not gorev_id:
        renkli_yaz("Gorev ID gerekli!", Renk.KIRMIZI)
        return
    
    print("\nYeni durum:")
    print("  1. bekliyor")
    print("  2. calisiyor")
    print("  3. tamamlandi")
    print("  4. iptal")
    
    durum_secim = input("Secim (1-4): ").strip()
    durum_map = {"1": "bekliyor", "2": "calisiyor", "3": "tamamlandi", "4": "iptal"}
    yeni_durum = durum_map.get(durum_secim)
    
    if not yeni_durum:
        renkli_yaz("Gecersiz secim!", Renk.KIRMIZI)
        return
    
    bulundu = False
    for bot in BOTLAR:
        dosya_yolu = os.path.join(GOREVLER_DIR, f"{bot}.json")
        if os.path.exists(dosya_yolu):
            try:
                with open(dosya_yolu, "r", encoding="utf-8") as f:
                    gorevler = json.load(f)
                
                for g in gorevler:
                    if g.get("id") == gorev_id:
                        eski_durum = g.get("durum")
                        g["durum"] = yeni_durum
                        bulundu = True
                        break
                
                if bulundu:
                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                        json.dump(gorevler, f, ensure_ascii=False, indent=2)
                    renkli_yaz(f"\n[+] Gorev {gorev_id} durumu '{eski_durum}' -> '{yeni_durum}' olarak guncellendi", Renk.YESIL)
                    log_yaz(f"Gorev guncellendi: {gorev_id} -> {yeni_durum}")
                    break
            except Exception as e:
                renkli_yaz(f"[-] Hata: {e}", Renk.KIRMIZI)
    
    if not bulundu:
        renkli_yaz(f"[-] Gorev bulunamadi: {gorev_id}", Renk.KIRMIZI)
    
    input("\nDevam icin Enter...")

def gorev_sil():
    print("\n" + "="*50)
    renkli_yaz("     GOREV SIL", Renk.KIRMIZI)
    print("="*50)
    
    gorev_id = input("Gorev ID: ").strip()
    if not gorev_id:
        renkli_yaz("Gorev ID gerekli!", Renk.KIRMIZI)
        return
    
    silindi = False
    for bot in BOTLAR:
        dosya_yolu = os.path.join(GOREVLER_DIR, f"{bot}.json")
        if os.path.exists(dosya_yolu):
            try:
                with open(dosya_yolu, "r", encoding="utf-8") as f:
                    gorevler = json.load(f)
                
                yeni_gorevler = [g for g in gorevler if g.get("id") != gorev_id]
                
                if len(yeni_gorevler) != len(gorevler):
                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                        json.dump(yeni_gorevler, f, ensure_ascii=False, indent=2)
                    renkli_yaz(f"\n[+] Gorev silindi: {gorev_id}", Renk.YESIL)
                    log_yaz(f"Gorev silindi: {gorev_id}")
                    silindi = True
                    break
            except Exception as e:
                renkli_yaz(f"[-] Hata: {e}", Renk.KIRMIZI)
    
    if not silindi:
        renkli_yaz(f"[-] Gorev bulunamadi: {gorev_id}", Renk.KIRMIZI)
    
    input("\nDevam icin Enter...")

def gorev_menu():
    os.makedirs(GOREVLER_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    while True:
        os.system('clear')
        print("\n" + "="*50)
        renkli_yaz("     GOREV YONETIM SISTEMI", Renk.MOR)
        print("="*50)
        print("\n  1. Gorev Ver")
        print("  2. Gorevleri Listele")
        print("  3. Gorev Durumu Guncelle")
        print("  4. Gorev Sil")
        print("  5. Ana Menuye Don")
        print("="*50)
        
        secim = input("\nSeciminiz (1-5): ").strip()
        
        if secim == "1":
            gorev_ekle()
        elif secim == "2":
            gorevleri_listele()
        elif secim == "3":
            gorev_guncelle()
        elif secim == "4":
            gorev_sil()
        elif secim == "5":
            break
        else:
            renkli_yaz("Gecersiz secim!", Renk.KIRMIZI)
            input("Devam icin Enter...")

if __name__ == "__main__":
    gorev_menu()
