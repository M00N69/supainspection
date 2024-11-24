from supabase import create_client, Client
import streamlit as st
import mimetypes

# Configuration Supabase
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]

# Création du client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Streamlit Configuration
st.title("Application d'Inspection")

# Fonction pour uploader une photo dans un bucket Supabase
def upload_photo(file, inspection_id):
    try:
        # Définir le chemin du fichier dans le bucket
        bucket_path = f"inspections/{inspection_id}/{file.name}"
        mime_type, _ = mimetypes.guess_type(file.name)

        # Téléversement dans le bucket Supabase
        response = supabase.storage.from_("photos").upload(
            bucket_path,
            file,
            {"content-type": mime_type}
        )

        if response.get("error"):
            raise Exception(response["error"]["message"])

        # Obtenir l'URL publique
        public_url = supabase.storage.from_("photos").get_public_url(bucket_path)["publicUrl"]
        return public_url
    except Exception as e:
        st.error(f"Erreur lors de l'upload : {e}")
        return None

# Connexion utilisateur
with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    login_button = st.form_submit_button("Se connecter")

if login_button:
    # Nettoyer et vérifier l'email
    email = email.strip()
    if not email:
        st.error("Veuillez entrer un email valide.")
    else:
        try:
            # Rechercher l'utilisateur
            response = supabase.table("users").select("*").filter("email", "eq", email).execute()
            user = response.data

            if user:
                st.session_state["user_id"] = user[0]["id"]
                st.success(f"Bienvenue {email} !")
            else:
                st.error("Utilisateur non trouvé.")
        except Exception as e:
            st.error(f"Erreur lors de la recherche de l'utilisateur : {e}")

# Inspection Workflow
if "user_id" in st.session_state:
    # Afficher les checklists disponibles
    checklists = ["CHECKPVNA", "CHECKHYGIENE", "CHECKSECURITE"]
    selected_checklist = st.selectbox("Choisissez un type d'inspection", checklists)

    if st.button("Démarrer l'inspection"):
        try:
            # Récupérer les checkpoints associés
            response = supabase.table("checkpoints").select("*").filter("name", "ilike", selected_checklist).execute()

            if not response.data:
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

                if not inspection.data:
                    st.error("Erreur lors de l'initialisation de l'inspection.")
                else:
                    st.success("Inspection démarrée avec succès !")
                    st.session_state["inspection_id"] = inspection.data[0]["id"]
        except Exception as e:
            st.error(f"Erreur lors de la récupération des checkpoints : {e}")

if "inspection_id" in st.session_state:
    try:
        # Récupérer les résultats de l'inspection actuelle
        response = supabase.table("inspections").select("*").filter("id", "eq", st.session_state["inspection_id"]).execute()

        if not response.data:
            st.error("Erreur lors de la récupération des résultats de l'inspection.")
        else:
            inspection = response.data[0]
            results = inspection.get("results", [])

            updated_results = []

            # Grouper les checkpoints par zone et permettre l'évaluation
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

                    # Gérer l'upload des photos
                    photo_urls = []
                    if photos:
                        for photo in photos:
                            photo_url = upload_photo(photo, st.session_state["inspection_id"])
                            if photo_url:
                                photo_urls.append(photo_url)

                    updated_results.append({
                        "checkpoint_id": cp["checkpoint_id"],
                        "status": status,
                        "comments": comment,
                        "photos": photo_urls  # Stocker les URLs des photos
                    })

            # Enregistrer les résultats
            if st.button("Enregistrer les résultats"):
                try:
                    # Calculer la progression
                    progress = len([r for r in updated_results if r["status"] != "Non évalué"]) / len(updated_results) * 100

                    # Mettre à jour l'inspection
                    response = supabase.table("inspections").update({
                        "results": updated_results,
                        "progress": progress
                    }).filter("id", "eq", st.session_state["inspection_id"]).execute()

                    if not response.data:
                        st.error("Erreur lors de la mise à jour des résultats.")
                    else:
                        st.success("Résultats enregistrés et progression mise à jour !")
                except Exception as e:
                    st.error(f"Erreur lors de l'enregistrement des résultats : {e}")
    except Exception as e:
        st.error(f"Erreur lors de la récupération des résultats de l'inspection : {e}")
