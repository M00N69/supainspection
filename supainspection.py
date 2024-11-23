from supabase import create_client, Client
import streamlit as st

# Configuration Supabase
SUPABASE_URL = "https://your-supabase-url.supabase.co"
SUPABASE_KEY = "your-supabase-key"

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
    # Rechercher l'utilisateur
    response = supabase.table("users").select("*").eq("email", email).execute()
    user = response.data

    if user:
        st.session_state["user_id"] = user[0]["id"]
        st.success(f"Bienvenue {email} !")
    else:
        st.error("Utilisateur non trouvé.")

if "user_id" in st.session_state:
    # Afficher les checklists disponibles
    checklists = ["CHECKPVNA", "CHECKHYGIENE", "CHECKSECURITE"]
    selected_checklist = st.selectbox("Choisissez un type d'inspection", checklists)

    if st.button("Démarrer l'inspection"):
        # Récupérer les checkpoints associés
        response = supabase.table("checkpoints").select("*").eq("name", selected_checklist).execute()
        checkpoints = response.data

        if checkpoints:
            # Initialiser l'inspection
            inspection = supabase.table("inspections").insert({
                "user_id": st.session_state["user_id"],
                "results": [{"checkpoint_id": cp["id"], "status": "Non évalué"} for cp in checkpoints],
                "status": "in_progress",
                "progress": 0
            }).execute()

            if inspection.status_code == 201:
                st.success("Inspection démarrée avec succès !")
                st.session_state["inspection_id"] = inspection.data[0]["id"]
        else:
            st.error("Aucun checkpoint trouvé pour cette checklist.")

if "inspection_id" in st.session_state:
    # Récupérer les résultats actuels de l'inspection
    response = supabase.table("inspections").select("*").eq("id", st.session_state["inspection_id"]).execute()
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

if st.button("Enregistrer les résultats"):
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
    }).eq("id", st.session_state["inspection_id"]).execute()

    if response.status_code == 204:
        st.success("Résultats enregistrés et progression mise à jour !")
    else:
        st.error("Erreur lors de la mise à jour des résultats.")

