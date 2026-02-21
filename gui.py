import customtkinter as ctk
import webbrowser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random

# ================= GLOBAL UI REFERENCES =================
lbl_track = None
lbl_artist = None
btn_spotify = None
txt_activity = None
lbl_emotion = None
debug_box = None

input_event = None
input_mood = None
meal_var = None
city_var = None

# ================= DATA =================
TR_CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
    "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
    "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul",
    "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli",
    "Kırşehir", "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa",
    "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
]

# ================= AGENT IMPORT =================
try:
    from agents.coordinator_agent import CoordinatorAgent
    coordinator = CoordinatorAgent()
    COORDINATOR_AVAILABLE = True
except Exception as e:
    print("Agent import hatası:", e)
    COORDINATOR_AVAILABLE = False
    coordinator = None

# ================= THEME SETTINGS =================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg": "#0f172a",
    "card_bg": "#1e293b",
    "accent": "#3b82f6",
    "text_main": "#f8fafc",
    "text_sub": "#94a3b8",
    "music_bg": "#064e3b",
    "music_fg": "#34d399",
    "act_bg": "#312e81",
    "act_fg": "#a5b4fc",
    "chart_line": "#38bdf8",
}

# ================= GRAPH FUNCTION =================
def update_chart(values):
    ax.clear()
    categories = ["Valence\n(Mutluluk)", "Arousal\n(Enerji)", "Comfort\n(Rahatlık)", "Calm\n(Sakinlik)", "Intensity\n(Yoğunluk)"]

    ax.plot(categories, values, color=COLORS["chart_line"], marker="o", linewidth=2, markersize=6)
    ax.fill_between(categories, values, color=COLORS["chart_line"], alpha=0.15)

    ax.set_ylim(-1.1, 1.1)
    ax.axhline(0, color=COLORS["text_sub"], linestyle="--", linewidth=0.8)
    ax.set_ylabel("Denge Sapması (Merkez=0)", color=COLORS["text_sub"], fontsize=8)

    fig.patch.set_facecolor(COLORS["card_bg"])
    ax.set_facecolor(COLORS["card_bg"])
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["text_sub"])
    ax.spines["left"].set_color(COLORS["text_sub"])
    
    ax.tick_params(axis="x", colors=COLORS["text_sub"], labelsize=8)
    ax.tick_params(axis="y", colors=COLORS["text_sub"], labelsize=8)

    canvas.draw()

# ================= HELPERS =================
def translate_weather(w_eng):
    mapping = {
        "rainy": "Yağmurlu 🌧️", "cloudy": "Bulutlu ☁️", 
        "clear": "Açık/Güneşli ☀️", "snowy": "Karlı ❄️", 
        "neutral": "Normal", "unknown": "Bilinmiyor"
    }
    return mapping.get(w_eng, w_eng)

def interpret_event_impact(event_delta):
    val = event_delta.get("valence", 0)
    aro = event_delta.get("arousal", 0)

    if val == 0 and aro == 0:
        return "Etkisiz / Nötr"
    elif val < 0 and aro > 0:
        return "Baskı / Stres Kaynağı ⚠️"
    elif val > 0:
        return "Enerji Yükseltici (Energy Up) 🚀"
    elif val < 0:
        return "Enerji Düşürücü (Energy Down) 📉"
    else:
        return "Karmaşık Etki"

def format_score_calc(param_name, breakdown_dict, current_val):
    parts = []
    
    base = breakdown_dict.get("base", {}).get(param_name, 50)
    parts.append(f"{base} (Baz)")
    
    emo = breakdown_dict.get("emotion", {}).get(param_name, 0)
    if emo != 0: parts.append(f"{'+' if emo>0 else ''}{emo} (Duygu)")
    
    evt = breakdown_dict.get("event", {}).get(param_name, 0)
    if evt != 0: parts.append(f"{'+' if evt>0 else ''}{evt} (Olay)")
    
    mic = breakdown_dict.get("micro", {}).get(param_name, 0)
    if mic != 0: parts.append(f"{'+' if mic>0 else ''}{mic} (Yemek)")
    
    ctx = breakdown_dict.get("context", {}).get(param_name, 0)
    if ctx != 0: parts.append(f"{'+' if ctx>0 else ''}{ctx} (Ortam)")
    
    calculation = " ".join(parts)
    return f"• {param_name.capitalize()}: {calculation} = {current_val}"


