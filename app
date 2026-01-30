import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="VeloShare - Arts et Métiers", page_icon="🚲")

# --- CONNEXION GOOGLE SHEETS ---
# On utilise le cache (ttl=0) pour être sûr d'avoir les données fraîches à chaque action
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        # On lit la feuille demandée
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except Exception:
        # Si la feuille est vide ou erreur, on renvoie un DF vide avec les bonnes colonnes
        if worksheet_name == "users":
            return pd.DataFrame(columns=["username", "password"])
        else:
            return pd.DataFrame(columns=["id", "bike_id", "username", "start_dt", "end_dt"])

def update_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)

# --- FONCTIONS LOGIQUES (ADAPTÉES PANDAS) ---

def check_overlap(bike_id, new_start, new_end):
    df = get_data("reservations")
    if df.empty:
        return False
    
    # Filtrer pour ce vélo uniquement
    bike_res = df[df['bike_id'] == bike_id].copy()
    if bike_res.empty:
        return False

    # Conversion des colonnes en datetime
    bike_res['start_dt'] = pd.to_datetime(bike_res['start_dt'])
    bike_res['end_dt'] = pd.to_datetime(bike_res['end_dt'])

    # Logique de chevauchement avec Pandas
    # (StartA < EndB) et (EndA > StartB)
    overlap = bike_res[
        (new_start < bike_res['end_dt']) & 
        (new_end > bike_res['start_dt'])
    ]
    
    return not overlap.empty

