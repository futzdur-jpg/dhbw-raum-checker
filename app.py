import streamlit as st
import requests
from icalendar import Calendar
import recurring_ical_events
from datetime import datetime, timedelta, time
import re
import pytz
import json
from pathlib import Path

# --- KONFIGURATION & DATEIPFADE ---
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
        if dt.tzinfo is None:
            return BERLIN_TZ.localize(dt)
        return dt.astimezone(BERLIN_TZ)
    return dt

def get_today_str():
    return datetime.now(BERLIN_TZ).strftime("%Y-%m-%d")

# --- DATEN-MANAGEMENT (CACHE) ---

def fetch_and_cache_data():
    """Lädt alle Kalender von der API und speichert sie lokal."""
    calendars = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, c_id in enumerate(COURSE_IDS):
        status_text.text(f"Synchronisiere Kurs: {c_id}...")
        try:
            r = requests.get(f"https://dhbw.app/ical/{c_id}", timeout=10)
            if r.status_code == 200:
                calendars[c_id] = r.text
        except:
            continue
        progress_bar.progress((i + 1) / len(COURSE_IDS))
    
    cache_content = {
        "last_sync": get_today_str(),
        "data": calendars
    }
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_content, f, ensure_ascii=False)
    
    status_text.empty()
    progress_bar.empty()
    return calendars

def load_data():
    """Lädt Daten aus dem Cache oder erzwingt Sync, wenn veraltet."""
    today = get_today_str()
    
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_content = json.load(f)
                if cache_content.get("last_sync") == today:
                    return cache_content["data"], True
        except:
            pass
            
    # Falls kein Cache oder veraltet: Neu laden
    return fetch_and_cache_data(), False

# --- UI SETUP ---
st.set_page_config(page_title="DHBW Raumfinder", page_icon="🏫")
st.title("🏫 DHBW Raum-Checker FN")

# Daten laden (einmalig pro App-Start/Refresh)
all_data, was_cached = load_data()

with st.sidebar:
    st.header("Daten-Status")
    if was_cached:
        st.success("Daten sind auf dem neuesten Stand.")
    else:
        st.info("Daten wurden soeben frisch geladen.")
    
    if st.button("Jetzt manuell synchronisieren"):
        all_data = fetch_and_cache_data()
        st.rerun()

    st.divider()
    gebaeude_filter = st.selectbox("Gebäude wählen:", ["Alle Gebäude", "N Gebäude", "H Gebäude", "E Gebäude"])
    filter_char = gebaeude_filter[0] if gebaeude_filter != "Alle Gebäude" else ""

# Modus-Auswahl im Hauptbereich
modus = st.radio("Zeitpunkt der Prüfung:", ["Jetzt", "Spezifisches Datum/Uhrzeit"], horizontal=True)

if modus == "Jetzt":
    target_dt = datetime.now(BERLIN_TZ)
else:
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input("Datum wählen:", datetime.now(BERLIN_TZ).date())
    with col2:
        t = st.time_input("Uhrzeit wählen:", datetime.now(BERLIN_TZ).time())
    target_dt = BERLIN_TZ.localize(datetime.combine(d, t))

# --- ANALYSE-LOGIK ---
if st.button("Verfügbarkeit prüfen", type="primary"):
    with st.spinner("Analysiere Raumbelegungen..."):
        # Zeitbereich für den gesamten Ziel-Tag (für recurring events nötig)
        day_start = BERLIN_TZ.localize(datetime.combine(target_dt.date(), time.min))
        day_end = BERLIN_TZ.localize(datetime.combine(target_dt.date(), time.max))
        
        inventar = set()
        raum_belegungen = {}

        for c_id, ics_text in all_data.items():
            try:
                cal = Calendar.from_ical(ics_text)
                events_today = recurring_ical_events.of(cal).between(day_start, day_end)
                
                for event in events_today:
                    raum = extrahiere_raum_code(event.get("LOCATION"))
                    if raum:
                        inventar.add(raum)
                        start = normalize_to_berlin(event.get("DTSTART").dt)
                        end = normalize_to_berlin(event.get("DTEND").dt)
                        
                        if raum not in raum_belegungen: raum_belegungen[raum] = []
                        raum_belegungen[raum].append((start, end))
            except: continue

        # Ergebnisse filtern und aufbereiten
        ergebnisse = []
        for raum in inventar:
            if filter_char and not raum.startswith(filter_char): continue
            
            belegungen = sorted(raum_belegungen.get(raum, []), key=lambda x: x[0])
            ist_belegt = False
            naechster_start = None
            
            for start, end in belegungen:
                if start <= target_dt < end:
                    ist_belegt = True
                    break
                if start > target_dt:
                    naechster_start = start
                    break
            
            if not ist_belegt:
                frei_bis = naechster_start.strftime("%H:%M") if naechster_start else "Ende des Tages"
                ergebnisse.append((raum, frei_bis))

        # --- ANZEIGE ---
        ergebnisse.sort()
        st.divider()
        st.subheader(f"Freie Räume am {target_dt.strftime('%d.%m.')} um {target_dt.strftime('%H:%M')}:")
        
        if ergebnisse:
            cols = st.columns(2) # Zweispaltige Anzeige für bessere Übersicht
            for idx, (raum, bis) in enumerate(ergebnisse):
                with cols[idx % 2].container():
                    st.info(f"**{raum}** \n(Frei bis {bis})")
        else:
            st.error("Keine freien Räume gefunden.")
