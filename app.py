import streamlit as st
import requests
from icalendar import Calendar
import recurring_ical_events
from datetime import datetime, timedelta, time
import re
import pytz
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor  # Für paralleles Laden

# --- KONFIGURATION ---
BERLIN_TZ = pytz.timezone("Europe/Berlin")
CACHE_FILE = Path("calendars_cache.json")

COURSE_IDS = [
    "FN-TEA22", "FN-TEA23", "FN-TEA23A", "FN-TEA23B", "FN-TEA24A", "FN-TEA24B", "FN-TEA25", "FN-TEA25A", "FN-TEA25B",
    "FN-TEU22", "FN-TEU23", "FN-TEU24", "FN-TEU25", "FN-TFE22-1", "FN-TFE22-2", "FN-TFE23-1", "FN-TFE23-2", "FN-TFE24-1",
    "FN-TFE24-2", "FN-TFE25-1", "FN-TFE25-2", "FN-TEN22", "FN-TEN23", "FN-TEN24", "FN-TEN25", "FN-TEK22", "FN-TEK23",
    "FN-TEK24", "FN-TEK25", "FN-TSL22", "FN-TSL23", "FN-TSL24", "FN-TSL25", "FN-TSA22", "FN-TSA23", "FN-TSA24", "FN-TSA25",
    "FN-TIA25", "FN-TIT22", "FN-TIT23", "FN-TIT24", "FN-TIS22", "FN-TIS23", "FN-TIS24", "FN-TIS25", "FN-TIK22", "FN-TIK23",
    "FN-TIK24", "FN-TIK25", "FN-TIM20", "FN-TIM22", "FN-TIM23", "FN-TIM24", "FN-TLE22", "FN-TLE23", "FN-TLE24", "FN-TLE25",
    "FN-TLS22", "FN-TLS24", "FN-TLS25", "FN-TMA23", "FN-TMA24", "FN-TMA25", "FN-TFS22", "FN-TFS23", "FN-TFS24", "FN-TFS25",
    "FN-TMK22-1", "FN-TMK22-2", "FN-TMK23-1", "FN-TMK23-2", "FN-TMK24-1", "FN-TMK24-2", "FN-TMK25-1", "FN-TMK25-2",
    "FN-TML22", "FN-TML23", "FN-TMM22", "FN-TMM23", "FN-TMP22", "FN-TMP23", "FN-TMP24", "FN-TMP25", "FN-TMT24", "FN-TMT25",
    "FN-TWE22", "FN-TWE23", "FN-TWE24", "FN-TWE25", "FN-TWI22-1", "FN-TWI22-2", "FN-TWI23-1", "FN-TWI23-2", "FN-TWI24-1",
    "FN-TWI24-2", "FN-TWI25-1", "FN-TWI25-2"
]

# --- HILFSFUNKTIONEN ---
def extrahiere_raum_code(location_str):
    if not location_str: return None
    match = re.search(r'([A-Z]\d{3})', str(location_str))
    return match.group(1) if match else None

def normalize_to_berlin(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None: return BERLIN_TZ.localize(dt)
        return dt.astimezone(BERLIN_TZ)
    return dt

def get_today_str():
    return datetime.now(BERLIN_TZ).strftime("%Y-%m-%d")

# --- PARALLELES LADEN ---
def fetch_single_calendar(c_id):
    """Hilfsfunktion für einen einzelnen Request."""
    try:
        r = requests.get(f"https://dhbw.app/ical/{c_id}", timeout=10)
        if r.status_code == 200:
            return c_id, r.text
    except:
        return c_id, None
    return c_id, None

def fetch_and_cache_data():
    calendars = {}
    status_text = st.empty()
    status_text.info("🚀 Starte parallele Synchronisierung...")
    progress_bar = st.progress(0)
    
    # Parallelisierung mit 20 Threads für maximale Geschwindigkeit
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_single_calendar, COURSE_IDS))
    
    for c_id, ics_text in results:
        if ics_text:
            calendars[c_id] = ics_text
            
    cache_content = {"last_sync": get_today_str(), "data": calendars}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_content, f, ensure_ascii=False)
    
    status_text.empty()
    progress_bar.empty()
    return calendars

@st.cache_data(ttl=86400) # Cache die verarbeiteten Schedules für 24h
def get_room_schedules_cached(all_data_json, target_date):
    """Verarbeitet die rohen ICS-Daten zu einem sauberen Zeitplan pro Raum."""
    # all_data_json wird als Key für den Cache genutzt
    all_data = json.loads(all_data_json)
    day_start = BERLIN_TZ.localize(datetime.combine(target_date, time.min))
    day_end = BERLIN_TZ.localize(datetime.combine(target_date, time.max))
    raum_belegungen = {}
    
    for c_id, ics_text in all_data.items():
        try:
            cal = Calendar.from_ical(ics_text)
            events = recurring_ical_events.of(cal).between(day_start, day_end)
            for event in events:
                raum = extrahiere_raum_code(event.get("LOCATION"))
                if raum:
                    start = normalize_to_berlin(event.get("DTSTART").dt)
                    end = normalize_to_berlin(event.get("DTEND").dt)
                    summary = str(event.get("SUMMARY"))
                    if raum not in raum_belegungen: raum_belegungen[raum] = []
                    if not any(s == start and e == end for s, e, sum in raum_belegungen[raum]):
                        raum_belegungen[raum].append((start.isoformat(), end.isoformat(), summary))
        except: continue
    return raum_belegungen

