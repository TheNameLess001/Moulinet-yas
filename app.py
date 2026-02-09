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
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR : CONFIGURATION ---
with st.sidebar:
    st.header("🔑 Paramètres")
    api_key_input = st.text_input("Clé API ImgBB", type="password")
    st.info("Clé gratuite : [api.imgbb.com](https://api.imgbb.com/)")
    
    st.markdown("---")
    st.header("🔧 Format Fichier")
    separator_option = st.selectbox(
        "Séparateur CSV",
        options=["Auto-détection", "Point-virgule (;)", "Virgule (,)", "Tabulation (\\t)"],
        index=0
    )

# --- FONCTIONS ---

def detect_separator(file_obj):
    """Tente de deviner le séparateur en lisant les premières lignes"""
    try:
        file_obj.seek(0)
        sample = file_obj.read(2048).decode('utf-8', errors='ignore')
        file_obj.seek(0)
        
        # Compte les occurrences
        semicolons = sample.count(';')
        commas = sample.count(',')
        tabs = sample.count('\t')
        
        if semicolons > commas and semicolons > tabs:
            return ';'
        elif tabs > commas and tabs > semicolons:
            return '\t'
        else:
            return ',' # Par défaut
    except:
        return ','

def process_single_image(url, api_key, max_size=None):
    if pd.isna(url) or str(url).strip() == "":
        return ""
    
    url = str(url).strip()
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        img = Image.open(io.BytesIO(resp.content))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            
        if max_size: img.thumbnail((max_size, max_size))
            
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        
        upload_url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key, "image": base64.b64encode(buffer.getvalue()).decode('utf-8')}
        
        post_resp = requests.post(upload_url, data=payload, timeout=30)
        if post_resp.status_code == 200:
            return post_resp.json()['data']['url']
        else:
            return f"Err API: {post_resp.json().get('error', {}).get('message', 'Unknown')}"
        
    except Exception as e:
        return f"Err: {str(e)[:50]}"

# --- MAIN ---
st.title("YASSIR - Convertisseur")

if not api_key_input:
    st.warning("⚠️ Entrez votre clé API à gauche.")
    st.stop()

uploaded_file = st.file_uploader("📂 Chargez votre fichier original (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # 1. Lecture du fichier avec le bon séparateur
    try:
        if uploaded_file.name.endswith('.csv'):
            # Détermination du séparateur
            if separator_option == "Auto-détection":
                sep = detect_separator(uploaded_file)
                st.info(f"ℹ️ Séparateur détecté : '{sep}'")
            elif separator_option == "Point-virgule (;)": sep = ';'
            elif separator_option == "Virgule (,)": sep = ','
            else: sep = '\t'
            
            df = pd.read_csv(uploaded_file, sep=sep, on_bad_lines='skip', engine='python')
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        st.stop()

    # 2. Vérification de la structure
    st.write("👀 **Aperçu des données (5 premières lignes) :**")
    st.dataframe(df.head())
    
    if len(df.columns) < 2:
        st.error("⚠️ Attention : 1 seule colonne détectée. Le séparateur est probablement incorrect. Changez-le dans le menu de gauche.")
        st.stop()

    # 3. Recherche de la colonne image
    target_col = None
    for col in df.columns:
        if "image" in str(col).lower():
            target_col = col
            break
            
    if target_col:
        st.success(f"✅ Colonne cible : **{target_col}**")
        
        if st.button("🚀 Lancer la conversion"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            urls = df[target_col].tolist()
            results = []
            total = len(urls)
            
            # Utilisation de ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # On map chaque future à son index pour garder l'ordre
                future_to_index = {
                    executor.submit(process_single_image, url, api_key_input, 1000): i 
                    for i, url in enumerate(urls)
                }
                
                results = [None] * total # Pré-allocation
                completed = 0
                
                for future in concurrent.futures.as_completed(future_to_index):
                    idx = future_to_index[future]
                    results[idx] = future.result()
                    completed += 1
                    if completed % 2 == 0 or completed == total:
                        progress_bar.progress(completed / total)
                        status_text.text(f"Traitement : {completed}/{total}")

            # Création de la colonne résultat
            df[f"New_{target_col}"] = results
            
            status_text.success("Terminé !")
            
            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                "📥 Télécharger le fichier corrigé",
                data=output.getvalue(),
                file_name="resultat_final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    else:
        st.error("❌ Aucune colonne contenant 'image' n'a été trouvée. Vérifiez l'aperçu ci-dessus.")
