import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Portale Fornitori - Tracking", page_icon="🌐", layout="wide")

# --- NASCONDI INTERFACCIA STREAMLIT (Linguetta superiore, footer, pulsanti di dev) ---
nascondi_menu = """
    <style>
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stHeader"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stFooter"] {visibility: hidden !important;}
    </style>
    """
st.markdown(nascondi_menu, unsafe_allow_html=True)

# --- CONNESSIONE A GOOGLE SHEETS ---
def connetti_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["google_key"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Logistica Tracking")
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        return None

# --- VERIFICA CREDENZIALI LOGIN ---
def verifica_login(username, password, doc_google):
    try:
        foglio_fornitori = doc_google.worksheet("Fornitori")
        dati_fornitori = pd.DataFrame(foglio_fornitori.get_all_records())
        
        utente = dati_fornitori[(dati_fornitori['Username'] == username) & (dati_fornitori['Password'] == str(password))]
        
        if not utente.empty:
            return utente.iloc[0]['Nome_Fornitore']
        return None
    except Exception as e:
        st.error(f"Errore durante la verifica delle credenziali: {e}")
        return None

# --- INIZIALIZZAZIONE STATO DELLA SESSIONE ---
if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False
    st.session_state["fornitore_nome"] = ""

if "ddt_selezionato" not in st.session_state:
    st.session_state["ddt_selezionato"] = None

doc_google = connetti_google_sheets()

# ==========================================
# 1. SCHERMATA DI LOGIN
# ==========================================
if not st.session_state["autenticato"]:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Portale Tracking</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Inserisci le tue credenziali per verificare lo stato delle spedizioni.</p>", unsafe_allow_html=True)
    
    with st.form("form_login", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            username_input = st.text_input("Username o Email")
        with col2:
            password_input = st.text_input("Password", type="password")
            
        bottone_login = st.form_submit_button("Accedi al Portale", use_container_width=True)
        
        if bottone_login:
            if doc_google:
                nome_fornitore = verifica_login(username_input, password_input, doc_google)
                if nome_fornitore:
                    st.session_state["autenticato"] = True
                    st.session_state["fornitore_nome"] = nome_fornitore
                    st.rerun()
                else:
                    st.error("❌ Username o Password errati. Riprova.")

# ==========================================
# 2. AREA RISERVATA (UTENTE AUTENTICATO)
# ==========================================
else:
    # Barra superiore con Titolo e Bottone Esci
    col_titolo, col_logout = st.columns([4, 1])
    with col_titolo:
        st.title(f"📦 Portale Spedizioni: {st.session_state['fornitore_nome']}")
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Esci", use_container_width=True):
            st.session_state["autenticato"] = False
            st.session_state["fornitore_nome"] = ""
            st.session_state["ddt_selezionato"] = None
            st.rerun()

    st.divider()

    # --- CARICAMENTO E FILTRAGGIO DATI ---
    if doc_google:
        with st.spinner("Aggiornamento dati in corso..."):
            try:
                foglio_spedizioni = doc_google.worksheet("Spedizioni")
                
                # TECNICA DI IMPORTAZIONE TESTO PURO: Salva le virgole dei pesi europei
                dati_foglio = foglio_spedizioni.get_all_values()
                if len(dati_foglio) > 0:
                    df_totale = pd.DataFrame(dati_foglio[1:], columns=dati_foglio[0])
                else:
                    df_totale = pd.DataFrame()
                
                # Applica il filtro di sicurezza per il fornitore loggato
                if 'Fornitore' in df_totale.columns:
                    df_filtrato = df_totale[df_totale['Fornitore'] == st.session_state["fornitore_nome"]]
                    # Capovolge l'ordine (mostra le righe più nuove in alto)
                    df_filtrato = df_filtrato.iloc[::-1]
                else:
                    df_filtrato = pd.DataFrame()
                    st.error("Errore del database: Colonna 'Fornitore' non trovata.")
                
            except Exception as e:
                st.error(f"Errore nel caricamento delle spedizioni: {e}")
                df_filtrato = pd.DataFrame()

        # ==========================================
        # VISTA A: DETTAGLIO DELLA SPEDIZIONE (DRILL-DOWN)
        # ==========================================
        if st.session_state["ddt_selezionato"] is not None:
            pacco = df_filtrato[df_filtrato['DDT'].astype(str) == str(st.session_state["ddt_selezionato"])]
            
            if not pacco.empty:
                pacco = pacco.iloc[0]
                
                # Bottone per tornare alla Tabella principale
                if st.button("
