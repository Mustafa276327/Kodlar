#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Görev Sorgulama ve Analiz Sistemi
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = "/storage/emulated/0/OtonomYZ"
GOREVLER_DIR = os.path.join(BASE_DIR, "Gorevler")
BASARILI_DIR = os.path.join(GOREVLER_DIR, "Basarili")
BASARISIZ_DIR = os.path.join(GOREVLER_DIR, "Basarisiz")

class Renk:
    RESET = "\033[0m"
    KIRMIZI = "\033[91m"
    YESIL = "\033[92m"
    SARI = "\033[93m"
    MAVI = "\033[94m"
    CYAN = "\033[96m"

def renkli_yaz(mesaj, renk=Renk.RESET):
    print(f"{renk}{mesaj}{Renk.RESET}")

def gorev_ara(aranan):
    """Görev ara"""
    sonuclar = []
    
    for klasor, durum in [(BASARILI_DIR, "BAŞARILI"), (BASARISIZ_DIR, "BAŞARISIZ")]:
        if os.path.exists(klasor):
            for dosya in os.listdir(klasor):
                try:
                    with open(os.path.join(klasor, dosya), "r") as f:
                        data = json.load(f)
                    
                    komut = data.get("komut", "")
                    if aranan.lower() in komut.lower():
                        sonuclar.append({
                            "dosya": dosya,
                            "durum": durum,
                            "data": data
                        })
                except:
                    pass
    
    return sonuclar

def gorev_detay(dosya_adi, durum):
    """Görev detayını göster"""
    klasor = BASARILI_DIR if durum == "BAŞARILI" else BASARISIZ_DIR
    dosya_yolu = os.path.join(klasor, dosya_adi)
    
    if os.path.exists(dosya_yolu):
        with open(dosya_yolu, "r") as f:
            data = json.load(f)
        
        print("\n" + "="*70)
        renkli_yaz(f"     GÖREV DETAYI: {dosya_adi}", Renk.CYAN)
        print("="*70)
        print(f"  ID: {data.get('id', '')}")
        print(f"  Durum: {durum}")
        print(f"  Tarih: {data.get('tarih', '')}")
        print(f"\n  Komut: {data.get('komut', '')}")
        print(f"\n  Alt Görevler:")
        for i, g in enumerate(data.get('gorevler', []), 1):
            print(f"    {i}. {g.get('gorev', '')[:100]}")
        print(f"\n  Sonuç: {data.get('sonuc', '')[:500]}...")
        print("\n" + "="*70)

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python gorev_sorgu.py <aranan_kelime>")
        sys.exit(1)
    
    aranan = sys.argv[1]
    sonuclar = gorev_ara(aranan)
    
    if not sonuclar:
        renkli_yaz(f"\n'{aranan}' için görev bulunamadı.", Renk.SARI)
        sys.exit(0)
    
    renkli_yaz(f"\n'{aranan}' için {len(sonuclar)} görev bulundu:", Renk.YESIL)
    print("="*70)
    
    for i, s in enumerate(sonuclar, 1):
        durum_renk = Renk.YESIL if s['durum'] == "BAŞARILI" else Renk.KIRMIZI
        renkli_yaz(f"\n{i}. [{s['durum']}] {s['data'].get('komut', '')[:80]}", durum_renk)
        print(f"   Dosya: {s['dosya']}")
        print(f"   Tarih: {s['data'].get('tarih', '')[:19]}")
    
    secim = input("\nDetay için görev numarası (çıkış için Enter): ").strip()
    if secim.isdigit() and 1 <= int(secim) <= len(sonuclar):
        s = sonuclar[int(secim)-1]
        gorev_detay(s['dosya'], s['durum'])

if __name__ == "__main__":
    main()
