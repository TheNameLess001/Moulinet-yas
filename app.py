import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import os
import uuid

# Configuration
st.set_page_config(page_title="Générateur de Liens PNG", layout="wide")

# Création du dossier static s'il n'existe pas
STATIC_FOLDER = "static"
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

st.title("🔗 Convertisseur URL ➡️ Liens PNG hébergés")

st.info("""
**Note importante :** Pour obtenir des liens, ce script sauvegarde les images sur ce serveur.
Vous devez définir l'URL de base (votre domaine) pour générer les liens corrects.
""")

# Input : L'URL de votre serveur (ex: http://localhost:8501 ou http://mon-serveur.com)
base_url = st.text_input("Entrez l'URL de base de votre application", value="http://localhost:8501")

# Upload Excel
uploaded_file = st.file_uploader("Choisissez votre fichier Excel (.xlsx)", type=["xlsx"])

if uploaded_file and base_url:
    df = pd.read_excel(uploaded_file)
    
    if "image" not in df.columns:
        st.error("La colonne 'image' est manquante.")
    else:
        if st.button("Convertir et Générer les Liens"):
            
            # Barre de progression
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            new_links = []
            
            for index, row in df.iterrows():
                url = row['image']
                try:
                    status_text.text(f"Traitement : {url}")
                    
                    # 1. Téléchargement
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    # 2. Conversion
                    img = Image.open(io.BytesIO(response.content))
                    
                    # Générer un nom unique pour éviter les conflits, tout en gardant l'extension PNG
                    # On peut aussi utiliser f"image_{index}.png" si on veut garder l'ordre strict simple
                    filename = f"image_{index + 1}_{uuid.uuid4().hex[:8]}.png"
                    save_path = os.path.join(STATIC_FOLDER, filename)
                    
                    # Sauvegarde sur le disque du serveur
                    img.save(save_path, format='PNG')
                    
                    # 3. Création du nouveau lien
                    # Streamlit sert automatiquement les fichiers du dossier "static" via l'url /app/static/ ou /static/
                    # Note: L'URL exacte dépend de la config Streamlit, par défaut c'est souvent à la racine si configuré
                    full_link = f"{base_url}/app/static/{filename}"
                    new_links.append(full_link)
                    
                except Exception as e:
                    new_links.append(f"Erreur: {e}")
                
                progress_bar.progress((index + 1) / len(df))
            
            # Ajouter la colonne au DataFrame
            df['image_png_link'] = new_links
            
            st.success("Conversion terminée ! Les images sont hébergées sur ce serveur.")
            
            # Afficher un aperçu
            st.dataframe(df[['image', 'image_png_link']].head())
            
            # Téléchargement du NOUVEL Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label="📥 Télécharger le fichier Excel avec les nouveaux liens",
                data=output.getvalue(),
                file_name="resultat_liens_png.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
