import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import base64
import time

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Yassir - Convertisseur d'Images",
    page_icon="🟣",
    layout="centered"
)

# --- 2. STYLE CSS PERSONNALISÉ (Thème Yassir) ---
st.markdown("""
    <style>
    /* Couleur de fond générale (optionnel, ici blanc pour la propreté) */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Titres en Violet Yassir */
    h1, h2, h3 {
        color: #4A148C !important;
    }
    
    /* Style du Bouton "Lancer" */
    div.stButton > button {
        background-color: #4A148C; /* Violet foncé */
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #7c43bd; /* Violet plus clair au survol */
        color: white;
    }
    
    /* Style du pied de page (Signature) */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #4A148C;
        text-align: center;
        padding: 15px;
        font-size: 14px;
        border-top: 3px solid #4A148C;
        z-index: 100;
    }
    .footer a {
        color: #4A148C;
        font-weight: bold;
        text-decoration: none;
    }
    
    /* Espacement pour ne pas cacher le contenu derrière le footer */
    .block-container {
        padding-bottom: 100px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. EN-TÊTE AVEC LOGO ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    # URL publique du logo Yassir (ou mettre un fichier local "logo.png")
    try:
        st.image("https://upload.wikimedia.org/wikipedia/commons/2/23/Yassir_Logo.svg", width=200)
    except:
        st.title("YASSIR") # Fallback si l'image ne charge pas

st.markdown("<h3 style='text-align: center;'>Convertisseur d'Images (URL ➡️ PNG)</h3>", unsafe_allow_html=True)

# --- 4. LOGIQUE ET API ---

# Ta clé API (Hardcoded)
API_KEY = "2caafdd6dc7859e3f4b10419752b96a0"

def upload_to_imagebb(image_bytes, api_key):
    """Envoie l'image vers ImageBB et retourne le lien"""
    url = "https://api.imgbb.com/1/upload"
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    payload = {"key": api_key, "image": b64_image}
    
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        return response.json()['data']['url']
    except Exception as e:
        return f"Erreur: {str(e)}"

# Upload du fichier
uploaded_file = st.file_uploader("📂 Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except:
        st.error("Format de fichier invalide.")
        st.stop()
        
    if "image" not in df.columns:
        st.error("🚨 La colonne 'image' est manquante.")
    else:
        st.info(f"📊 {len(df)} images détectées. Prêt pour la conversion.")
        
        if st.button("🚀 Lancer la conversion"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            new_links = []
            
            for index, row in df.iterrows():
                url = row['image']
                status_text.text(f"Traitement de la ligne {index+1}...")
                
                try:
                    # Téléchargement & Conversion
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content))
                    
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    
                    # Upload
                    link = upload_to_imagebb(buffer.getvalue(), API_KEY)
                    new_links.append(link)
                    
                except Exception as e:
                    new_links.append(f"Erreur")
                
                progress_bar.progress((index + 1) / len(df))
                time.sleep(0.3) 
            
            # --- REMPLACEMENT DE LA COLONNE ---
            df['image'] = new_links
            
            status_text.success("✅ Conversion terminée avec succès !")
            progress_bar.empty()
            
            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Télécharger le fichier final",
                data=output.getvalue(),
                file_name="resultat_yassir_png.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- 5. SIGNATURE (FOOTER) ---
st.markdown("""
    <div class="footer">
        <p>Developed by <b>Bounoir Saif Eddine</b><br>
        Contact: <a href="mailto:saifeddine.bounoir@yassir.com">saifeddine.bounoir@yassir.com</a></p>
    </div>
""", unsafe_allow_html=True)
