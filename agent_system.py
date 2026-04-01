#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OtonomYZ Çoklu Agent Yapay Zeka Sistemi
StarCoder | LLaMA | Alpaca | WizardLM | MiniGPT
"""

import os
import sys
import json
import subprocess
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from queue import Queue
from collections import defaultdict

BASE_DIR = "/storage/emulated/0/OtonomYZ"
GOREVLER_DIR = os.path.join(BASE_DIR, "Gorevler")
BASARILI_DIR = os.path.join(GOREVLER_DIR, "Basarili")
BASARISIZ_DIR = os.path.join(GOREVLER_DIR, "Basarisiz")
BEKLEYEN_DIR = os.path.join(GOREVLER_DIR, "Bekleyen")
ARSIV_DIR = os.path.join(GOREVLER_DIR, "Arsiv")
LOG_DIR = os.path.join(BASE_DIR, "Agent_Logs")
CONFIG_DIR = os.path.join(BASE_DIR, "Agent_Config")

# Thread Lock
GOREV_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()

class Renk:
    RESET = "\033[0m"
    KIRMIZI = "\033[91m"
    YESIL = "\033[92m"
    SARI = "\033[93m"
    MAVI = "\033[94m"
    MOR = "\033[95m"
    CYAN = "\033[96m"
    BEYAZ = "\033[97m"

def renkli_yaz(mesaj, renk=Renk.RESET):
    print(f"{renk}{mesaj}{Renk.RESET}")

def log_yaz(tur, mesaj, agent=None):
    with LOG_LOCK:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            tarih = datetime.now().strftime("%Y%m%d")
            dosya = os.path.join(LOG_DIR, f"{tur}_{tarih}.log")
            with open(dosya, "a", encoding="utf-8") as f:
                if agent:
                    f.write(f"[{datetime.now().isoformat()}] [{agent}] {mesaj}\n")
                else:
                    f.write(f"[{datetime.now().isoformat()}] {mesaj}\n")
        except:
            pass

class BaseAgent(threading.Thread):
    """Temel Agent sınıfı - Thread bazlı"""
    
    def __init__(self, name, model, timeout=60):
        super().__init__(daemon=True)
        self.name = name
        self.model = model
        self.timeout = timeout
        self.gorev_kuyrugu = Queue()
        self.sonuc = None
        self.hata = None
        self.calisiyor = True
        self.istatistik = {
            "toplam_gorev": 0,
            "basarili": 0,
            "basarisiz": 0,
            "toplam_sure": 0
        }
    
    def run(self):
        """Agent thread döngüsü"""
        while self.calisiyor:
            try:
                if not self.gorev_kuyrugu.empty():
                    gorev = self.gorev_kuyrugu.get(timeout=1)
                    self._islem_yap(gorev)
                time.sleep(0.1)
            except:
                pass
    
    def _islem_yap(self, gorev):
        """Görevi işle"""
        baslangic = time.time()
        self.istatistik["toplam_gorev"] += 1
        
        try:
            sonuc = self.calistir(gorev["prompt"])
            self.sonuc = sonuc
            self.istatistik["basarili"] += 1
            log_yaz("aktivite", f"Gorev tamamlandi: {gorev.get('tip', 'bilinmiyor')}", self.name)
        except Exception as e:
            self.hata = str(e)
            self.istatistik["basarisiz"] += 1
            log_yaz("hata", f"Gorev hatasi: {e}", self.name)
        
        self.istatistik["toplam_sure"] += time.time() - baslangic
    
    def calistir(self, prompt):
        """Modeli çalıştır"""
        try:
            result = subprocess.run(['ollama', 'run', self.model, prompt],
                                   capture_output=True, text=True, timeout=self.timeout)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except subprocess.TimeoutExpired:
            log_yaz("hata", f"Zaman asimi: {self.name}", self.name)
            return None
        except Exception as e:
            log_yaz("hata", f"{self.name} hatasi: {e}", self.name)
            return None
    
    def gorev_ver(self, gorev):
        """Görev ver"""
        self.gorev_kuyrugu.put(gorev)
    
    def durdur(self):
        """Agent'ı durdur"""
        self.calisiyor = False

class AlpacaAgent(BaseAgent):
    """Görev analizi ve dağıtımı"""
    def __init__(self):
        super().__init__("Alpaca", "llama2:7b", 45)
    
    def analiz_et(self, komut):
        """Komutu analiz et ve alt görevlere böl"""
        prompt = f"""Komut: {komut}
Bu komutu analiz et ve mantıksal alt görevlere ayır. 
Alt görevleri JSON array formatında döndür.
Her alt görev için: {{"gorev": "görev açıklaması", "tip": "kodlama|mantik|analiz|hafiza", "oncelik": 1-5}}
Sadece JSON array'ini döndür, başka şey yazma."""
        
        sonuc = self.calistir(prompt)
        if sonuc:
            try:
                gorevler = json.loads(sonuc.strip())
                if isinstance(gorevler, list):
                    return gorevler
            except:
                pass
        return [{"gorev": komut, "tip": "analiz", "oncelik": 3}]

