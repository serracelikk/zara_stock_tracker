import customtkinter as ctk
import requests, threading, time, json, os, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── AYARLAR ──────────────────────────────────────────────
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DATA_FILE = "zara_data.json"

# ── RENKLER (Parisian Chic) ───────────────────────────────
C_BG        = "#FAF6F4"
C_PANEL     = "#F5EBE7"
C_TOPBAR    = "#F2E6E1"
C_BORDER    = "#E2C9C0"
C_ACCENT    = "#8B5A52"
C_ACCENT2   = "#C9877A"
C_INPUT_BG  = "#FDF8F6"
C_TEXT      = "#6B4040"
C_MUTED     = "#B89890"
C_SUBBLOCK  = "#EFE0DB"
C_GREEN     = "#7A9E7E"
C_RED_SOFT  = "#B87070"
C_SELECTED  = "#EFE0DB"   # seçili kart vurgusu

FONT_SERIF  = ("Georgia", 15, "bold")
FONT_TITLE  = ("Georgia", 20, "bold")
FONT_BODY   = ("Helvetica", 12)
FONT_SMALL  = ("Helvetica", 10)
FONT_BIGBTN = ("Helvetica", 13)

# ── TELEGRAM ─────────────────────────────────────────────
def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj}, timeout=10)
        print(f"[TELEGRAM] {r.status_code} | {r.text}")
    except Exception as e:
        print(f"[TELEGRAM HATA] {e}")

# ── ZARA API ──────────────────────────────────────────────
def zara_api_stok_kontrol(url, hedef_beden):
    try:
        match = re.search(r'-p(\d+)\.html', url)
        if not match:
            return None
        product_id    = match.group(1)
        country_match = re.search(r'zara\.com/(\w+)/(\w+)/', url)
        country       = country_match.group(1) if country_match else "tr"
        lang          = country_match.group(2) if country_match else "tr"
        api_url       = f"https://www.zara.com/api/product/v1/{country}/{lang}/products/{product_id}/stock"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":     "application/json",
            "Referer":    "https://www.zara.com/",
        }
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        for section in data.get("dataGroups", []):
            for item in section.get("commercialComponents", []):
                for size in item.get("detail", {}).get("colors", [{}])[0].get("sizes", []):
                    if hedef_beden.upper() in size.get("name", "").upper():
                        stok_var = size.get("availability") == "in_stock"
                        return stok_var
        return None
    except Exception as e:
        print(f"[API HATA] {e}")
        return None

# ── SELENIUM ──────────────────────────────────────────────
def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def selenium_stok_kontrol(driver, url, hedef_beden):
    print(f"[SELENIUM] Taranıyor: {url}")
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.size-selector__list-item"))
        )
    except:
        time.sleep(8)

    try:
        bedenler = driver.find_elements(By.CSS_SELECTOR, "li.size-selector__list-item")
        if bedenler:
            for b in bedenler:
                try:
                    b_text  = b.find_element(By.CSS_SELECTOR, ".size-selector__size-name").text.strip().upper()
                    b_class = b.get_attribute("class") or ""
                    if hedef_beden.upper() == b_text:
                        stok = ("is-disabled" not in b_class and
                                "out-of-stock" not in b_class and
                                "disabled" not in b_class)
                        return stok
                except:
                    continue
            return False
    except Exception as e:
        print(f"  [SEL-1 HATA] {e}")

    try:
        tum_butonlar = driver.find_elements(By.CSS_SELECTOR, "[aria-label]")
        for btn in tum_butonlar:
            label = (btn.get_attribute("aria-label") or "").upper()
            if hedef_beden.upper() in label:
                disabled = btn.get_attribute("aria-disabled") or ""
                b_class  = btn.get_attribute("class") or ""
                return (disabled != "true" and
                        "disabled" not in b_class.lower() and
                        "out-of-stock" not in b_class.lower())
    except Exception as e:
        print(f"  [SEL-2 HATA] {e}")

    return False

