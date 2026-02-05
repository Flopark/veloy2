# -*- coding: utf-8 -*-
"""
Created on Thu Dec 25 00:04:15 2025

@author: march
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Veloy - Gadz", page_icon="🚲")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    # Fonction pour récupérer les données proprement
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except Exception:
        # Si la feuille est vide ou n'existe pas encore, on renvoie une structure vide
        if worksheet_name == "users":
            return pd.DataFrame(columns=["username", "password"])
        else:
            return pd.DataFrame(columns=["id", "bike_id", "username", "start_dt", "end_dt"])

def update_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)

# --- FONCTIONS LOGIQUES ---

def check_overlap(bike_id, new_start, new_end):
    df = get_data("reservations")
    if df.empty:
        return False
    
    # On filtre sur le vélo concerné
    bike_res = df[df['bike_id'] == bike_id].copy()
    if bike_res.empty:
        return False

    # Conversion des colonnes en datetime pour la comparaison mathématique
    bike_res['start_dt'] = pd.to_datetime(bike_res['start_dt'])
    bike_res['end_dt'] = pd.to_datetime(bike_res['end_dt'])

    # Logique de chevauchement : (StartA < EndB) et (EndA > StartB)
    overlap = bike_res[
        (new_start < bike_res['end_dt']) & 
        (new_end > bike_res['start_dt'])
    ]
    
    return not overlap.empty

def make_reservation(bike_id, username, start_dt, end_dt):
    if check_overlap(bike_id, start_dt, end_dt):
        return False
    
    df = get_data("reservations")
    
    # Création d'un ID unique basé sur le temps
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
    # On garde tout ce qui n'est PAS l'ID à supprimer
    updated_df = df[df['id'] != reservation_id]
    update_data(updated_df, "reservations")

def clean_old_reservations():
    df = get_data("reservations")
    
    if not df.empty:
        # 1. Conversion propre des dates
        df['start_dt'] = pd.to_datetime(df['start_dt'])
        df['end_dt'] = pd.to_datetime(df['end_dt'])
        
        # 2. GESTION DU DÉCALAGE HORAIRE (UTC+1 pour la France)
        # On ajoute 1 heure à l'heure du serveur pour qu'il soit synchro avec nous
        now_france = datetime.now() + timedelta(hours=1)
        
        # 3. Filtrage
        future_df = df[df['end_dt'] > now_france].copy()
        
        # 4. Mise à jour si nécessaire
        if len(future_df) < len(df):
            future_df['start_dt'] = future_df['start_dt'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            future_df['end_dt'] = future_df['end_dt'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            
            update_data(future_df, "reservations")
            # Petit hack : on recharge la page pour que l'utilisateur voie la modif tout de suite
            st.rerun()


def add_user(username, password):
    df = get_data("users")
    
    # Vérification doublon
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

# Sidebar : Authentification
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

with st.sidebar:
    st.markdown("### Espace Membre")
    if not st.session_state['logged_in']:
        choice = st.radio("Option", ["Connexion", "Inscription"])
        user = st.text_input("Identifiant (bucque Li prom's)")
        password = st.text_input("Mot de passe (lettre uniquement)", type='password')
        
        if choice == "Inscription":
            if st.button("Créer compte"):
                if user and password:
                    if add_user(user, password):
                        st.success("Compte créé ! Connectez-vous.")
                    else:
                        st.error("Identifiant pris.")
                else:
                    st.warning("Faut remplir les champs !")
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
clean_old_reservations()
st.title("🚲 Veloy - Gadz")
st.markdown("Faites chauffer vos giboles pour préparer les GUAI.")
st.markdown("⚠️ Pensez bien à ranger le vélo dans l'espace reservé aux vélos de prom's ⚠️")


if st.session_state['logged_in']:
    
    # 1. FORMULAIRE DE RÉSERVATION
    st.subheader("📅 Nouvelle Réservation")
    
    # Liste des vélos disponibles
    bikes = ["Le grand", "Le tranquille", "L'abominable","Le Violet","Le vélo de (Lab)t ou(r)° (venir en mp pour l'utiliser)"]
    
    # Dictionnaire pour lier chaque vélo à sa photo
    # ATTENTION : Vérifie que les noms des fichiers correspondent EXACTEMENT à ce que tu as mis dans le dossier 'asset'
    images_velos = {
        "Le grand": "vel2.jpeg",
        "Le tranquille": "vel3.jpeg",
        "L'abominable": "vel4.jpeg",
        "Le Violet" : "Le_Violet_(j'ai plus d'inspi).jpg",
        "Le vélo de (Lab)t ou(r)° (venir en mp pour l'utiliser)": "velo_de_Balou.jpg",
    }

    col1, col2 = st.columns(2)
    
    with col1:
        bike_choice = st.selectbox("Choisir un vélo", bikes)
        
        # --- C'est ici que la magie opère ---
        # On affiche l'image correspondant au choix
        # On gère le cas où l'image n'existerait pas pour éviter que l'app plante
        try:
            image_path = images_velos.get(bike_choice)
            st.image(image_path, width=300, caption=f"📸 {bike_choice}")
        except:
            st.warning(f"Photo du {bike_choice} introuvable (vérifier le dossier asset)")
        # -------------------------------------

        
    
    with col2:
        start_time = st.time_input("Heure de début", value=time(9, 0))
        duration = st.number_input("Durée (heures)", min_value=0.5, max_value=24.0, step=0.5, value=1.0)
        date_choice = st.date_input("Date de l'emprunt", value=datetime.today())

    # Calcul des dates
    start_dt = datetime.combine(date_choice, start_time)
    end_dt = start_dt + timedelta(hours=duration)
    
    # ... Le reste du code (bouton valider) reste identique ...
    st.info(f"Créneau demandé : **{start_dt.strftime('%H:%M')}** à **{end_dt.strftime('%H:%M')}** ({date_choice.strftime('%d/%m')})")

    if st.button("Valider la réservation"):
        # ... (Garde ton code de validation ici) ...
        if end_dt <= start_dt:
            st.error("L'heure de fin doit être après l'heure de début !")
        else:
            success = make_reservation(bike_choice, st.session_state['user'], start_dt, end_dt)
            if success:
                st.success(f"✅ Réservé ! Vous avez le {bike_choice}.")
                st.rerun()
            else:
                st.error("⚠️ Ce vélo est déjà pris sur ce créneau (tu sais pas lire !?).")

    st.divider()

    # 2. MES RÉSERVATIONS
    st.markdown("### 🎫 Mes réservations")
    LOCK_CODES = {
        "Le grand": "0225",
        "Le tranquille": "0225",
        "L'abominable": "0225",
        "Le Violet" : "0225",
        "Le vélo de (Lab)t ou(r)° (venir en mp pour l'utiliser)": "0225",
    }
    
    # Récupération depuis GSheets
    df_res = get_data("reservations")
    
    user_has_res = False
    
    if not df_res.empty:
        # Filtrer pour l'utilisateur connecté
        my_res = df_res[df_res['username'] == st.session_state['user']].copy()
        
        if not my_res.empty:
            user_has_res = True
            # Tri par date décroissante
            my_res['start_dt'] = pd.to_datetime(my_res['start_dt'])
            my_res = my_res.sort_values(by='start_dt', ascending=False)
            
            for index, row in my_res.iterrows():
                res_id = row['id']
                bike_name = row['bike_id']
                # Les dates sont déjà en datetime grâce à pd.to_datetime au dessus ou lors du read
                s_dt = row['start_dt']
                e_dt = pd.to_datetime(row['end_dt'])
                
                # Récupération du code (ou "????" si le vélo n'est pas dans la liste)
                code = LOCK_CODES.get(bike_name, "????")

                # On affiche une carte pour chaque réservation
                with st.container():
                    col_text, col_act = st.columns([4, 1])
                    with col_text:
                        # LE FORMAT DEMANDÉ
                        st.info(f"🚲 **{bike_name}** | 🔒 Code du cadenas : **{code}** | 📅 Le {s_dt.strftime('%d/%m/%Y')} de {s_dt.strftime('%H:%M')} à {e_dt.strftime('%H:%M')}")
                    with col_act:
                        if st.button("Annuler", key=f"del_{res_id}", type="primary"):
                            cancel_reservation(res_id)
                            st.success("Réservation annulée !")
                            st.rerun()
    
    if not user_has_res:
        st.info("Bah alors ça RIDE pas 🤙")

    # 3. PLANNING GÉNÉRAL
    st.subheader("🗓️ Planning global des réservations")
    
    # On recharge les données pour être sûr d'avoir tout le monde
    df_all = get_data("reservations")
    
    if not df_all.empty:
        # Préparation des données pour l'affichage
        display_df = df_all.copy()
        display_df['start_dt'] = pd.to_datetime(display_df['start_dt'])
        display_df['end_dt'] = pd.to_datetime(display_df['end_dt'])
        
        # Tri
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
    st.warning("🔒 OH FADA IDENTIFIE TOI D'ABORD.")

# --- PIED DE PAGE ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown("---")
col_f1, col_f2 = st.columns([1.5, 4]) 

with col_f1:
    # Logo Arts et Métiers (Chemin local tel que fourni)
    # Note : Sur le Cloud, assure-toi que le dossier 'asset' et l'image sont bien uploadés !
    st.image("Amtradszaloeil-modified.png", width=80)

with col_f2:
    st.markdown("""
    **Veloy - Gadz** Une initiative lars tradz pour évacuer les bières de vos coin².  
    *Développé avec ❤️ par K'sséne 148Li224 et Seratr1 71Li225*

    """)


























