import streamlit as st
import pandas as pd
import json
import gspread
import math
from oauth2client.service_account import ServiceAccountCredentials

# CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Portale Fornitori - Tracking", page_icon="🌐", layout="wide")

# NASCONDI INTERFACCIA STREAMLIT
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

# ==========================================
# 1. CONNESSIONE AI FILE (CON CACHE DI RETE)
# ==========================================
@st.cache_resource
def inizializza_connessioni_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["google_key"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        doc_princ = client.open("Logistica Tracking")
        try:
            doc_arch = client.open("Archivio_Logistica")
        except:
            doc_arch = None
            
        return doc_princ, doc_arch
    except Exception as e:
        st.error(f"Errore critico di inizializzazione: {e}")
        return None, None

# ==========================================
# 2. CARICAMENTO DATI (CON CACHE DI MEMORIA)
# ==========================================
@st.cache_data(ttl=600)
def cached_get_fornitori(_doc_google):
    foglio_fornitori = _doc_google.worksheet("Fornitori")
    return pd.DataFrame(foglio_fornitori.get_all_records())

@st.cache_data(ttl=300)
def cached_get_spedizioni(_doc_google, _doc_archivio):
    dati_principale = _doc_google.worksheet("Spedizioni").get_all_values()
    df_principale = pd.DataFrame(dati_principale[1:], columns=dati_principale[0]) if len(dati_principale) > 1 else pd.DataFrame()
    
    df_archivio_sped = pd.DataFrame()
    if _doc_archivio:
        try:
            dati_arch_sped = _doc_archivio.worksheet("Spedizioni").get_all_values()
            if len(dati_arch_sped) > 1:
                df_archivio_sped = pd.DataFrame(dati_arch_sped[1:], columns=dati_arch_sped[0])
        except:
            pass
    return pd.concat([df_principale, df_archivio_sped], ignore_index=True).fillna("")

@st.cache_data(ttl=300)
def cached_get_storico(_doc_google, _doc_archivio):
    df_st_principale = pd.DataFrame()
    try:
        dati_st_princ = _doc_google.worksheet("Storico").get_all_values()
        if len(dati_st_princ) > 1:
            df_st_principale = pd.DataFrame(dati_st_princ[1:], columns=dati_st_princ[0])
    except:
        pass
        
    df_st_archivio = pd.DataFrame()
    if _doc_archivio:
        try:
            dati_st_arch = _doc_archivio.worksheet("Storico").get_all_values()
            if len(dati_st_arch) > 1:
                df_st_archivio = pd.DataFrame(dati_st_arch[1:], columns=dati_st_arch[0])
        except:
            pass
            
    return pd.concat([df_st_principale, df_st_archivio], ignore_index=True).fillna("")

# VERIFICA CREDENZIALI LOGIN
def verifica_login(username, password, doc_google):
    try:
        dati_fornitori = cached_get_fornitori(doc_google)
        utente = dati_fornitori[(dati_fornitori['Username'] == username) & (dati_fornitori['Password'] == str(password))]
        
        if not utente.empty:
            return utente.iloc[0]['Nome_Fornitore']
        return None
    except Exception as e:
        st.error(f"Errore durante la verifica delle credenziali: {e}")
        return None

# FUNZIONE PER RESETTARE LA PAGINA SE CAMBIA IL FILTRO
def resetta_pagina():
    st.session_state["pagina_corrente"] = 1

# INIZIALIZZAZIONE STATO DELLA SESSIONE
if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False
    st.session_state["fornitore_nome"] = ""

if "id_pacco_selezionato" not in st.session_state:
    st.session_state["id_pacco_selezionato"] = None

if "pagina_corrente" not in st.session_state:
    st.session_state["pagina_corrente"] = 1

# ==========================================
# ESECUZIONE CONNESSIONE INIZIALE CON SPINNER VISIVO
# ==========================================
with st.spinner("Connessione ai server in corso, attendere..."):
    doc_google, doc_archivio = inizializza_connessioni_google()

# ==========================================
# 3. SCHERMATA DI LOGIN
# ==========================================
if not st.session_state["autenticato"]:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Portale TP Manetti</h1>", unsafe_allow_html=True)
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
# 4. AREA RISERVATA (UTENTE AUTENTICATO)
# ==========================================
else:
    col_titolo, col_logout = st.columns([4, 1])
    with col_titolo:
        st.title(f"📦 Portale Spedizioni: {st.session_state['fornitore_nome']}")
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Esci", use_container_width=True):
            st.session_state["autenticato"] = False
            st.session_state["fornitore_nome"] = ""
            st.session_state["id_pacco_selezionato"] = None
            st.session_state["pagina_corrente"] = 1
            st.rerun()

    st.divider()

    # UI FILTRO TEMPORALE GLOBALE
    col_filtro, _ = st.columns([1.5, 3])
    with col_filtro:
        filtro_tempo = st.selectbox(
            "📅 Visualizza spedizioni di:",
            ["Tutto", "Oggi", "Ultimi 5 giorni", "Ultimi 15 giorni", "Ultimo mese", "Ultimi 3 mesi", "Ultimi 6 mesi", "Quest'anno"],
            index=4,
            on_change=resetta_pagina 
        )

    # CARICAMENTO E FILTRAGGIO DATI
    if doc_google:
        with st.spinner("Sincronizzazione dati in corso..."):
            try:
                df_totale = cached_get_spedizioni(doc_google, doc_archivio)
                df_storico = cached_get_storico(doc_google, doc_archivio)
                
                if 'Stato' in df_totale.columns:
                    df_totale['Stato'] = df_totale['Stato'].replace('In Carico', 'In Consegna')
                else:
                    df_totale = pd.DataFrame()

                # APPLICAZIONE DEI FILTRI DI RICERCA E TEMPO
                if not df_totale.empty and 'Fornitore' in df_totale.columns:
                    df_filtrato = df_totale[df_totale['Fornitore'] == st.session_state["fornitore_nome"]]
                    
                    if 'Ordinamento' in df_filtrato.columns and filtro_tempo != "Tutto":
                        date_convertite = pd.to_datetime(
                            df_filtrato['Ordinamento'].astype(str).str[:8], 
                            format='%Y%m%d', 
                            errors='coerce'
                        )
                        oggi = pd.Timestamp.today().normalize()
                        
                        if filtro_tempo == "Oggi":
                            df_filtrato = df_filtrato[date_convertite >= oggi]
                        elif filtro_tempo == "Ultimi 5 giorni":
                            df_filtrato = df_filtrato[date_convertite >= (oggi - pd.Timedelta(days=5))]
                        elif filtro_tempo == "Ultimi 15 giorni":
                            df_filtrato = df_filtrato[date_convertite >= (oggi - pd.Timedelta(days=15))]
                        elif filtro_tempo == "Ultimo mese":
                            df_filtrato = df_filtrato[date_convertite >= (oggi - pd.Timedelta(days=30))]
                        elif filtro_tempo == "Ultimi 3 mesi":
                            df_filtrato = df_filtrato[date_convertite >= (oggi - pd.Timedelta(days=90))]
                        elif filtro_tempo == "Ultimi 6 mesi":
                            df_filtrato = df_filtrato[date_convertite >= (oggi - pd.Timedelta(days=180))]
                        elif filtro_tempo == "Quest'anno":
                            df_filtrato = df_filtrato[date_convertite.dt.year == oggi.year]
                            
                    df_filtrato = df_filtrato.iloc[::-1]
                else:
                    df_filtrato = pd.DataFrame()
                    st.error("Nessun dato valido disponibile o Fornitore non configurato.")
                    
            except Exception as e:
                st.error(f"Errore nel caricamento delle spedizioni: {e}")
                df_filtrato = pd.DataFrame()

        # ==========================================
        # VISTA A: DETTAGLIO DELLA SPEDIZIONE (DRILL-DOWN)
        # ==========================================
        if st.session_state["id_pacco_selezionato"] is not None:
            pacco_target = df_filtrato[df_filtrato['ID_Pacco'].astype(str) == str(st.session_state["id_pacco_selezionato"])]
            
            if not pacco_target.empty:
                pacco = pacco_target.iloc[0]
                
                if st.button("⬅️ Torna alla lista delle spedizioni"):
                    st.session_state["id_pacco_selezionato"] = None
                    st.rerun()
                
                st.markdown(f"## Dettaglio Spedizione DDT: **{pacco.get('DDT', 'N/D')}**")
                
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
                
                movimenti_trovati = False
                if not df_storico.empty and 'ID_Pacco' in df_storico.columns:
                    storico_pacco = df_storico[df_storico['ID_Pacco'].astype(str) == str(pacco.get('ID_Pacco', ''))]
                    
                    if not storico_pacco.empty:
                        movimenti_trovati = True
                        storico_pacco = storico_pacco.iloc[::-1]
                        
                        for idx_st, mov in storico_pacco.iterrows():
                            stato_mov_puro = str(mov.get('Stato Registrato', mov.get('Stato_Registrato', ''))).strip()
                            stato_mov_test = stato_mov_puro.lower()
                            data_mov = mov.get('Data Ora', mov.get('Data_Ora', 'N/D'))
                            
                            # IL BLOCCO "IN MAGAZZINO" È RIMASTO INTONSO COME DA TUA RICHIESTA
                            if "in magazzino" in stato_mov_test:
                                st.markdown("""
                                    <div style="
                                        background-color: rgba(138, 66, 166, 0.2); 
                                        padding: 15px; 
                                        border-radius: 8px; 
                                        color: #b159d4;
                                        margin-bottom: 15px;
                                    ">
                                        🏢 <b>IN MAGAZZINO</b> — Elaborato nell'hub logistico
                                    </div>
                                """, unsafe_allow_html=True)
                            elif "in carico" in stato_mov_test or "in consegna" in stato_mov_test:
                                st.info(f"🚚 **IN CONSEGNA** — Spedizione caricata sul mezzo il: `{data_mov}`")
                            elif "consegnato" in stato_mov_test:
                                st.success(f"✅ **CONSEGNATO** — Merce consegnata con successo il: `{data_mov}`")
                            elif "respinto" in stato_mov_test:
                                st.error(f"⚠️ **RESPINTO** — Spedizione rifiutata dal destinatario il: `{data_mov}`")
                            elif "assente" in stato_mov_test:
                                st.warning(f"🟡 **DESTINATARIO ASSENTE** — Tentata consegna a vuoto il: `{data_mov}`")
                            elif "eliminato" in stato_mov_test:
                                st.error(f"🗑️ **ELIMINATO** — Annullato dal magazzino il: `{data_mov}`")
                            else:
                                st.text(f"📦 **{stato_mov_puro.upper()}** — Aggiornamento registrato il: `{data_mov}`")
                            
                            st.markdown("<p style='margin: -10px 0px -5px 15px; color: gray; opacity: 0.4;'>▲</p>", unsafe_allow_html=True)
                
                # FALLBACK SE LO STORICO E' VUOTO
                if not movimenti_trovati:
                    stato_attuale = pacco.get('Stato', '')
                    ora_car = pacco.get('Navigazione / Ora_Carico', pacco.get('Ora_Carico', 'N/D'))
                    ora_esi = pacco.get('Ora_Esito', 'N/D')
                    
                    if stato_attuale == "Eliminato":
                        st.error("❌ **Eliminato** — La spedizione è stata annullata o rimossa dal magazzino.")
                    else:
                        if stato_attuale == "Consegnato":
                            st.success(f"✅ **CONSEGNATO** \n🕒 Ora: {ora_esi}")
                            st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                        elif stato_attuale == "Respinto":
                            st.error(f"⚠️ **RESPINTO DAL CLIENTE** \n🕒 Ora: {ora_esi}")
                            st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                        elif stato_attuale == "Assente":
                            st.error(f"❌ **DESTINATARIO ASSENTE** \n🕒 Ora: {ora_esi}")
                            st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                            
                        if stato_attuale in ["In Consegna", "Consegnato", "Respinto", "Assente"]:
                            st.info(f"🚚 **IN CONSEGNA** \n🕒 Ora: {ora_car}")
                            st.markdown("  ▲<br>  │", unsafe_allow_html=True)
                            
                        if stato_attuale in ["In Magazzino", "In Consegna", "Consegnato", "Respinto", "Assente"]:
                            st.warning("🏢 **IN MAGAZZINO** — Il pacco è arrivato ed è stato elaborato nell'hub logistico.")
            else:
                st.error("Errore: Spedizione non trovata o rimossa dal database.")
                st.session_state["id_pacco_selezionato"] = None

        # ==========================================
        # VISTA B: TABELLA GENERALE CON IMPAGINAZIONE
        # ==========================================
        else:
            if df_filtrato.empty:
                st.info("Nessuna spedizione trovata per il periodo selezionato.")
            else:
                st.subheader("Stato Attuale delle Spedizioni")
                totali = len(df_filtrato)
                consegnati = len(df_filtrato[df_filtrato['Stato'] == 'Consegnato'])
                in_viaggio = len(df_filtrato[df_filtrato['Stato'] == 'In Consegna'])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Spedizioni Totali", totali)
                c2.metric("✅ Consegnate", consegnati)
                c3.metric("🚚 In Consegna", in_viaggio)
                
                st.divider()
                
                st.subheader("Elenco Spedizioni")
                cerca_ddt = st.text_input(
                    "Filtra la tabella inserendo il numero di DDT o il nome del Destinatario:",
                    on_change=resetta_pagina 
                )
                
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
                    righe_per_pagina = 10
                    totale_pagine = math.ceil(len(df_visualizza) / righe_per_pagina)
                    
                    if st.session_state["pagina_corrente"] > totale_pagine:
                        st.session_state["pagina_corrente"] = 1
                        
                    inizio = (st.session_state["pagina_corrente"] - 1) * righe_per_pagina
                    fine = inizio + righe_per_pagina
                    
                    df_pagina = df_visualizza.iloc[inizio:fine]
                    
                    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 3, 2, 1.5])
                    col_h1.markdown("**Numero DDT**")
                    col_h2.markdown("**Ragione Sociale / Destinatario**")
                    col_h3.markdown("**Stato Spedizione**")
                    col_h4.markdown("**Azioni**")
                    
                    st.markdown("<hr style='margin: 4px 0px 12px 0px; border-bottom: 2px solid #4F4F4F;'>", unsafe_allow_html=True)
                    
                    for index, pacco in df_pagina.iterrows():
                        c1, c2, c3, c4 = st.columns([2, 3, 2, 1.5])
                        
                        c1.markdown(f"<p style='margin-top:8px;'>{pacco.get('DDT', 'N/D')}</p>", unsafe_allow_html=True)
                        c2.markdown(f"<p style='margin-top:8px;'>{pacco.get('Destinatario', 'N/D')}</p>", unsafe_allow_html=True)
                        c3.markdown(f"<p style='margin-top:8px;'>`{pacco.get('Stato', '')}`</p>", unsafe_allow_html=True)
                        
                        with c4:
                            if st.button("Apri ➔", key=f"btn_apri_{index}", use_container_width=True):
                                st.session_state["id_pacco_selezionato"] = pacco.get('ID_Pacco')
                                st.rerun()
                        
                        st.markdown("<hr style='margin: 6px 0px; opacity: 0.15;'>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_prev, col_page, col_next = st.columns([1, 2, 1])
                    
                    with col_prev:
                        if st.button("⬅️ Precedente", use_container_width=True, disabled=(st.session_state["pagina_corrente"] == 1)):
                            st.session_state["pagina_corrente"] -= 1
                            st.rerun()
                            
                    with col_page:
                        st.markdown(f"<p style='text-align: center; margin-top: 8px;'>Pagina <b>{st.session_state['pagina_corrente']}</b> di <b>{totale_pagine}</b></p>", unsafe_allow_html=True)
                        
                    with col_next:
                        if st.button("Successiva ➡️", use_container_width=True, disabled=(st.session_state["pagina_corrente"] == totale_pagine)):
                            st.session_state["pagina_corrente"] += 1
                            st.rerun()