# ================= PIPELINE =================
def run_pipeline():
    global lbl_track, lbl_artist, btn_spotify, txt_activity, lbl_emotion, debug_box
    
    user_text = input_mood.get("1.0", "end").strip()
    event_text = input_event.get("1.0", "end").strip()
    city = city_var.get() or "Bursa"
    micro_input = meal_var.get()

    if not user_text:
        return 

    debug_box.configure(state="normal")
    debug_box.delete("1.0", "end")

    disclaimer_text = (
        "⚠️ YASAL UYARI: Bu analiz tıbbi veya psikolojik bir teşhis değildir.\n"
        "   Amaç, anlık duygusal farkındalık ve destek sunmaktır.\n"
        f"{'-'*55}\n"
    )
    debug_box.insert("end", disclaimer_text, "warning")

    if COORDINATOR_AVAILABLE:
        try:
            res = coordinator.process(
                user_text=user_text,
                city=city,
                event_text=event_text if event_text else None,
                micro_input=micro_input,
            )

            lbl_emotion.configure(text=res.final_emotion.upper())

            s = res.affect_state
            chart_values = [
                (s.valence - 50) / 50,
                (s.arousal - 50) / 50,
                (s.physical_comfort - 50) / 50,
                (s.environmental_calm - 50) / 50,
                (s.emotional_intensity - 50) / 50,
            ]
            update_chart(chart_values)

            # --- DEBUG RAPORU ---
            
            # 1. GİRDİLER
            debug_box.insert("end", "📌 ADIM 1: GİRDİ ANALİZİ\n", "header")
            debug_box.insert("end", f"• Duygu Tespiti: {res.final_emotion.upper()}\n")
            
            if res.context:
                w_str = translate_weather(res.context.get('weather'))
                temp = res.context.get('temperature')
                time_d = "Gece" if res.context.get('is_dark') else "Gündüz"
                debug_box.insert("end", f"• Ortam: {res.context.get('city')}, {w_str}, {temp}°C, {time_d}\n")
            
            meal_status = "Nötr"
            if micro_input == 1: meal_status = "İyi/Tok (+)"
            elif micro_input == -1: meal_status = "Kötü/Aç (-)"
            debug_box.insert("end", f"• Fizyolojik Durum: {meal_status}\n")

            if event_text:
                evt_breakdown = res.affect_breakdown.get("event", {})
                impact_label = interpret_event_impact(evt_breakdown)
                short_text = (event_text[:30] + '..') if len(event_text) > 30 else event_text
                debug_box.insert("end", f"• Olay Girdisi: '{short_text}'\n")
                debug_box.insert("end", f"• Olay Etkisi: {impact_label}\n")
            else:
                debug_box.insert("end", "• Olay Girdisi: Yok (Nötr)\n")


            # 2. HESAPLAMA
            debug_box.insert("end", "\n🧮 ADIM 2: 5 BOYUTLU HESAPLAMA\n", "header")
            debug_box.insert("end", "Her boyut 50 puan ile başlar. Faktörler toplanır.\n", "info")
            
            bd = res.affect_breakdown
            debug_box.insert("end", format_score_calc("valence", bd, s.valence) + "\n")
            debug_box.insert("end", format_score_calc("arousal", bd, s.arousal) + "\n")
            debug_box.insert("end", format_score_calc("physical_comfort", bd, s.physical_comfort) + "\n")
            debug_box.insert("end", format_score_calc("environmental_calm", bd, s.environmental_calm) + "\n")
            debug_box.insert("end", format_score_calc("emotional_intensity", bd, s.emotional_intensity) + "\n")

            # 3. REGÜLASYON
            debug_box.insert("end", "\n🎯 ADIM 3: REGÜLASYON STRATEJİSİ\n", "header")
            
            guidance_list = res.regulation.guidance
            if not guidance_list:
                debug_box.insert("end", "• Durum dengeli, radikal bir değişim gerekmiyor.\n")
            else:
                for guide in guidance_list:
                    debug_box.insert("end", f"• Karar: {guide}\n")
            
            delta = res.regulation.delta
            max_delta_key = max(delta, key=lambda k: abs(delta[k]))
            max_val = delta[max_delta_key]
            
            if abs(max_val) > 5:
                action = "artırmaya" if max_val > 0 else "azaltmaya"
                focus = f"Sistem '{max_delta_key}' seviyesini {action} odaklandı."
                debug_box.insert("end", f"👉 Strateji: {focus}\n", "info")

            # Müzik & Aktivite
            music = res.music or {}
            lbl_track.configure(text=music.get("track", "Öneri Yok"))
            lbl_artist.configure(text=music.get("artist", "-"))
            
            spotify_link = music.get("spotify_url")
            if spotify_link:
                btn_spotify.configure(state="normal", command=lambda: webbrowser.open(spotify_link))
            else:
                btn_spotify.configure(state="disabled")

            txt_activity.configure(state="normal")
            txt_activity.delete("1.0", "end")
            txt_activity.insert("end", res.micro_activity)
            txt_activity.configure(state="disabled")

        except Exception as e:
            debug_box.insert("end", f"\n❌ HATA: {e}\n", "header")
            print(e)
            import traceback
            traceback.print_exc()
    else:
        # Mock Data
        lbl_emotion.configure(text="TEST: MUTLU")
        update_chart([random.uniform(-0.8, 0.8) for _ in range(5)])
        
        lbl_track.configure(text="Test Şarkısı")
        lbl_artist.configure(text="Test Sanatçısı")
        
        txt_activity.configure(state="normal")
        txt_activity.delete("1.0", "end")
        txt_activity.insert("end", "Agent bağlı değil. Demo çıktısıdır.")
        txt_activity.configure(state="disabled")
        
        debug_box.insert("end", "⚠️ Agent bulunamadı, mock veriler.", "header")

    debug_box.configure(state="disabled")

