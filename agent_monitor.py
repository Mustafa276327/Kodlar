#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent İzleme ve Raporlama Sistemi
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = "/storage/emulated/0/OtonomYZ"
GOREVLER_DIR = os.path.join(BASE_DIR, "Gorevler")
BASARILI_DIR = os.path.join(GOREVLER_DIR, "Basarili")
BASARISIZ_DIR = os.path.join(GOREVLER_DIR, "Basarisiz")
LOG_DIR = os.path.join(BASE_DIR, "Agent_Logs")

class Renk:
    RESET = "\033[0m"
    KIRMIZI = "\033[91m"
    YESIL = "\033[92m"
    SARI = "\033[93m"
    MAVI = "\033[94m"
    CYAN = "\033[96m"

def renkli_yaz(mesaj, renk=Renk.RESET):
    print(f"{renk}{mesaj}{Renk.RESET}")

def monitor():
    """Agent sistemini izle"""
    while True:
        os.system('clear')
        print("\n" + "="*70)
        renkli_yaz("     AGENT SİSTEMİ İZLEME PANELİ", Renk.CYAN)
        print("="*70)
        print(f"  Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Görev istatistikleri
        if os.path.exists(BASARILI_DIR):
            basarili = len(os.listdir(BASARILI_DIR))
        else:
            basarili = 0
        
        if os.path.exists(BASARISIZ_DIR):
            basarisiz = len(os.listdir(BASARISIZ_DIR))
        else:
            basarisiz = 0
        
        renkli_yaz(f"\n  📊 GÖREV İSTATİSTİKLERİ:", Renk.MAVI)
        print(f"     Başarılı: {basarili}")
        print(f"     Başarısız: {basarisiz}")
        print(f"     Toplam: {basarili + basarisiz}")
        
        # Son görevler
        renkli_yaz(f"\n  📁 SON GÖREVLER:", Renk.MAVI)
        tum_gorevler = []
        if os.path.exists(BASARILI_DIR):
            tum_gorevler.extend([(f, "BAŞARILI") for f in os.listdir(BASARILI_DIR)])
        if os.path.exists(BASARISIZ_DIR):
            tum_gorevler.extend([(f, "BAŞARISIZ") for f in os.listdir(BASARISIZ_DIR)])
        
        tum_gorevler.sort(key=lambda x: x[0], reverse=True)
        
        for dosya, durum in tum_gorevler[:5]:
            try:
                with open(os.path.join(BASARILI_DIR if durum == "BAŞARILI" else BASARISIZ_DIR, dosya), "r") as f:
                    data = json.load(f)
                renkli_yaz(f"     [{durum}] {data.get('komut', '')[:50]}", 
                          Renk.YESIL if durum == "BAŞARILI" else Renk.KIRMIZI)
                print(f"        ID: {data.get('id', '')} | Tarih: {data.get('tarih', '')[:19]}")
            except:
                print(f"     [{durum}] {dosya}")
        
        print("\n" + "="*70)
        print("  q: Çıkış | r: Yenile")
        print("="*70)
        
        secim = input("\nKomut: ").strip().lower()
        if secim == 'q':
            break

if __name__ == "__main__":
    monitor()
