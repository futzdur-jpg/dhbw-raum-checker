import streamlit as st
import requests
from icalendar import Calendar
import recurring_ical_events
from datetime import datetime, timedelta, time
import re

# --- KONFIGURATION & DATEN ---
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

def extrahiere_raum_code(location_str):
    if not location_str: return None
    match = re.search(r'([A-Z]\d{3})', str(location_str))
    return match.group(1) if match else None

@st.cache_data(ttl=3600) # Cache für eine Stunde
def fetch_all_calendars():
    calendars = {}
    for c_id in COURSE_IDS:
        try:
            r = requests.get(f"https://dhbw.app/ical/{c_id}", timeout=10)
            if r.status_code == 200:
                calendars[c_id] = r.text
        except: continue
    return calendars

# --- UI SETUP ---
st.set_page_config(page_title="DHBW Raumfinder", page_icon="🏫")
st.title("🏫 DHBW Raum-Checker FN")

gebaeude_filter = st.selectbox("Gebäude wählen:", ["Alle Gebäude", "N (Neubau)", "H (Hauptgebäude)", "E (Elektrotechnik)"])
filter_char = gebaeude_filter[0] if gebaeude_filter != "Alle Gebäude" else ""

if st.button("Jetzt prüfen", type="primary"):
    with st.spinner("Analysiere Zeitpläne..."):
        all_data = fetch_all_calendars()
        now = datetime.now()
        # Zeitbereich für "heute" definieren
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)
        
        inventar = set()
        raum_belegungen = {} # raum: [start_zeiten_der_vorlesungen]

        for c_id, ics_text in all_data.items():
            try:
                cal = Calendar.from_ical(ics_text)
                # Alle Events für heute laden
                events_today = recurring_ical_events.of(cal).between(today_start, today_end)
                
                for event in events_today:
                    raum = extrahiere_raum_code(event.get("LOCATION"))
                    if raum:
                        inventar.add(raum)
                        start = event.get("DTSTART").dt
                        # Falls Zeitzone im Kalender, auf "naive" umwandeln für Vergleich
                        if hasattr(start, "tzinfo"): start = start.replace(tzinfo=None)
                        end = event.get("DTEND").dt
                        if hasattr(end, "tzinfo"): end = end.replace(tzinfo=None)
                        
                        if raum not in raum_belegungen: raum_belegungen[raum] = []
                        raum_belegungen[raum].append((start, end))
            except: continue

        # Ergebnisse auswerten
        ergebnisse = []
        for raum in inventar:
            if filter_char and not raum.startswith(filter_char): continue
            
            belegungen = sorted(raum_belegungen.get(raum, []), key=lambda x: x[0])
            
            ist_belegt = False
            naechster_start = None
            
            for start, end in belegungen:
                if start <= now <= end:
                    ist_belegt = True
                    break
                if start > now:
                    naechster_start = start
                    break
            
            if not ist_belegt:
                frei_bis = naechster_start.strftime("%H:%M") if naechster_start else "Ende des Tages"
                ergebnisse.append((raum, frei_bis))

        # Anzeige
        ergebnisse.sort()
        st.divider()
        if ergebnisse:
            st.subheader(f"Freie Räume (Stand {now.strftime('%H:%M')}):")
            for raum, bis in ergebnisse:
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    col1.success(f"**{raum}**")
                    col2.info(f"Frei bis {bis}")
        else:
            st.error("Keine freien Räume gefunden.")