class StarCoderAgent(BaseAgent):
    """Kod üretimi"""
    def __init__(self):
        super().__init__("StarCoder", "codellama:7b", 60)
    
    def kod_uret(self, gorev):
        """Kod üret"""
        prompt = f"""Görev: {gorev}
Bu görev için Python kodu üret. Kod hafif, hızlı ve hatasız olsun.
Sadece kodu döndür, açıklama yazma."""
        return self.calistir(prompt) or f"# Kod üretilemedi: {gorev}"

class WizardLMAgent(BaseAgent):
    """Optimizasyon ve hata düzeltme"""
    def __init__(self):
        super().__init__("WizardLM", "qwen2.5:7b", 60)
    
    def optimize_et(self, kod, gorev):
        """Kodu optimize et"""
        prompt = f"""Görev: {gorev}
Kod: {kod}
Bu kodu optimize et, hataları düzelt, performansı artır.
Sadece düzeltilmiş kodu döndür."""
        return self.calistir(prompt) or kod

class LLaMAAgent(BaseAgent):
    """Mantıksal denetim"""
    def __init__(self):
        super().__init__("LLaMA", "llama2:7b", 45)
    
    def kontrol_et(self, kod, gorev):
        """Mantıksal kontrol yap"""
        prompt = f"""Görev: {gorev}
Kod: {kod}
Bu kodu mantıksal ve algoritmik olarak kontrol et.
Hata varsa belirt, yoksa "OK" yaz.
Sadece kısa cevap ver."""
        return self.calistir(prompt) or "Kontrol yapilamadi"

class MiniGPTAgent(BaseAgent):
    """Hafıza yönetimi"""
    def __init__(self):
        super().__init__("MiniGPT", "phi:2.7b", 30)
    
    def hafizaya_kaydet(self, komut, gorevler, sonuc):
        """Görevi hafızaya kaydet"""
        try:
            gorev_id = hashlib.md5(f"{komut}{time.time()}".encode()).hexdigest()[:8]
            
            kayit = {
                "id": gorev_id,
                "komut": komut,
                "tarih": datetime.now().isoformat(),
                "gorevler": gorevler,
                "sonuc": sonuc[:2000] if sonuc else None,
                "agent_istatistik": {
                    "alpaca": self.parent.alpaca.istatistik if hasattr(self, 'parent') else {},
                    "starcoder": self.parent.starcoder.istatistik if hasattr(self, 'parent') else {},
                    "wizard": self.parent.wizard.istatistik if hasattr(self, 'parent') else {},
                    "llama": self.parent.llama.istatistik if hasattr(self, 'parent') else {}
                }
            }
            
            # Başarılı/Başarısız kontrolü
            dosya_adi = f"gorev_{gorev_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if "hata" in str(sonuc).lower() or "error" in str(sonuc).lower():
                kayit_yolu = os.path.join(BASARISIZ_DIR, dosya_adi)
            else:
                kayit_yolu = os.path.join(BASARILI_DIR, dosya_adi)
            
            with open(kayit_yolu, "w", encoding="utf-8") as f:
                json.dump(kayit, f, ensure_ascii=False, indent=2)
            
            # Arsivleme (30 gün sonra)
            return kayit_yolu
            
        except Exception as e:
            log_yaz("hata", f"MiniGPT kayit hatasi: {e}")
            return None