def load_data():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_content = json.load(f)
            if cache_content.get("last_sync") == get_today_str():
                return cache_content["data"], True
    return fetch_and_cache_data(), False

# --- UI SETUP ---
st.set_page_config(page_title="DHBW Raumfinder", page_icon="🏫", layout="wide")
st.title("🏫 DHBW Raum-Checker & Planer")

all_data, was_cached = load_data()
current_now = datetime.now(BERLIN_TZ)

with st.sidebar:
    st.header("Daten-Status")
    if was_cached:
        st.success("Daten von heute geladen.")
    else:
        st.warning("Daten neu geladen.")
    
    if st.button("🔄 Alles neu laden"):
        st.cache_data.clear()
        all_data = fetch_and_cache_data()
        st.rerun()
    st.divider()
    
    st.write("**Ansicht wählen:**")
    modus = st.radio("Modus", ["Freie Räume", "Raum-Details"], horizontal=True, label_visibility="collapsed")

# --- HAUPTLOGIK ---
# Konvertiere all_data für den Cache-Key in String
all_data_str = json.dumps(all_data)

if modus == "Freie Räume":
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Zeitpunkt:**")
        check_type = st.radio("Zeit", ["Jetzt", "Spezifisch"], horizontal=True, label_visibility="collapsed")
    with col2:
        st.write("**Gebäude:**")
        gebaeude = st.radio("Gebäude", ["Alle", "N", "H", "E"], horizontal=True, label_visibility="collapsed")
    
    if check_type == "Jetzt":
        target_dt = current_now
    else:
        c1, c2 = st.columns(2)
        d = c1.date_input("Datum:", current_now.date())
        t = c2.time_input("Uhrzeit:", current_now.time())
        target_dt = BERLIN_TZ.localize(datetime.combine(d, t))

    if st.button("🔍 Verfügbarkeit prüfen", type="primary"):
        # Nutze den schnellen Cache für die Raumberechnung
        schedules_raw = get_room_schedules_cached(all_data_str, target_dt.date())
        ergebnisse = []
        filter_char = gebaeude[0] if gebaeude != "Alle" else ""
        
        for raum, events in schedules_raw.items():
            if filter_char and not raum.startswith(filter_char): continue
            
            ist_belegt = False
            naechster_start = None
            
            # Da ISO-Strings im Cache, zurück zu datetime für Vergleich
            sorted_events = sorted(events, key=lambda x: x[0])
            for s_str, e_str, summary in sorted_events:
                s = datetime.fromisoformat(s_str)
                e = datetime.fromisoformat(e_str)
                if s <= target_dt < e:
                    ist_belegt = True
                    break
                if s > target_dt:
                    naechster_start = s
                    break
            
            if not ist_belegt:
                frei_bis = naechster_start.strftime("%H:%M") if naechster_start else "Ende des Tages"
                ergebnisse.append((raum, frei_bis))
        
        ergebnisse.sort()
        st.divider()
        if ergebnisse:
            cols = st.columns(3)
            for idx, (raum, bis) in enumerate(ergebnisse):
                cols[idx % 3].info(f"**{raum}** \n Frei bis {bis}")
        else:
            st.error("Keine freien Räume gefunden.")

else:
    # Modus: Raum-Details
    schedules_raw = get_room_schedules_cached(all_data_str, current_now.date())
    alle_raeume = sorted(list(schedules_raw.keys()))
    
    st.write("**Raum wählen:**")
    selected_raum = st.selectbox("Raum auswählen", alle_raeume, label_visibility="collapsed")
    
    if selected_raum:
        st.subheader(f"Tagesplan für Raum {selected_raum}")
        belegungen = sorted(schedules_raw[selected_raum], key=lambda x: x[0])
        
        for s_str, e_str, summary in belegungen:
            s = datetime.fromisoformat(s_str)
            e = datetime.fromisoformat(e_str)
            is_current = s <= current_now < e
            label = "🔴 AKTUELL BELEGT" if is_current else "📅 Vorlesung"
            with st.expander(f"{label}: {s.strftime('%H:%M')} - {e.strftime('%H:%M')}", expanded=is_current):
                st.write(f"**Inhalt:** {summary}")
        
        ist_belegt_jetzt = any(datetime.fromisoformat(s) <= current_now < datetime.fromisoformat(e) for s, e, sum in belegungen)
        if not ist_belegt_jetzt:
            st.success(f"Raum {selected_raum} ist momentan frei.")
