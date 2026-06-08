import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Portale Fornitori - Tracking", page_icon="🌐", layout="wide")

# --- NASCONDI INTERFACCIA STREAMLIT (OPZIONALE) ---
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
        
        # Filtra per username e password corretti
        utente = dati_fornitori[(dati_fornitori['Username'] == username) & (dati_fornitori['Password'] == str(password))]
        
        if not utente.empty:
            return utente.iloc[0]['Nome_Fornitore']
        return None
    except Exception as e:
        st.error(f"Errore durante la verifica delle credenziali: {e}")
        return None

# --- INIZIALIZZAZIONE SESSIONE ---
if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False
    st.session_state["fornitore_nome"] = ""

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
# 2. AREA RISERVATA (LOGGED IN)
# ==========================================
else:
    # Barra superiore con titolo e Logout
    col_titolo, col_logout = st.columns([4, 1])
    with col_titolo:
        st.title(f"📦 Portale Spedizioni: {st.session_state['fornitore_nome']}")
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Esci", use_container_width=True):
            st.session_state["autenticato"] = False
            st.session_state["fornitore_nome"] = ""
            st.rerun()

    st.divider()

    # --- SCARICAMENTO E FILTRO DATI ---
    if doc_google:
        with st.spinner("Aggiornamento dati in corso..."):
            try:
                foglio_spedizioni = doc_google.worksheet("Spedizioni")
                df_totale = pd.DataFrame(foglio_spedizioni.get_all_records())
                
                # Filtro di sicurezza basato sul fornitore loggato
                if 'Fornitore' in df_totale.columns:
                    df_filtrato = df_totale[df_totale['Fornitore'] == st.session_state["fornitore_nome"]]
                    # Capovolge la tabella per mostrare i record più recenti in alto
                    df_filtrato = df_filtrato.iloc[::-1]
                else:
                    df_filtrato = pd.DataFrame()
                    st.error("Errore di configurazione: Colonna 'Fornitore' non trovata nel foglio Spedizioni.")
                
            except Exception as e:
                st.error(f"Errore nel caricamento delle spedizioni: {e}")
                df_filtrato = pd.DataFrame()

        # CONTROLLO DATI DISPONIBILI
        if df_filtrato.empty:
            st.info("Nessuna spedizione trovata per il tuo account.")
        else:
            # --- DASHBOARD DEI CONTATORI ---
            st.subheader("Stato Attuale delle Spedizioni")
            totali = len(df_filtrato)
            consegnati = len(df_filtrato[df_filtrato['Stato'] == 'Consegnato'])
            in_viaggio = len(df_filtrato[df_filtrato['Stato'] == 'In Carico'])
            anomalie = len(df_filtrato[df_filtrato['Stato'].isin(['Respinto', 'Eliminato'])])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Spedizioni Totali", totali)
            c2.metric("✅ Consegnate", consegnati)
            c3.metric("🚚 In Consegna", in_viaggio)
            c4.metric("⚠️ Anomalie/Respinte", anomalie)
            
            st.divider()
            
            # --- BARRA DI RICERCA ---
            st.subheader("🔍 Ricerca Spedizione")
            cerca_ddt = st.text_input("Inserisci il numero di DDT o il nome del Destinatario per filtrare la lista:")
            
            if cerca_ddt:
                df_visualizza = df_filtrato[
                    df_filtrato['DDT'].astype(str).str.contains(cerca_ddt, case=False, na=False) | 
                    df_filtrato['Destinatario'].astype(str).str.contains(cerca_ddt, case=False, na=False)
                ]
            else:
                df_visualizza = df_filtrato

            st.divider()
            st.subheader("📦 Elenco Spedizioni (Clicca su una riga per aprire i dettagli)")

            if df_visualizza.empty:
                st.info("Nessuna spedizione corrisponde ai criteri di ricerca.")
            else:
                # --- LISTA AD ESPANSIONE INTERATTIVA (FISARMONICA) ---
                for index, pacco in df_visualizza.iterrows():
                    
                    # Generazione del titolo della riga principale
                    ddt_val = pacco.get('DDT', 'N/D')
                    dest_val = pacco.get('Destinatario', 'N/D')
                    stato_val = pacco.get('Stato', 'Non definito')
                    
                    titolo_riga = f"DDT: {ddt_val} ➔ {dest_val} | Stato attuale: {stato_val}"
                    
                    # Creazione del blocco cliccabile
                    with st.expander(titolo_riga):
                        
                        # Informazioni dettagliate interne
                        col_det1, col_det2 = st.columns(2)
                        with col_det1:
                            st.markdown(f"📍 **Indirizzo di Consegna:** {pacco.get('Indirizzo', 'N/D')}")
                        with col_det2:
                            st.markdown(f"⚖️ **Peso Lordo Spedizione:** {pacco.get('Peso Lordo', 'N/D')} kg")
                        
                        st.divider()
                        st.markdown("#### 🕒 Cronologia e Storico Stati (Timeline)")
                        
                        stato_attuale = pacco.get('Stato', '')
                        posizione_gps = pacco.get('Posizione', 'Non disponibile')
                        
                        # COSTRUZIONE DELLA TIMELINE VISIVA IN BASE ALLO STATO CORRENTE
                        if stato_attuale == "Eliminato":
                            st.error(f"❌ **Eliminato** — La spedizione è stata annullata o rimossa dal magazzino.")
                        else:
                            # STEP 3: Stato Finale (Consegnato o Respinto)
                            if stato_attuale == "Consegnato":
                                st.success(f"✅ **CONSEGNATO**<br>📍 Coordinate GPS Registrate: {posizione_gps}", unsafe_allow_html=True)
                                st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                            elif stato_attuale == "Respinto":
                                st.error(f"⚠️ **RESPINTO DAL CLIENTE**<br>📍 Coordinate GPS Registrate: {posizione_gps}", unsafe_allow_html=True)
                                st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                                
                            # STEP 2: Presa in carico sul mezzo
                            if stato_attuale in ["In Carico", "Consegnato", "Respinto"]:
                                st.info(f"🚚 **IN CONSEGNA (Sul furgone)** — Il corriere ha caricato il pacco ed è in viaggio.")
                                st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                                
                            # STEP 1: Arrivo in Hub Logistico
                            if stato_attuale in ["In Magazzino", "In Carico", "Consegnato", "Respinto"]:
                                st.warning(f"🏢 **IN MAGAZZINO** — Il pacco è stato preso in carico presso l'hub principale.")
