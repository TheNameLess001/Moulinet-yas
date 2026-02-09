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

# --- SIDEBAR : CONFIGURATION API ---
with st.sidebar:
    st.header("🔑 Paramètres API")
    api_key_input = st.text_input("Clé API ImgBB", type="password", help="Entrez votre clé API ImgBB.")
    st.info("Clé gratuite ici : [api.imgbb.com](https://api.imgbb.com/)")

# --- HEADER ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    try:
        st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4umnB7rjE_AoR_VtRqiIIk-_8Dkqt771lZQ&s", width=180)
    except:
        st.title("YASSIR")
st.markdown("<h3 style='text-align: center;'>Convertisseur High-Speed (Debug Mode)</h3>", unsafe_allow_html=True)

# --- FONCTIONS ---

def process_single_image(url, api_key, max_size=None):
    if pd.isna(url) or str(url).strip() == "":
        return "Vide"
    
    url = str(url).strip()
    
    try:
        # 1. Download avec User-Agent (pour éviter le blocage 403 Forbidden)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status() # Lève une erreur si le téléchargement échoue (ex: 404)
        
        try:
            img = Image.open(io.BytesIO(resp.content))
        except Exception:
            return "Format Image Invalide"

        # Conversion RGB pour éviter les erreurs PNG/Palette
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # 2. Resize
        if max_size:
            img.thumbnail((max_size, max_size))
            
        # 3. Convert
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        
        # 4. Upload ImgBB
        upload_url = "https://api.imgbb.com/1/upload"
        b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        payload = {"key": api_key, "image": b64_image}
        
        post_resp = requests.post(upload_url, data=payload, timeout=30)
        
        if post_resp.status_code == 200:
            return post_resp.json()['data']['url']
        else:
            # Retourne l'erreur spécifique de l'API (ex: API key invalide)
            error_msg = post_resp.json().get('error', {}).get('message', 'Erreur API inconnue')
            return f"Err API: {error_msg}"
        
    except requests.exceptions.HTTPError as e:
        return f"Err HTTP: {e.response.status_code}"
    except Exception as e:
        # Retourne l'erreur Python précise
        return f"Err: {str(e)[:50]}"

def get_image_column_smart(columns):
    for col in columns:
        if "image" in str(col).strip().lower():
            return col
    return None

# --- UI PRINCIPALE ---

if not api_key_input:
    st.warning("⚠️ Veuillez saisir votre **Clé API ImgBB** dans la barre latérale.")
    st.stop()

uploaded_file = st.file_uploader("📂 Chargez votre fichier (Excel/CSV)", type=["xlsx", "csv"])

with st.expander("⚙️ Options avancées"):
    resize_option = st.checkbox("Redimensionner", value=True)
    max_pixels = st.slider("Max pixels", 500, 2000, 1000) if resize_option else None

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

    target_col = get_image_column_smart(df.columns)

    if target_col:
        st.success(f"✅ Colonne source : **'{target_col}'** ({len(df)} lignes)")
        
        # Aperçu avant traitement
        st.caption("Aperçu des 3 premières URLs :")
        st.code(df[target_col].head(3).to_string(index=False))

        if st.button("🚀 Lancer la conversion"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            urls = df[target_col].tolist()
            total = len(df)
            
            # Réduction des workers pour stabilité
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(process_single_image, url, api_key_input, max_pixels): index for index, url in enumerate(urls)}
                
                results_map = {}
                completed = 0
                
                for future in concurrent.futures.as_completed(futures):
                    index = futures[future]
                    results_map[index] = future.result()
                    completed += 1
                    
                    # Mise à jour UI
                    if completed % 5 == 0 or completed == total:
                        progress_bar.progress(completed / total)
                        status_text.text(f"Traitement : {completed}/{total}")

            # Création d'une NOUVELLE colonne pour ne pas écraser l'ancienne
            new_col_name = f"New_{target_col}"
            df[new_col_name] = [results_map[i] for i in range(total)]
            
            status_text.success("⚡ Terminé !")
            progress_bar.empty()
            
            # Afficher un aperçu des erreurs s'il y en a
            errors = df[df[new_col_name].astype(str).str.contains("Err")]
            if not errors.empty:
                st.warning(f"⚠️ {len(errors)} erreurs détectées. Voici un exemple :")
                st.write(errors[[target_col, new_col_name]].head())
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                "📥 Télécharger le résultat (avec détails erreurs)",
                data=output.getvalue(),
                file_name="resultat_yassir_debug.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("⚠️ Impossible de trouver une colonne 'image'.")

# --- FOOTER ---
st.markdown(f"""
    <div class="footer">
        <p>Developed by <b>Bounoir Saif Eddine</b> | Yassir Operations Tools</p>
    </div>
""", unsafe_allow_html=True)