# ================= APP UI LAYOUT =================
app = ctk.CTk()
app.title("Duygu Regülasyonu Asistanı")
app.geometry("1200x850")
app.configure(fg_color=COLORS["bg"])

app.grid_columnconfigure(0, weight=55)
app.grid_columnconfigure(1, weight=45)
app.grid_rowconfigure(2, weight=1)

# 1. HEADER
header = ctk.CTkFrame(app, fg_color="transparent")
header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 5))

ctk.CTkLabel(header, text="🎧 Duygu Regülasyonu Asistanı", font=("Roboto", 26, "bold"), text_color=COLORS["text_main"]).pack(anchor="center")
ctk.CTkLabel(header, text="Beş boyutlu duygu analizi & yapay zeka destekli regülasyon", font=("Roboto", 14), text_color=COLORS["text_sub"]).pack(anchor="center")

# 2. SOL PANEL
left_panel = ctk.CTkFrame(app, fg_color="transparent")
left_panel.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=20, pady=10)

def create_card(parent):
    frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=16)
    frame.pack(fill="x", pady=8)
    return frame

# Mood & Şehir
card1 = create_card(left_panel)
c1_header = ctk.CTkFrame(card1, fg_color="transparent")
c1_header.pack(fill="x", padx=15, pady=(12, 5))

ctk.CTkLabel(c1_header, text="🧠 Nasıl Hissediyorsun?", font=("Roboto", 15, "bold"), text_color=COLORS["text_main"]).pack(side="left")

city_var = ctk.StringVar(value="Bursa")
ctk.CTkOptionMenu(c1_header, variable=city_var, values=TR_CITIES, width=130, fg_color=COLORS["accent"], button_color=COLORS["accent"]).pack(side="right")

input_mood = ctk.CTkTextbox(card1, height=100, fg_color=COLORS["bg"], text_color="white", border_width=0)
input_mood.pack(fill="x", padx=15, pady=(0, 15))

# Olay & Yemek
card2 = create_card(left_panel)
ctk.CTkLabel(card2, text="📩 Günlük Bağlam", font=("Roboto", 15, "bold"), text_color=COLORS["text_main"]).pack(anchor="w", padx=15, pady=(12, 5))
c2_grid = ctk.CTkFrame(card2, fg_color="transparent")
c2_grid.pack(fill="x", padx=15, pady=(0, 15))
c2_grid.grid_columnconfigure(0, weight=3)
c2_grid.grid_columnconfigure(1, weight=1)

input_event = ctk.CTkTextbox(c2_grid, height=80, fg_color=COLORS["bg"], text_color="white")
input_event.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
ctk.CTkLabel(c2_grid, text="Olay / Mesaj (Opsiyonel)", font=("Roboto", 10), text_color=COLORS["text_sub"]).grid(row=1, column=0, sticky="w")

