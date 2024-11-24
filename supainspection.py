from supabase import create_client, Client
import streamlit as st

# Configuration Supabase
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]

# Création du client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Streamlit
st.title("Application d'Inspection")

# Connexion utilisateur
with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    login_button = st.form_submit_button("Se connecter")

if login_button:
    # Nettoyer l'email
    email = email.strip()

    # Vérifier que l'email est valide
    if not email:
        st.error("Veuillez entrer un email valide.")
    else:
        try:
            # Rechercher l'utilisateur avec une recherche insensible à la casse
            response = supabase.table("users").select("*").filter("email", "ilike", email).execute()

            # Vérifier les données renvoyées
            if not response.data or len(response.data) == 0:
                st.error("Utilisateur non trouvé.")
            else:
                user = response.data
                st.session_state["user_id"] = user[0]["id"]
                st.success(f"Bienvenue {email} !")
        except Exception as e:
            st.error(f"Erreur lors de la recherche de l'utilisateur : {e}")

if "user_id" in st.session_state:
    # Afficher les checklists disponibles
    checklists = ["CHECKPVNA", "CHECKHYGIENE", "CHECKSECURITE"]
    selected_checklist = st.selectbox("Choisissez un type d'inspection", checklists)

    if st.button("Démarrer l'inspection"):
        try:
            # Nettoyer la sélection pour éviter les problèmes d'espaces
            selected_checklist = selected_checklist.strip()

            # Récupérer les checkpoints associés à la checklist sélectionnée
            response = supabase.table("checkpoints").select("*").filter("name", "eq", selected_checklist).execute()

            if response.error:
                st.error(f"Erreur lors de la récupération des checkpoints : {response.error['message']}")
            elif not response.data or len(response.data) == 0:
                st.error("Aucun checkpoint trouvé pour cette checklist.")
            else:
                checkpoints = response.data

                # Initialiser l'inspection
                inspection = supabase.table("inspections").insert({
                    "user_id": st.session_state["user_id"],
                    "results": [{"checkpoint_id": cp["id"], "status": "Non évalué"} for cp in checkpoints],
                    "status": "in_progress",
                    "progress": 0
                }).execute()

                if inspection.error:
                    st.error(f"Erreur lors de l'initialisation de l'inspection : {inspection.error['message']}")
                else:
                    st.success("Inspection démarrée avec succès !")
                    st.session_state["inspection_id"] = inspection.data[0]["id"]
        except Exception as e:
            st.error(f"Erreur lors de la récupération des checkpoints : {e}")

if "inspection_id" in st.session_state:
    try:
        # Récupérer les résultats actuels de l'inspection
        response = supabase.table("inspections").select("*").filter("id", "eq", st.session_state["inspection_id"]).execute()

        if response.error:
            st.error(f"Erreur lors de la récupération des résultats de l'inspection : {response.error['message']}")
        elif not response.data or len(response.data) == 0:
            st.error("Erreur lors de la récupération des résultats de l'inspection.")
        else:
            inspection = response.data[0]
            results = inspection["results"]

            # Grouper les checkpoints par zone
            for zone in set(cp["zone"] for cp in results):
                st.header(f"Zone : {zone}")
                for cp in [cp for cp in results if cp["zone"] == zone]:
                    st.subheader(cp["points"])
                    status = st.radio(
                        f"Évaluation : {cp['points']}",
                        ["Non évalué", "Conforme", "Non conforme"],
                        key=f"status_{cp['checkpoint_id']}"
                    )
                    comment = st.text_area(
                        f"Commentaires ({cp['points']})",
                        key=f"comment_{cp['checkpoint_id']}"
                    )
                    photos = st.file_uploader(
                        f"Ajouter des photos ({cp['points']})", accept_multiple_files=True, key=f"photos_{cp['checkpoint_id']}"
                    )
    except Exception as e:
        st.error(f"Erreur lors de la récupération des résultats de l'inspection : {e}")

if st.button("Enregistrer les résultats"):
    try:
        updated_results = []
        for cp in results:
            checkpoint_id = cp["checkpoint_id"]
            updated_results.append({
                "checkpoint_id": checkpoint_id,
                "status": st.session_state.get(f"status_{checkpoint_id}", "Non évalué"),
                "comments": st.session_state.get(f"comment_{checkpoint_id}", ""),
                "photos": []  # Ajouter les URLs des photos après téléversement
            })

        # Calculer la progression
        progress = len([r for r in updated_results if r["status"] != "Non évalué"]) / len(updated_results) * 100

        # Mettre à jour l'inspection
        response = supabase.table("inspections").update({
            "results": updated_results,
            "progress": progress
        }).filter("id", "eq", st.session_state["inspection_id"]).execute()

        if response.error:
            st.error(f"Erreur lors de la mise à jour des résultats : {response.error['message']}")
        else:
            st.success("Résultats enregistrés et progression mise à jour !")
    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement des résultats : {e}")