def make_reservation(bike_id, username, start_dt, end_dt):
    if check_overlap(bike_id, start_dt, end_dt):
        return False
    
    df = get_data("reservations")
    
    # Création d'un ID unique simple (timestamp)
    new_id = int(datetime.now().timestamp())
    
    new_row = pd.DataFrame([{
        "id": new_id,
        "bike_id": bike_id,
        "username": username,
        "start_dt": start_dt.isoformat(),
        "end_dt": end_dt.isoformat()
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    update_data(updated_df, "reservations")
    return True

def cancel_reservation(reservation_id):
    df = get_data("reservations")
    # On garde tout SAUF la ligne avec cet ID
    updated_df = df[df['id'] != reservation_id]
    update_data(updated_df, "reservations")

def add_user(username, password):
    df = get_data("users")
    
    # Vérifier si l'utilisateur existe déjà
    if not df.empty and username in df['username'].values:
        return False
        
    new_row = pd.DataFrame([{"username": username, "password": password}])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    update_data(updated_df, "users")
    return True

def login_user(username, password):
    df = get_data("users")
    if df.empty:
        return False
    # Vérification stricte
    user_row = df[(df['username'] == username) & (df['password'] == password)]
    return not user_row.empty

# --- INTERFACE ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

with st.sidebar:
    logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Logo_Arts_et_M%C3%A9tiers_ParisTech.png/600px-Logo_Arts_et_M%C3%A9tiers_ParisTech.png"
    st.markdown(f"""<div style="background-color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"><img src="{logo_url}" width="120" style="display: block; margin-left: auto; margin-right: auto;"></div>""", unsafe_allow_html=True)
    
    st.markdown("### Espace Membre")
    if not st.session_state['logged_in']:
        choice = st.radio("Option", ["Connexion", "Inscription"])
        user = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type='password')
        
        if choice == "Inscription":
            if st.button("Créer compte"):
                if user and password:
                    if add_user(user, password):
                        st.success("Compte créé ! Connectez-vous.")
                    else:
                        st.error("Identifiant pris.")
                else:
                    st.warning("Remplissez tout.")
        else:
            if st.button("Se connecter"):
                if login_user(user, password):
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.rerun()
                else:
                    st.error("Erreur d'identifiants.")
    else:
        st.write(f"Bonjour, **{st.session_state['user']}** 👋")
        if st.button("Se déconnecter"):
            st.session_state['logged_in'] = False
            st.rerun()

# --- CONTENU PRINCIPAL ---
st.title("🚲 VeloShare - Arts et Métiers")
st.markdown("Réservez un vélo gratuitement pour vos déplacements.")

if st.session_state['logged_in']:
    
    # 1. FORMULAIRE
    st.subheader("📅 Nouvelle Réservation")
    bikes = ["VTT Rockrider", "Vélo de ville Peugeot", "Vélo Électrique", "Tandem"]
    
    col1, col2 = st.columns(2)
    with col1:
        bike_choice = st.selectbox("Choisir un vélo", bikes)
        date_choice = st.date_input("Date de l'emprunt", value=datetime.today())
    with col2:
        start_time = st.time_input("Heure de début", value=time(9, 0))
        duration = st.number_input("Durée (heures)", min_value=0.5, max_value=24.0, step=0.5, value=1.0)

    start_dt = datetime.combine(date_choice, start_time)
    end_dt = start_dt + timedelta(hours=duration)
    st.info(f"Créneau demandé : **{start_dt.strftime('%H:%M')}** à **{end_dt.strftime('%H:%M')}** ({date_choice.strftime('%d/%m')})")

    if st.button("Valider la réservation"):
        if end_dt <= start_dt:
            st.error("Erreur d'heure.")
        else:
            if make_reservation(bike_choice, st.session_state['user'], start_dt, end_dt):
                st.success(f"✅ Réservé ! Vous avez le {bike_choice}.")
                st.rerun()
            else:
                st.error("⚠️ Ce vélo est déjà pris sur ce créneau.")

    st.divider()

    # 2. MES RÉSERVATIONS
    st.markdown("### 🎫 Mes réservations actives")
    LOCK_CODES = {"VTT Rockrider": "1234", "Vélo de ville Peugeot": "5678", "Vélo Électrique": "9012", "Tandem": "0000"}
    
    # Lecture depuis Google Sheets
    df_res = get_data("reservations")
    
    if not df_res.empty:
        # Filtrer pour l'user actuel
        my_res = df_res[df_res['username'] == st.session_state['user']].copy()
        
        # Trier par date
        my_res['start_dt'] = pd.to_datetime(my_res['start_dt'])
        my_res = my_res.sort_values(by='start_dt', ascending=False)
        
        if not my_res.empty:
            for index, row in my_res.iterrows():
                res_id = row['id']
                bike_name = row['bike_id']
                s_dt = row['start_dt'] # C'est déjà un datetime grâce à la conversion
                e_dt = pd.to_datetime(row['end_dt'])
                code = LOCK_CODES.get(bike_name, "????")

                with st.container():
                    col_text, col_act = st.columns([4, 1])
                    with col_text:
                        st.info(f"🚲 **{bike_name}** | 🔒 Code : **{code}** | 📅 Le {s_dt.strftime('%d/%m/%Y')} de {s_dt.strftime('%H:%M')} à {e_dt.strftime('%H:%M')}")
                    with col_act:
                        if st.button("Annuler", key=f"del_{res_id}", type="primary"):
                            cancel_reservation(res_id)
                            st.success("Annulé !")
                            st.rerun()
        else:
            st.info("Aucune réservation.")
    else:
        st.info("Aucune réservation.")

    # 3. PLANNING GÉNÉRAL
    st.subheader("🗓️ Planning global")
    if not df_res.empty:
        # Copie pour affichage propre
        display_df = df_res.copy()
        display_df['start_dt'] = pd.to_datetime(display_df['start_dt'])
        display_df['end_dt'] = pd.to_datetime(display_df['end_dt'])
        
        # Tri et mise en forme
        display_df = display_df.sort_values(by='start_dt', ascending=False)
        
        clean_data = []
        for index, row in display_df.iterrows():
             clean_data.append({
                "Vélo": row['bike_id'],
                "Début": row['start_dt'].strftime('%d/%m %H:%M'),
                "Fin": row['end_dt'].strftime('%d/%m %H:%M'),
                "Réservé par": row['username']
            })
        st.dataframe(pd.DataFrame(clean_data), use_container_width=True)
    else:
        st.write("Le planning est vide.")

else:
    st.warning("🔒 Veuillez vous identifier.")

# --- FOOTER ---
st.markdown("<br><br><br>---", unsafe_allow_html=True)
col_f1, col_f2 = st.columns([1.5, 4]) 
with col_f1:
    st.markdown(f"""<div style="background-color: white; padding: 10px; border-radius: 8px; display: flex; justify-content: center; align-items: center;"><img src="{logo_url}" width="80"></div>""", unsafe_allow_html=True)
with col_f2:
    st.markdown("""<div style="padding-top: 10px;"><strong>VeloShare - Arts et Métiers</strong><br>Initiative mobilité douce.<br><em style="font-size: 0.9em; color: gray;">Développé avec ❤️ par [Ton Prénom]</em></div>""", unsafe_allow_html=True)