meal_frame = ctk.CTkFrame(c2_grid, fg_color="transparent")
meal_frame.grid(row=0, column=1, sticky="ns")
ctk.CTkLabel(meal_frame, text="Yemek nasıldı?", font=("Roboto", 12, "bold"), text_color=COLORS["text_sub"]).pack(anchor="w")
meal_var = ctk.IntVar(value=0)
ctk.CTkRadioButton(meal_frame, text="Açım/Kötü", variable=meal_var, value=-1, font=("Roboto", 11)).pack(anchor="w", pady=5)
ctk.CTkRadioButton(meal_frame, text="Tokum/İyi", variable=meal_var, value=1, font=("Roboto", 11)).pack(anchor="w")

# Buton
ctk.CTkButton(left_panel, text="✨ Analiz Et ve Regüle Et", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["accent"], hover_color="#2563eb", corner_radius=12, command=run_pipeline).pack(fill="x", pady=10)

# Müzik & Aktivite Grid
output_grid = ctk.CTkFrame(left_panel, fg_color="transparent")
output_grid.pack(fill="x", pady=(10, 0))
output_grid.grid_columnconfigure(0, weight=1)
output_grid.grid_columnconfigure(1, weight=1)

music_box = ctk.CTkFrame(output_grid, fg_color=COLORS["music_bg"], corner_radius=16)
music_box.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

ctk.CTkLabel(music_box, text="🎧 Müzik Önerisi", font=("Roboto", 14, "bold"), text_color=COLORS["music_fg"]).pack(anchor="w", padx=15, pady=(15, 5))
lbl_track = ctk.CTkLabel(music_box, text="-", font=("Roboto", 16, "bold"), text_color="white", wraplength=200)
lbl_track.pack(anchor="w", padx=15)
lbl_artist = ctk.CTkLabel(music_box, text="-", font=("Roboto", 12), text_color="#a7f3d0")
lbl_artist.pack(anchor="w", padx=15)
btn_spotify = ctk.CTkButton(music_box, text="Spotify'da Aç", fg_color="#1db954", hover_color="#15803d", text_color="white", height=32, state="disabled")
btn_spotify.pack(anchor="w", padx=15, pady=(10, 15))

act_box = ctk.CTkFrame(output_grid, fg_color=COLORS["act_bg"], corner_radius=16)
act_box.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

ctk.CTkLabel(act_box, text="🧩 Mikro Aktivite", font=("Roboto", 14, "bold"), text_color=COLORS["act_fg"]).pack(anchor="w", padx=15, pady=(15, 5))
txt_activity = ctk.CTkTextbox(act_box, height=80, fg_color="transparent", text_color="white", wrap="word", font=("Roboto", 13))
txt_activity.pack(fill="both", expand=True, padx=10, pady=(0, 10))
txt_activity.insert("end", "Öneri bekleniyor...")
txt_activity.configure(state="disabled")

# 3. SAĞ PANEL
right_panel = ctk.CTkFrame(app, fg_color="transparent")
right_panel.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(0, 20), pady=10)

summary_card = ctk.CTkFrame(right_panel, fg_color=COLORS["card_bg"], corner_radius=16)
summary_card.pack(fill="x", pady=(0, 10))

lbl_emotion = ctk.CTkLabel(summary_card, text="ANALİZ BEKLENİYOR", font=("Roboto", 24, "bold"), text_color=COLORS["accent"])
lbl_emotion.pack(pady=(15, 5))

fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=summary_card)
canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
update_chart([0, 0, 0, 0, 0])

debug_frame = ctk.CTkFrame(right_panel, fg_color="#020617", corner_radius=12)
debug_frame.pack(fill="both", expand=True)

ctk.CTkLabel(debug_frame, text="🛠️ Analiz Detayları & Karar Mantığı", font=("Consolas", 12, "bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 5))

debug_box = ctk.CTkTextbox(debug_frame, font=("Consolas", 12), fg_color="transparent", text_color="#cbd5e1", wrap="word")
debug_box.pack(fill="both", expand=True, padx=5, pady=(0, 5))

debug_box._textbox.tag_config("header", foreground=COLORS["accent"], font=("Consolas", 12, "bold"))
debug_box._textbox.tag_config("info", foreground="#94a3b8", font=("Consolas", 11, "italic"))
debug_box._textbox.tag_config("warning", foreground="#f59e0b", font=("Consolas", 11, "bold"))

debug_box.insert("end", "Sistem hazır. Veri girişi bekleniyor...\n")
debug_box.configure(state="disabled")

if __name__ == "__main__":
    app.mainloop()