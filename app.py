import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import base64
import concurrent.futures

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="Yassir - Convertisseur Pro", page_icon="🟣", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1, h2, h3 { color: #4A148C !important; }
    div.stButton > button {
        background-color: #4A148C; color: white; border-radius: 8px;
        padding: 10px 24px; font-weight: bold; border: none; width: 100%;
    }
    div.stButton > button:hover { background-color: #7c43bd; color: white; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #f8f9fa; color: #4A148C; text-align: center;
        padding: 10px; font-size: 12px; border-top: 3px solid #4A148C; z-index: 100;
    }
    .footer a { color: #4A148C; font-weight: bold; text-decoration: none; }
    .block-container { padding-bottom: 80px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    try:
        st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4umnB7rjE_AoR_VtRqiIIk-_8Dkqt771lZQ&s", width=180)
    except:
        st.title("YASSIR")
st.markdown("<h3 style='text-align: center;'>Convertisseur High-Speed (Multi-Thread)</h3>", unsafe_allow_html=True)

# --- FONCTIONS ---

# Gestion de la clé API (soit dans les secrets, soit en dur pour le test)
try:
    API_KEY = st.secrets["imgbb_api_key"]
except:
    API_KEY = "2caafdd6dc7859e3f4b10419752b96a0" # Fallback pour tes tests locaux

def process_single_image(url, api_key, max_size=None):
    """Fonction qui traite une seule image (Télécharge -> Resize -> Convert -> Upload)"""
    if pd.isna(url) or str(url).strip() == "":
        return ""
    
    try:
        # 1. Download
        resp = requests.get(str(url), timeout=10)
        resp.raise_for_status()
        
        img = Image.open(io.BytesIO(resp.content))
        
        # 2. Resize optionnel (pour optimiser le PNG)
        if max_size:
            img.thumbnail((max_size, max_size)) # Garde les proportions
            
        # 3. Convert to PNG
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        
        # 4. Upload ImageBB
        upload_url = "https://api.imgbb.com/1/upload"
        b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        payload = {"key": api_key, "image": b64_image}
        
        post_resp = requests.post(upload_url, data=payload, timeout=30)
        post_resp.raise_for_status()
        return post_resp.json()['data']['url']
        
    except Exception:
        return "Erreur"

def get_image_column(columns):
    for col in columns:
        if str(col).strip().lower() == "image": return col
    return None

# --- UI PRINCIPALE ---

uploaded_file = st.file_uploader("📂 Chargez votre fichier (Excel/CSV)", type=["xlsx", "csv"])

# Option pour redimensionner (Caché dans un 'expander' pour garder l'interface propre)
with st.expander("⚙️ Options avancées (Redimensionnement)"):
    resize_option = st.checkbox("Redimensionner les images (Recommandé pour réduire la taille)", value=True)
    max_pixels = st.slider("Taille maximum (px)", 500, 2000, 1000) if resize_option else None

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file)
            except: 
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';')
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erreur lecture: {e}")
        st.stop()

    target_col = get_image_column(df.columns)

    if target_col:
        st.info(f"✅ {len(df)} images à traiter. Mode Rapide activé.")
        
        if st.button("🚀 Lancer la conversion rapide"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- PARALLÉLISATION ---
            # On utilise ThreadPoolExecutor pour lancer plusieurs tâches en même temps
            results = []
            total = len(df)
            urls = df[target_col].tolist()
            
            # Max workers = nombre de connexions simultanées (5 à 10 est bien pour ne pas bloquer l'API)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                # On lance tout
                futures = {executor.submit(process_single_image, url, API_KEY, max_pixels): index for index, url in enumerate(urls)}
                
                # On récupère les résultats au fur et à mesure
                completed = 0
                results_map = {} # Pour garder l'ordre
                
                for future in concurrent.futures.as_completed(futures):
                    index = futures[future]
                    try:
                        res = future.result()
                    except:
                        res = "Erreur Fatal"
                    
                    results_map[index] = res
                    completed += 1
                    
                    # Mise à jour UI
                    progress = completed / total
                    progress_bar.progress(progress)
                    status_text.text(f"Traitement : {completed}/{total}")

            # Reconstruire la liste dans le bon ordre initial
            final_links = [results_map[i] for i in range(total)]
            
            # Mise à jour DF
            df[target_col] = final_links
            
            status_text.success("⚡ Terminé en un temps record !")
            progress_bar.empty()
            
            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                "📥 Télécharger le fichier final",
                data=output.getvalue(),
                file_name="resultat_yassir_pro.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("Colonne 'image' introuvable.")

# --- FOOTER ---
st.markdown("""
    <div class="footer">
        <p>Developed by <b>Bounoir Saif Eddine</b> | Yassir Operations Tools<br>
        <a href="mailto:saifeddine.bounoir@yassir.com">saifeddine.bounoir@yassir.com</a></p>
    </div>
""", unsafe_allow_html=True)
