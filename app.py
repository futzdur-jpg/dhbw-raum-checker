import streamlit as st
import requests
from icalendar import Calendar
import recurring_ical_events
from datetime import datetime
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

# Streamlit Caching: Lädt die Kalenderdaten nur einmal pro Tag herunter
@st.cache_data(ttl=86400)
def fetch_all_calendars():
    calendars = {}
    for c_id in COURSE_IDS:
        try:
            r = requests.get(f"https://dhbw.app/ical/{c_id}", timeout=10)
            if r.status_code == 200:
                calendars[c_id] = r.text
        except:
            continue
    return calendars

# --- UI SETUP ---
st.set_page_config(page_title="DHBW Raumfinder", page_icon="🏫")
st.title("🏫 DHBW Raum-Checker FN")
st.write("Finde schnell einen freien Raum zum Lernen.")

gebaeude_filter = st.selectbox("Welches Gebäude?", ["Alle Gebäude", "N (Neubau)", "H (Hauptgebäude)", "E (Elektrotechnik)"])
filter_char = gebaeude_filter[0] if gebaeude_filter != "Alle Gebäude" else ""

if st.button("Jetzt freie Räume suchen", type="primary"):
    with st.spinner("Analysiere Vorlesungspläne..."):
        all_data = fetch_all_calendars()
        now = datetime.now()
        
        inventar = set()
        belegt = set()

        for c_id, ics_text in all_data.items():
            try:
                cal = Calendar.from_ical(ics_text)
                # Inventar lernen
                for event in cal.walk('VEVENT'):
                    r = extrahiere_raum_code(event.get("LOCATION"))
                    if r: inventar.add(r)
                
                # Belegung prüfen
                active_events = recurring_ical_events.of(cal).at(now)
                for event in active_events:
                    r_b = extrahiere_raum_code(event.get("LOCATION"))
                    if r_b: belegt.add(r_b)
            except:
                continue

        # Differenzmenge berechnen
        frei = inventar - belegt
        
        if filter_char:
            resultat = sorted([r for r in frei if r.startswith(filter_char)])
        else:
            resultat = sorted(list(frei))

        # Ergebnisse anzeigen
        st.divider()
        st.subheader(f"Freie Räume um {now.strftime('%H:%M')} Uhr:")
        
        if resultat:
            cols = st.columns(2) # Zweispaltige Anzeige für Mobile
            for idx, r in enumerate(resultat):
                cols[idx % 2].success(f"**{r}**")
        else:
            st.error("Keine freien Räume gefunden.")