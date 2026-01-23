import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import base64
import time

# Configuration de la page
st.set_page_config(page_title="Convertisseur PNG vers ImageBB", layout="centered")

st.title("⚡ Convertisseur & Hébergeur d'Images")
st.markdown("Convertit les liens (JPG, WebP, etc.) en **PNG** et génère des liens **ImageBB**.")

# TA CLÉ API EST DÉJÀ CONFIGURÉE ICI
DEFAULT_API_KEY = "2caafdd6dc7859e3f4b10419752b96a0"

# On met la clé par défaut dans le champ, mais tu peux la modifier si besoin
api_key = st.text_input("Clé API ImageBB", value=DEFAULT_API_KEY, type="password")

uploaded_file = st.file_uploader("Chargez votre fichier Excel (.xlsx)", type=["xlsx"])

def upload_to_imagebb(image_bytes, api_key):
    """Envoie l'image binaire convertie vers ImageBB"""
    url = "https://api.imgbb.com/1/upload"
    
    # Encodage en Base64 requis par l'API ImageBB
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "key": api_key,
        "image": b64_image,
    }
    
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        # Retourne le lien direct (url)
        return data['data']['url'] 
    except Exception as e:
        return f"Erreur: {str(e)}"

if uploaded_file and api_key:
    # Lecture du fichier
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")
        st.stop()
    
    # Vérification de la colonne
    if "image" not in df.columns:
        st.error("🚨 Erreur : La colonne 'image' est introuvable dans le fichier Excel.")
    else:
        st.info(f"{len(df)} liens trouvés. Prêt à convertir.")
        
        if st.button("Lancer la conversion"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Liste pour stocker les résultats dans l'ordre
            final_links = []
            
            for index, row in df.iterrows():
                url = row['image']
                status_text.text(f"Traitement {index+1}/{len(df)}...")
                
                try:
                    # 1. Téléchargement de l'image source
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    
                    # 2. Conversion en PNG
                    img = Image.open(io.BytesIO(resp.content))
                    
                    # On sauvegarde l'image convertie dans une mémoire tampon
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    img_png_bytes = buffer.getvalue()
                    
                    # 3. Envoi vers ImageBB
                    link = upload_to_imagebb(img_png_bytes, api_key)
                    final_links.append(link)
                    
                except Exception as e:
                    final_links.append(f"Erreur : {e}")
                
                # Mise à jour de la barre de progression
                progress_bar.progress((index + 1) / len(df))
                
                # Petite pause pour éviter de bloquer l'API
                time.sleep(0.3)

            # Fin du traitement
            status_text.success("✅ Traitement terminé !")
            progress_bar.empty()
            
            # Ajout de la nouvelle colonne
            df['image_png_link'] = final_links
            
            st.write("Aperçu du résultat :")
            st.dataframe(df.head())
            
            # Préparation du téléchargement
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Télécharger le fichier Excel final",
                data=output.getvalue(),
                file_name="resultat_links_png.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
