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
                if st.button("⬅️ Torna alla lista delle spedizioni"):
                    st.session_state["ddt_selezionato"] = None
                    st.rerun()
                
                st.markdown(f"## Dettaglio Spedizione DDT: **{pacco['DDT']}**")
                
                # Scheda riassuntiva info pacco
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"👤 **Destinatario:** {pacco.get('Destinatario', 'N/D')}")
                    st.markdown(f"📍 **Indirizzo di Consegna:** {pacco.get('Indirizzo', 'N/D')}")
                with col_info2:
                    st.markdown(f"⚖️ **Peso Lordo Spedizione:** {pacco.get('Peso Lordo', 'N/D')} kg")
                    st.markdown(f"📦 **Numero Colli:** {pacco.get('Colli', 'N/D')}")
                    st.markdown(f"🏷️ **Stato Attuale:** `{pacco.get('Stato', 'N/D')}`")
                
                st.divider()
                st.subheader("🕒 Cronologia e Storico Stati")
                
                # --- RECUPERO DATI TEMPORALI (Timeline Snella) ---
                stato_attuale = pacco.get('Stato', '')
                ora_car = pacco.get('Navigazione / Ora_Carico', pacco.get('Ora_Carico', 'N/D'))
                ora_esi = pacco.get('Ora_Esito', 'N/D')
                
                # --- COSTRUZIONE TIMELINE GRAFICA VELOCE ---
                if stato_attuale == "Eliminato":
                    st.error("❌ **Eliminato** — La spedizione è stata annullata o rimossa dal magazzino.")
                else:
                    # Passo 3: Esito finale su strada (Richiede Ora)
                    if stato_attuale == "Consegnato":
                        st.success(f"✅ **CONSEGNATO** \n🕒 Ora: {ora_esi}")
                        st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                    elif stato_attuale == "Respinto":
                        st.error(f"⚠️ **RESPINTO DAL CLIENTE** \n🕒 Ora: {ora_esi}")
                        st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                        
                    # Passo 2: Presa in carico furgone (Richiede Ora)
                    if stato_attuale in ["In Carico", "Consegnato", "Respinto"]:
                        st.info(f"🚚 **IN CONSEGNA (Sul furgone)** \n🕒 Ora: {ora_car}")
                        st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                        
                    # Passo 1: Stoccaggio iniziale hub (Solo testuale)
                    if stato_attuale in ["In Magazzino", "In Carico", "Consegnato", "Respinto"]:
                        st.warning("🏢 **IN MAGAZZINO** — Il pacco è arrivato ed è stato elaborato nell'hub logistico.")
            else:
                st.error("Errore: Spedizione non trovata.")
                st.session_state["ddt_selezionato"] = None

        # ==========================================
        # VISTA B: TABELLA GENERALE PERSONALIZZATA
        # ==========================================
        else:
            if df_filtrato.empty:
                st.info("Nessuna spedizione trouvata per il tuo account.")
            else:
                # Piccolo Dashboard contatori veloci
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
                
                # Barra di ricerca dinamica
                st.subheader("Elenco Spedizioni")
                cerca_ddt = st.text_input("Filtra la tabella inserendo il numero di DDT o il nome del Destinatario:")
                
                if cerca_ddt:
                    df_visualizza = df_filtrato[
                        df_filtrato['DDT'].astype(str).str.contains(cerca_ddt, case=False, na=False) | 
                        df_filtrato['Destinatario'].astype(str).str.contains(cerca_ddt, case=False, na=False)
                    ]
                else:
                    df_visualizza = df_filtrato

                st.markdown("<br>", unsafe_allow_html=True)

                if df_visualizza.empty:
                    st.warning("Nessuna spedizione corrisponde ai criteri di ricerca.")
                else:
                    # --- DISEGNO DELLA GRIGLIA TABELLARE CUSTOM ---
                    
                    # Intestazioni delle colonne
                    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 3, 2, 1.5])
                    col_h1.markdown("**Numero DDT**")
                    col_h2.markdown("**Ragione Sociale / Destinatario**")
                    col_h3.markdown("**Stato Spedizione**")
                    col_h4.markdown("**Azioni**")
                    
                    # Linea marcata sotto l'intestazione
                    st.markdown("<hr style='margin: 4px 0px 12px 0px; border-bottom: 2px solid #4F4F4F;'>", unsafe_allow_html=True)
                    
                    # Generazione ciclica delle righe di dati
                    for index, pacco in df_visualizza.iterrows():
                        c1, c2, c3, c4 = st.columns([2, 3, 2, 1.5])
                        
                        # Mostra i testi allineandoli verticalmente al pulsante
                        c1.markdown(f"<p style='margin-top:8px;'>{pacco.get('DDT', 'N/D')}</p>", unsafe_allow_html=True)
                        c2.markdown(f"<p style='margin-top:8px;'>{pacco.get('Destinatario', 'N/D')}</p>", unsafe_allow_html=True)
                        c3.markdown(f"<p style='margin-top:8px;'>`{pacco.get('Stato', '')}`</p>", unsafe_allow_html=True)
                        
                        # Il pulsante di azione che apre la vista di dettaglio
                        with c4:
                            if st.button("Apri ➔", key=f"btn_{pacco.get('DDT', index)}", use_container_width=True):
                                st.session_state["ddt_selezionato"] = pacco['DDT']
                                st.rerun()
                        
                        # Linea grigia chiarissima per dividerive visivamente i record
                        st.markdown("<hr style='margin: 6px 0px; opacity: 0.15;'>", unsafe_allow_html=True)
