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
    .stApp { background-color: #ffffff; }
    h1, h2, h3 { color: #4A148C !important; }
    div.stButton > button {
        background-color: #4A148C;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover { background-color: #7c43bd; color: white; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #f8f9fa; color: #4A148C;
        text-align: center; padding: 15px; font-size: 14px;
        border-top: 3px solid #4A148C; z-index: 100;
    }
    .footer a { color: #4A148C; font-weight: bold; text-decoration: none; }
    .block-container { padding-bottom: 100px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EN-TÊTE ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    try:
        st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4umnB7rjE_AoR_VtRqiIIk-_8Dkqt771lZQ&s", width=200)
    except:
        st.title("YASSIR")

st.markdown("<h3 style='text-align: center;'>Convertisseur d'Images (Multi-Format)</h3>", unsafe_allow_html=True)

# --- 4. LOGIQUE MÉTIER ---

API_KEY = "2caafdd6dc7859e3f4b10419752b96a0"

def get_image_column(columns):
    """Cherche une colonne qui s'appelle image/IMAGE/Image..."""
    for col in columns:
        if str(col).strip().lower() == "image":
            return col
    return None

def upload_to_imagebb(image_bytes, api_key):
    url = "https://api.imgbb.com/1/upload"
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    payload = {"key": api_key, "image": b64_image}
    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        return response.json()['data']['url']
    except Exception as e:
        return f"Erreur" # Simplifié pour le tableau final

# Upload acceptant CSV et EXCEL
uploaded_file = st.file_uploader("📂 Chargez votre fichier (Excel ou CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # Lecture intelligente du fichier
    try:
        if uploaded_file.name.endswith('.csv'):
            # On essaie de lire, si ça échoue on tente avec le séparateur point-virgule (fréquent)
            try:
                df = pd.read_csv(uploaded_file)
                # Petit hack : si on a 1 seule colonne avec des points-virgules dedans, on relit
                if len(df.columns) == 1 and ';' in str(df.iloc[0,0]):
                     uploaded_file.seek(0)
                     df = pd.read_csv(uploaded_file, sep=';')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';')
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Impossible de lire le fichier. Erreur : {e}")
        st.stop()
        
    # Recherche de la colonne image (Insensible à la casse)
    target_col = get_image_column(df.columns)

    if not target_col:
        st.error("🚨 Aucune colonne nommée 'image' (ou IMAGE, Image...) n'a été trouvée.")
        st.write("Colonnes détectées :", list(df.columns))
    else:
        st.info(f"✅ Colonne détectée : **{target_col}** ({len(df)} lignes).")
        
        if st.button("🚀 Lancer la conversion"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            new_links = []
            
            for index, row in df.iterrows():
                url = row[target_col]
                status_text.text(f"Traitement {index+1}/{len(df)}...")
                
                # Vérification basique si c'est bien un lien
                if pd.isna(url) or str(url).strip() == "":
                    new_links.append("")
                    continue

                try:
                    # Téléchargement
                    resp = requests.get(str(url), timeout=10)
                    resp.raise_for_status()
                    
                    # Conversion PNG
                    img = Image.open(io.BytesIO(resp.content))
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    
                    # Upload
                    link = upload_to_imagebb(buffer.getvalue(), API_KEY)
                    new_links.append(link)
                    
                except Exception as e:
                    new_links.append("Erreur") # Ou garder l'ancien lien : new_links.append(url)
                
                progress_bar.progress((index + 1) / len(df))
                time.sleep(0.2)
            
            # Remplacement de la colonne existante
            df[target_col] = new_links
            
            status_text.success("✅ Terminé !")
            progress_bar.empty()
            
            # Export en Excel (toujours plus propre pour les liens)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Télécharger le résultat (Excel)",
                data=output.getvalue(),
                file_name="resultat_yassir_final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- 5. SIGNATURE ---
st.markdown("""
    <div class="footer">
        <p>Developed by <b>Bounoir Saif Eddine</b><br>
        Contact: <a href="mailto:saifeddine.bounoir@yassir.com">saifeddine.bounoir@yassir.com</a></p>
    </div>
""", unsafe_allow_html=True)