# ── ANA UYGULAMA ──────────────────────────────────────────
class ZaraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zara Stok Takibi")
        self.geometry("1180x860")
        self.resizable(True, True)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=C_BG)

        self.items         = self.load_data()
        self.is_running    = False
        self.selected_mode = ctk.StringVar(value="once")
        self.paralel_mod   = ctk.BooleanVar(value=False)
        self.secili_id     = None   # hangi kart seçili

        self._build_topbar()
        self._build_body()
        self.render_slots()

    # ── ÜST BAR ──────────────────────────────────────────
    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=C_TOPBAR, corner_radius=0,
                           border_width=1, border_color=C_BORDER)
        bar.pack(fill="x")

        ctk.CTkLabel(bar, text="ZARA STOK",
                     font=FONT_TITLE, text_color=C_ACCENT).pack(side="left", padx=28, pady=18)

        self.entry_url = ctk.CTkEntry(
            bar, width=500,
            placeholder_text="Ürün linkini yapıştırın veya listeden seçin...",
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, placeholder_text_color=C_MUTED,
            font=FONT_BODY, corner_radius=2)
        self.entry_url.pack(side="left", padx=12, pady=18)

        self.size_menu = ctk.CTkOptionMenu(
            bar, values=["XS", "S", "M", "L", "XL"],
            fg_color=C_ACCENT2, button_color=C_ACCENT,
            text_color=C_INPUT_BG, font=FONT_BODY,
            corner_radius=2, width=80)
        self.size_menu.pack(side="left", padx=4)

        # Seçili ürün iptal butonu
        self.btn_iptal = ctk.CTkButton(
            bar, text="✕ Seçimi Kaldır", font=FONT_SMALL,
            fg_color="transparent", hover_color=C_BORDER,
            text_color=C_MUTED, border_width=1, border_color=C_BORDER,
            corner_radius=2, height=30, width=110,
            command=self.secimi_kaldir)
        self.btn_iptal.pack(side="left", padx=8)
        self.btn_iptal.pack_forget()   # başta gizli

    # ── GÖVDE ─────────────────────────────────────────────
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._build_left(body)
        self._build_right(body)

    # ── SOL PANEL ─────────────────────────────────────────
    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, width=285, fg_color=C_PANEL,
                            corner_radius=0, border_width=1, border_color=C_BORDER)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="MOD SEÇİMİ",
                     font=FONT_SERIF, text_color=C_ACCENT).pack(anchor="w", padx=28, pady=(28, 20))

        self._radio_row(left, "Tek Sefer Ara", "once")

        self._radio_row(left, "Sürekli Döngü", "freq")
        fi = ctk.CTkFrame(left, fg_color="transparent")
        fi.pack(anchor="w", padx=(46, 0), pady=(0, 12))
        ctk.CTkLabel(fi, text="HER KAÇ DAKİKADA",
                     font=FONT_SMALL, text_color=C_MUTED).pack(anchor="w")
        fr = ctk.CTkFrame(fi, fg_color="transparent")
        fr.pack(anchor="w")
        self.freq_entry = ctk.CTkEntry(
            fr, width=56, fg_color=C_INPUT_BG,
            border_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BODY, corner_radius=2)
        self.freq_entry.insert(0, "15")
        self.freq_entry.pack(side="left")
        ctk.CTkLabel(fr, text="  dk", font=FONT_SMALL, text_color=C_MUTED).pack(side="left")

        self._radio_row(left, "Zaman Ayarlı", "time")
        sub = ctk.CTkFrame(left, fg_color=C_SUBBLOCK, corner_radius=4,
                           border_width=2, border_color=C_ACCENT2)
        sub.pack(anchor="w", padx=(46, 20), pady=(0, 16), fill="x")

        col1 = ctk.CTkFrame(sub, fg_color="transparent")
        col1.pack(side="left", padx=(14, 8), pady=12)
        ctk.CTkLabel(col1, text="SAAT ARALIĞI",
                     font=FONT_SMALL, text_color=C_MUTED).pack(anchor="w")
        self.hour_entry = ctk.CTkEntry(
            col1, width=68, fg_color=C_INPUT_BG,
            border_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BODY, corner_radius=2)
        self.hour_entry.insert(0, "09-22")
        self.hour_entry.pack(anchor="w")

        col2 = ctk.CTkFrame(sub, fg_color="transparent")
        col2.pack(side="left", padx=(0, 14), pady=12)
        ctk.CTkLabel(col2, text="HER KAÇ DAKİKA",
                     font=FONT_SMALL, text_color=C_MUTED).pack(anchor="w")
        row2 = ctk.CTkFrame(col2, fg_color="transparent")
        row2.pack(anchor="w")
        self.time_freq_entry = ctk.CTkEntry(
            row2, width=46, fg_color=C_INPUT_BG,
            border_color=C_BORDER, text_color=C_TEXT,
            font=FONT_BODY, corner_radius=2)
        self.time_freq_entry.insert(0, "30")
        self.time_freq_entry.pack(side="left")
        ctk.CTkLabel(row2, text="  dk", font=FONT_SMALL, text_color=C_MUTED).pack(side="left")

        ctk.CTkFrame(left, height=1, fg_color=C_BORDER).pack(fill="x", padx=20, pady=(16, 12))

        paralel_frame = ctk.CTkFrame(left, fg_color=C_SUBBLOCK, corner_radius=4,
                                      border_width=1, border_color=C_BORDER)
        paralel_frame.pack(fill="x", padx=20, pady=(0, 12))
        pf_inner = ctk.CTkFrame(paralel_frame, fg_color="transparent")
        pf_inner.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(pf_inner, text="PARALEL TARAMA",
                     font=FONT_SMALL, text_color=C_ACCENT).pack(side="left")
        ctk.CTkSwitch(
            pf_inner, text="", variable=self.paralel_mod,
            fg_color=C_BORDER, progress_color=C_ACCENT2,
            button_color=C_ACCENT, width=36, height=18).pack(side="right")
        ctk.CTkLabel(paralel_frame,
                     text="Tüm ürünleri aynı anda tarar.\nAz ürün için önerilir (≤4).",
                     font=FONT_SMALL, text_color=C_MUTED,
                     justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        self.btn_main = ctk.CTkButton(
            left, text="A R A", font=FONT_BIGBTN,
            fg_color=C_ACCENT, hover_color="#6B3E38",
            text_color=C_INPUT_BG, corner_radius=2,
            height=48, command=self.start_action)
        self.btn_main.pack(padx=20, fill="x")

        self.btn_stop = ctk.CTkButton(
            left, text="D U R D U R", font=FONT_SMALL,
            fg_color="transparent", hover_color=C_BORDER,
            text_color=C_MUTED, corner_radius=2,
            border_width=1, border_color=C_BORDER,
            height=36, command=self.stop_all)
        self.btn_stop.pack(padx=20, pady=8, fill="x")

        self.speed_label = ctk.CTkLabel(left, text="", font=FONT_SMALL, text_color=C_MUTED)
        self.speed_label.pack(padx=20, pady=4)

    def _radio_row(self, parent, text, value):
        ctk.CTkRadioButton(
            parent, text=text,
            variable=self.selected_mode, value=value,
            fg_color=C_ACCENT2, hover_color=C_ACCENT,
            text_color=C_TEXT, font=FONT_BODY,
            border_color=C_ACCENT2).pack(anchor="w", padx=28, pady=(0, 6))

    # ── SAĞ PANEL ─────────────────────────────────────────
    def _build_right(self, parent):
        wrap = ctk.CTkFrame(parent, fg_color=C_BG)
        wrap.pack(side="right", fill="both", expand=True, padx=28, pady=22)

        ctk.CTkLabel(wrap, text="TAKİP LİSTESİ",
                     font=FONT_SERIF, text_color=C_ACCENT).pack(anchor="w", pady=(0, 6))

        # ipucu etiketi
        self.hint_label = ctk.CTkLabel(
            wrap,
            text="Bir ürüne tıklayarak linki ve bedeni üst bara yükleyebilirsin.",
            font=FONT_SMALL, text_color=C_MUTED)
        self.hint_label.pack(anchor="w", pady=(0, 6))

        ctk.CTkFrame(wrap, height=1, fg_color=C_BORDER).pack(fill="x", pady=(0, 14))

        self.slot_area = ctk.CTkScrollableFrame(
            wrap, fg_color="transparent",
            scrollbar_button_color=C_BORDER)
        self.slot_area.pack(fill="both", expand=True)

    # ── SLOTLAR ───────────────────────────────────────────
    def render_slots(self):
        for w in self.slot_area.winfo_children():
            w.destroy()
        if not self.items:
            ctk.CTkLabel(self.slot_area, text="Henüz ürün eklenmedi.",
                         font=FONT_BODY, text_color=C_MUTED).pack(pady=40)
            return

        for item in self.items:
            secili  = item['id'] == self.secili_id
            bg_renk = C_SELECTED if secili else C_INPUT_BG
            b_renk  = C_ACCENT2  if secili else C_BORDER
            b_width = 2          if secili else 1

            card = ctk.CTkFrame(self.slot_area, fg_color=bg_renk,
                                corner_radius=2, border_width=b_width, border_color=b_renk)
            card.pack(fill="x", pady=6)

            # Tüm karta tıklanabilirlik
            card.bind("<Button-1>", lambda e, i=item: self.kart_sec(i))

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", padx=20, pady=14, fill="x", expand=True)
            info.bind("<Button-1>", lambda e, i=item: self.kart_sec(i))

            status = item.get("status", "Bekliyor")
            if "STOK" in status.upper() and "YOK" not in status.upper():
                s_color = C_GREEN
            elif "YOK" in status.upper() or "❌" in status:
                s_color = C_RED_SOFT
            else:
                s_color = C_MUTED

            yontem = item.get("yontem", "")
            for lbl_text, lbl_font, lbl_color in [
                (f"Beden {item['size']}   ·   {item.get('last', '—')}   ·   {yontem}", FONT_SMALL, C_MUTED),
                (item.get("display", ""), FONT_BODY, C_TEXT),
                (status, FONT_BODY, s_color),
            ]:
                l = ctk.CTkLabel(info, text=lbl_text, font=lbl_font, text_color=lbl_color)
                l.pack(anchor="w")
                l.bind("<Button-1>", lambda e, i=item: self.kart_sec(i))

            # Seçili göstergesi
            if secili:
                ctk.CTkLabel(card, text="● Seçili", font=FONT_SMALL,
                             text_color=C_ACCENT2).pack(side="right", padx=(0, 8))

            ctk.CTkButton(
                card, text="Sil", width=56, height=30,
                fg_color="transparent", hover_color=C_BORDER,
                text_color=C_MUTED, border_width=1, border_color=C_BORDER,
                corner_radius=2, font=FONT_SMALL,
                command=lambda i=item['id']: self.delete_item(i)).pack(side="right", padx=16)

    # ── KART SEÇ → URL + BEDENİ ÜST BARA YÜKLe ──────────
    def kart_sec(self, item):
        """Karta tıklandığında linki ve bedeni üst bara yükler."""
        self.secili_id = item['id']

        # URL'yi entry'e yaz
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, item['url'])

        # Bedeni size_menu'de seç
        self.size_menu.set(item['size'])

        # İptal butonunu göster
        self.btn_iptal.pack(side="left", padx=8)

        # Hint güncelle
        self.hint_label.configure(
            text=f"Seçili: Beden {item['size']}  ·  Modu seçip A R A butonuna bas.",
            text_color=C_ACCENT2)

        self.render_slots()

    def secimi_kaldir(self):
        self.secili_id = None
        self.entry_url.delete(0, "end")
        self.size_menu.set("S")
        self.btn_iptal.pack_forget()
        self.hint_label.configure(
            text="Bir ürüne tıklayarak linki ve bedeni üst bara yükleyebilirsin.",
            text_color=C_MUTED)
        self.render_slots()

    # ── AKSİYONLAR ───────────────────────────────────────
    def start_action(self):
        url = self.entry_url.get().strip()

        if url and "zara.com" in url:
            # Seçili bir ürün varsa yeniden eklemek yerine direkt tara
            if self.secili_id:
                self.is_running = True
                mode = self.selected_mode.get()
                self.btn_main.configure(text="ARANIYOR...", state="disabled", fg_color="#4B3030")
                threading.Thread(target=self.main_loop, args=(mode,), daemon=True).start()
                return

            # Yeni ürün ekle
            self.items.append({
                "id":      str(int(time.time() * 1000)),
                "url":     url,
                "display": url.split("/")[-1][:45],
                "size":    self.size_menu.get(),
                "status":  "Bekliyor",
                "last":    "—",
                "yontem":  ""
            })
            self.save_data()
            self.render_slots()
            self.entry_url.delete(0, "end")

        if self.items:
            self.is_running = True
            mode = self.selected_mode.get()
            self.btn_main.configure(text="ARANIYOR...", state="disabled", fg_color="#4B3030")
            threading.Thread(target=self.main_loop, args=(mode,), daemon=True).start()

    def stop_all(self):
        self.is_running = False
        self.btn_main.configure(text="A R A", state="normal", fg_color=C_ACCENT)
        self.speed_label.configure(text="")

    def delete_item(self, i_id):
        if self.secili_id == i_id:
            self.secimi_kaldir()
        self.items = [i for i in self.items if i['id'] != i_id]
        self.save_data()
        self.render_slots()

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    # ── ANA DÖNGÜ ─────────────────────────────────────────
    def main_loop(self, mode):
        while self.is_running or mode == "once":
            if mode == "time":
                try:
                    h_range = self.hour_entry.get().replace("–", "-").split("-")
                    s, e    = int(h_range[0].strip()), int(h_range[1].strip())
                    now     = datetime.now().hour
                    aktif   = (s <= now < e) if s < e else (now >= s or now < e)
                    if not aktif:
                        time.sleep(60)
                        continue
                except Exception as ex:
                    print(f"[ZAMAN HATA] {ex}")
                    break

            # Seçili ürün varsa sadece onu tara
            if self.secili_id:
                idx = next((i for i, x in enumerate(self.items) if x['id'] == self.secili_id), None)
                if idx is not None:
                    self._tek_idx_tara(idx)
            else:
                self.full_scanner()

            if mode == "once":
                break
            elif mode == "freq":
                try:
                    bekleme = int(self.freq_entry.get()) * 60
                except:
                    bekleme = 900
                time.sleep(bekleme)
            elif mode == "time":
                try:
                    bekleme = int(self.time_freq_entry.get()) * 60
                except:
                    bekleme = 1800
                time.sleep(bekleme)

        self.after(0, self.stop_all)

    def _tek_idx_tara(self, idx):
        item = self.items[idx]
        self.items[idx]['status'] = "Taranıyor..."
        self.after(0, self.render_slots)
        sonuc = zara_api_stok_kontrol(item['url'], item['size'])
        if sonuc is not None:
            self._guncelle(idx, sonuc, "API ⚡")
        else:
            try:
                driver = create_driver()
                stok   = selenium_stok_kontrol(driver, item['url'], item['size'])
                driver.quit()
                self._guncelle(idx, stok, "Selenium 🌐")
            except Exception as e:
                print(f"[TEK TARA HATA] {e}")
                self.items[idx]['status'] = "Hata ⚠️"
                self.after(0, self.render_slots)

    # ── TARAYICI ──────────────────────────────────────────
    def full_scanner(self):
        baslangic = time.time()

        if self.paralel_mod.get():
            self._paralel_api_tara()
        else:
            sel_gerekli = []
            for i, item in enumerate(self.items):
                if not self.is_running:
                    break
                self.items[i]['status'] = "Taranıyor..."
                self.after(0, self.render_slots)
                sonuc = zara_api_stok_kontrol(item['url'], item['size'])
                if sonuc is not None:
                    self._guncelle(i, sonuc, "API ⚡")
                else:
                    sel_gerekli.append(i)
            if sel_gerekli and self.is_running:
                self._selenium_tara(sel_gerekli)

        sure = round(time.time() - baslangic, 1)
        ozet = f"{sure}sn  ·  {'Paralel ⚡⚡' if self.paralel_mod.get() else 'Sıralı'}"
        self.after(0, lambda: self.speed_label.configure(text=ozet))

    def _paralel_api_tara(self):
        lock        = threading.Lock()
        sel_gerekli = []
        threads     = []

        def api_isle(i, item, gecikme):
            time.sleep(gecikme)
            if not self.is_running:
                return
            self.items[i]['status'] = "Taranıyor..."
            self.after(0, self.render_slots)
            sonuc = zara_api_stok_kontrol(item['url'], item['size'])
            if sonuc is not None:
                self._guncelle(i, sonuc, "API ⚡⚡")
            else:
                with lock:
                    sel_gerekli.append(i)

        for i, item in enumerate(self.items):
            t = threading.Thread(target=api_isle, args=(i, item, i * 1.0), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        if sel_gerekli and self.is_running:
            self._selenium_tara(sorted(sel_gerekli))

    def _selenium_tara(self, indeksler):
        try:
            driver = create_driver()
            for i in indeksler:
                if not self.is_running:
                    break
                try:
                    stok = selenium_stok_kontrol(driver, self.items[i]['url'], self.items[i]['size'])
                    self._guncelle(i, stok, "Selenium 🌐")
                except Exception as e:
                    print(f"[SELENIUM HATA] {e}")
                    self.items[i]['status'] = "Hata ⚠️"
                    self.after(0, self.render_slots)
            driver.quit()
        except Exception as e:
            print(f"[DRIVER HATA] {e}")

    def _guncelle(self, i, stok, yontem):
        self.items[i]['status'] = "STOKTA ✓" if stok else "Stok Yok"
        self.items[i]['last']   = datetime.now().strftime("%H:%M")
        self.items[i]['yontem'] = yontem
        self.save_data()
        if stok:
            telegram_gonder(
                f"🎀 MÜJDE! {self.items[i]['size']} Beden Stokta!\n{self.items[i]['url']}")
        self.after(0, self.render_slots)


if __name__ == "__main__":
    app = ZaraApp()
    app.mainloop()