class AgentManager:
    """Agent Yöneticisi - Tüm agent'ları koordine eder"""
    
    def __init__(self):
        self.alpaca = AlpacaAgent()
        self.starcoder = StarCoderAgent()
        self.wizard = WizardLMAgent()
        self.llama = LLaMAAgent()
        self.minigpt = MiniGPTAgent()
        
        # Agent'ları başlat
        self.agents = [self.alpaca, self.starcoder, self.wizard, self.llama, self.minigpt]
        
    def baslat(self):
        """Tüm agent'ları başlat"""
        for agent in self.agents:
            agent.start()
        log_yaz("aktivite", "Tum agent'lar baslatildi")
    
    def durdur(self):
        """Tüm agent'ları durdur"""
        for agent in self.agents:
            agent.durdur()
        log_yaz("aktivite", "Tum agent'lar durduruldu")
    
    def isle(self, komut):
        """Ana işlem döngüsü"""
        print("\n" + "="*70)
        renkli_yaz("     ÇOKLU AGENT SİSTEMİ BAŞLATILIYOR", Renk.MOR)
        print("="*70)
        renkli_yaz(f"\n  Komut: {komut[:100]}", Renk.CYAN)
        print()
        
        # 1. Alpaca - Görev analizi
        renkli_yaz("[1/5] Alpaca: Komut analiz ediliyor...", Renk.SARI)
        gorevler = self.alpaca.analiz_et(komut)
        renkli_yaz(f"      ✓ {len(gorevler)} alt görev belirlendi", Renk.YESIL)
        log_yaz("aktivite", f"Alpaca: {len(gorevler)} alt gorev belirlendi")
        
        # 2. StarCoder - Kod üretimi (paralel)
        renkli_yaz("\n[2/5] StarCoder: Kod üretiliyor...", Renk.SARI)
        kodlar = []
        for i, g in enumerate(gorevler):
            renkli_yaz(f"      Görev {i+1}: {g.get('gorev', '')[:50]}...", Renk.MAVI)
            kod = self.starcoder.kod_uret(g.get('gorev', ''))
            kodlar.append({"gorev": g, "kod": kod})
            time.sleep(0.5)  # Rate limit
        renkli_yaz(f"      ✓ {len(kodlar)} kod parçasi üretildi", Renk.YESIL)
        
        # 3. WizardLM - Optimizasyon (paralel)
        renkli_yaz("\n[3/5] WizardLM: Kodlar optimize ediliyor...", Renk.SARI)
        optimize_kodlar = []
        for k in kodlar:
            optimize = self.wizard.optimize_et(k['kod'], k['gorev'].get('gorev', ''))
            optimize_kodlar.append({"gorev": k['gorev'], "kod": optimize})
        renkli_yaz(f"      ✓ {len(optimize_kodlar)} kod optimize edildi", Renk.YESIL)
        
        # 4. LLaMA - Mantıksal kontrol (paralel)
        renkli_yaz("\n[4/5] LLaMA: Mantıksal kontrol yapılıyor...", Renk.SARI)
        kontroller = []
        for k in optimize_kodlar:
            kontrol = self.llama.kontrol_et(k['kod'], k['gorev'].get('gorev', ''))
            kontroller.append({"gorev": k['gorev'], "kod": k['kod'], "kontrol": kontrol})
            if "hata" in kontrol.lower() or "error" in kontrol.lower():
                renkli_yaz(f"      ⚠️  Uyari: {kontrol[:80]}", Renk.SARI)
        renkli_yaz(f"      ✓ {len(kontroller)} kontrol yapıldı", Renk.YESIL)
        
        # 5. MiniGPT - Hafıza kaydı
        renkli_yaz("\n[5/5] MiniGPT: Sonuçlar hafızaya kaydediliyor...", Renk.SARI)
        sonuc_str = "\n\n" + "="*50 + "\n".join([
            f"\n📌 Görev: {k['gorev'].get('gorev')}\n📝 Kod:\n{k['kod'][:500]}\n✅ Kontrol: {k['kontrol']}" 
            for k in kontroller
        ])
        dosya = self.minigpt.hafizaya_kaydet(komut, gorevler, sonuc_str)
        
        # Sonuç
        print("\n" + "="*70)
        renkli_yaz("     İŞLEM TAMAMLANDI", Renk.YESIL)
        print("="*70)
        renkli_yaz(f"\n  📁 Kayıt: {dosya}", Renk.CYAN)
        
        print("\n  📊 AGENT İSTATİSTİKLERİ:")
        print("  " + "-"*50)
        for agent in self.agents:
            i = agent.istatistik
            renkli_yaz(f"  {agent.name}:", Renk.MAVI)
            print(f"     Görev: {i['toplam_gorev']} | Başarılı: {i['basarili']} | Başarısız: {i['basarisiz']}")
        
        log_yaz("aktivite", f"Agent sistemi tamamlandi: {dosya}")
        print("\n" + "="*70)
        
        return kontroller

def main():
    if len(sys.argv) < 2:
        print("Komut gerekli!")
        sys.exit(1)
    
    komut = sys.argv[1]
    
    # Klasörleri oluştur
    for d in [GOREVLER_DIR, BASARILI_DIR, BASARISIZ_DIR, BEKLEYEN_DIR, ARSIV_DIR, LOG_DIR, CONFIG_DIR]:
        os.makedirs(d, exist_ok=True)
    
    # Agent yöneticisini başlat
    manager = AgentManager()
    manager.baslat()
    
    try:
        manager.isle(komut)
    finally:
        manager.durdur()

if __name__ == "__main__":
    main()
