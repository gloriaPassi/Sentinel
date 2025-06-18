import streamlit as st
import json
import os
import feedparser
from datetime import datetime
from datetime import datetime, timedelta
from textblob import TextBlob
import pandas as pd
from googlesearch import search
import time
import requests
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from collections import Counter
from streamlit_option_menu import option_menu
import pandas as pd
import pytz
import re
from transformers import pipeline



favicon_path = os.path.join("icon", "favicon.ico")

# Cette ligne doit venir tout de suite après les imports
st.set_page_config(page_title="Sentinel : Veille Informationnelle", layout="wide",page_icon=favicon_path,)

# Ensuite ton cache et pipeline
@st.cache_resource
def load_sentiment_model():
    return pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")

sentiment_pipeline = load_sentiment_model()


# Fonction utilitaire pour convertir les labels du modèle en catégories simples
def convertir_etoiles_en_sentiment(label):
    if label in ["4 stars", "5 stars"]:
        return "Positif"
    elif label == "3 stars":
        return "Neutre"
    else:
        return "Négatif"


################### Authentification ###################

# Chargement des identifiants entreprises depuis JSON

def charger_entreprises():
    with open("Entreprises.json", "r") as f:
        return json.load(f)

# Vérification des identifiants
def verifier_identifiants(username, password, entreprises):
    for id_entreprise, infos in entreprises.items():
        if infos["username"] == username and infos["password"] == password:
            st.session_state["est_authentifie"] = True
            st.session_state["entreprise_id"] = id_entreprise
            st.session_state["nom_affichage"] = infos["nom_affichage"]
            return id_entreprise
    return False


# Interface de login
def afficher_login():
    st.title("🔐 Connexion à la plateforme de veille")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        entreprises = charger_entreprises()
        entreprise_id = verifier_identifiants(username, password, entreprises)
        if entreprise_id:
            st.session_state.authentifie = True
            st.session_state.entreprise_id = entreprise_id
            st.session_state.nom_affichage = entreprises[entreprise_id]["nom_affichage"]
            st.success(f"Bienvenue {st.session_state.nom_affichage} !")
            st.rerun()
        else:
            st.error("Identifiants incorrects")

# Comportement global
def verifier_connexion():
    if "authentifie" not in st.session_state:
        st.session_state.authentifie = False
    if not st.session_state.authentifie:
        afficher_login()
        st.stop()  # Bloque l'accès au reste tant qu'on n'est pas connecté


verifier_connexion()


# ✅ Charger les comptes avec cache
@st.cache_data
def charger_entreprises():
    with open("Entreprises.json", "r") as f:
        return json.load(f)

# ✅ Vérification login
def verifier_identifiants(username, password, entreprises):
    for id_ent, infos in entreprises.items():
        if infos["username"] == username and infos["password"] == password:
            return {
                "entreprise_id": id_ent,
                "nom_affichage": infos["nom_affichage"],
                "role": infos.get("role", "invité")
            }
    return None

# ✅ Interface de login
def afficher_login():
    st.markdown("<h2 style='color:#4B8BBE;'>🔐 Connexion à Sentinel</h2>", unsafe_allow_html=True)
    st.markdown("### Veuillez entrer vos identifiants :")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    login = st.button("Se connecter")

    if login:
        entreprises = charger_entreprises()
        utilisateur = verifier_identifiants(username, password, entreprises)
        if utilisateur:
            st.session_state.authentifie = True
            st.session_state.utilisateur = utilisateur
            st.success(f"Bienvenue {utilisateur['nom_affichage']} 🎉")
            st.experimental_rerun()
        else:
            st.error("Identifiants incorrects. Veuillez réessayer.")

# ✅ Bloquer accès si non connecté
def verifier_connexion():
    if "authentifie" not in st.session_state or not st.session_state.authentifie:
        afficher_login()
        st.stop()


API_KEY_YOUTUBE = "AIzaSyBe72qFn--gOiILHQBdGywtTLesSD20b8Q"

# Dossiers et fichiers JSON
CONFIG_FILE = "config.json"
SOURCES_FILE = "sources_a_verifier.json"
ARTICLES_FILE = "articles_pertinents.json"
KEYWORDS_FILE = "mots_cles_dangereux.json"

# Initialisation du dossier data
os.makedirs("data", exist_ok=True)
CONFIG_FILE = os.path.join("data", CONFIG_FILE)
SOURCES_FILE = os.path.join("data", SOURCES_FILE)
ARTICLES_FILE = os.path.join("data", ARTICLES_FILE)
KEYWORDS_FILE = os.path.join("data", KEYWORDS_FILE)

# Chargement ou création de la configuration
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"enterprise": "MaEntreprise"}, f)

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Chargement des sources
if not os.path.exists(SOURCES_FILE):
    with open(SOURCES_FILE, "w") as f:
        json.dump([], f)

def load_sources():
    with open(SOURCES_FILE, "r") as f:
        return json.load(f)

def save_sources(sources):
    with open(SOURCES_FILE, "w") as f:
        json.dump(sources, f, indent=2)

# Chargement des Mots-clés
if not os.path.exists(KEYWORDS_FILE):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump([], f)

def load_keywords():
    with open(KEYWORDS_FILE, "r") as f:
        return json.load(f)

def save_keywords(keywords):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump(keywords, f, indent=2)
        
# Sauvegarde des articles pertinents
def save_articles(articles):
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)


def load_articles():
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, "r" , encoding="utf-8") as f:
            return json.load(f)
    return []

# Analyse des flux RSS
def analyze_sources():
    config = load_config()
    enterprise_name = config.get("enterprise", "MaEntreprise").lower()
    sources = load_sources()
    keywords = [k.lower() for k in load_keywords()]
    found_articles = []

    new_articles = []
    texts_to_analyze = []

    for src in sources:
        feed = feedparser.parse(src)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            content = (title + " " + summary).lower()

            if enterprise_name in content:
                danger_hits = [kw for kw in keywords if kw in content]
                status = "RAS"
                if len(danger_hits) == 1:
                    status = "A surveiller"
                elif len(danger_hits) > 1:
                    status = "Critique"

                # Préparer l'article sans sentiment
                article = {
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": src,
                    "published": entry.get("published", datetime.now().isoformat()),
                    "status": status,
                    "danger_keywords": danger_hits,
                    "sentiment": None  # À remplir après analyse batch
                }

                new_articles.append(article)
                texts_to_analyze.append(title + " " + summary)

    # Analyse de sentiment en batch
    if texts_to_analyze:
        try:
            results = sentiment_pipeline(texts_to_analyze, batch_size=8)
            for article, result in zip(new_articles, results):
                sentiment_label = convertir_etoiles_en_sentiment(result['label'])
                article["sentiment"] = sentiment_label
        except Exception as e:
            print(f"Erreur lors de l'analyse de sentiment en batch RSS : {e}")
            # Par défaut sentiment neutre si erreur
            for article in new_articles:
                article["sentiment"] = "Neutre"

    # Fusion avec les articles précédents
    found_articles.extend(new_articles)

    save_articles(found_articles)
    return found_articles


# Analayse Web (Google)

from transformers import pipeline

try:
    sentiment_model = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
except Exception as e:
    print(f"Erreur lors du chargement du modèle de sentiment : {e}")
    sentiment_model = None  # Pour pouvoir gérer l'absence de modèle


def analyze_google_mentions():
    config = load_config()
    enterprise_name = config.get("enterprise", "MaEntreprise").lower()
    keywords = [k.lower() for k in load_keywords()]
    found_articles = load_articles()

    # Liste pour stocker les nouveaux articles et leurs textes à analyser
    new_articles = []
    texts_to_analyze = []

    for kw in keywords:
        query = f'"{enterprise_name}" "{kw}"'
        try:
            for url in search(query, num_results=5):
                # Texte à analyser (un seul bloc par article)
                text_for_sentiment = f"Mention trouvée sur Google : {enterprise_name} + {kw}. Résultat contenant le mot-clé dangereux '{kw}'."

                # On crée un article sans encore le sentiment
                article = {
                    "title": f"Mention trouvée sur Google : {enterprise_name} + {kw}",
                    "summary": f"Résultat Google contenant le mot-clé dangereux '{kw}'.",
                    "link": url,
                    "source": "Google Search",
                    "published": datetime.now().isoformat(),
                    "status": "Critique",
                    "danger_keywords": [kw],
                    # Sentiment temporaire, remplacé ensuite
                    "sentiment": None
                }

                new_articles.append(article)
                texts_to_analyze.append(text_for_sentiment)

                time.sleep(1)  # Respect Google Search

        except Exception as e:
            print(f"Erreur lors de la recherche Google pour '{query}' : {e}")

    # ⚡ Traitement en lot des sentiments
    if texts_to_analyze:
        try:
            results = sentiment_pipeline(texts_to_analyze, batch_size=8)
            for article, result in zip(new_articles, results):
                label = result['label']
                if label in ['4 stars', '5 stars']:
                    sentiment_label = "Positif"
                elif label == '3 stars':
                    sentiment_label = "Neutre"
                else:
                    sentiment_label = "Négatif"
                article["sentiment"] = sentiment_label
        except Exception as e:
            print(f"Erreur lors de l'analyse de sentiment en batch : {e}")
            # Fallback : tous neutres
            for article in new_articles:
                article["sentiment"] = "Neutre"

    # Fusion avec les anciens articles
    found_articles.extend(new_articles)

    save_articles(found_articles)
    return found_articles


#Analyse de Youtube
def search_youtube(query, max_results=10):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    video_url = "https://www.googleapis.com/youtube/v3/videos"

    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY_YOUTUBE
    }

    response = requests.get(search_url, params=search_params)
    results = response.json()
    video_ids = [item["id"]["videoId"] for item in results.get("items", [])]

    if not video_ids:
        return []

    details_params = {
        "part": "snippet",
        "id": ",".join(video_ids),
        "key": API_KEY_YOUTUBE
    }

    response_details = requests.get(video_url, params=details_params)
    details = response_details.json()

    video_data = []
    for item in details.get("items", []):
        snippet = item["snippet"]
        video_data.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "channel": snippet["channelTitle"],
            "description": snippet["description"]
        })

    return video_data



##################################### Interface Streamlit ##############################
#st.set_page_config(page_title="Veille Informationnelle", layout="wide")

# Appliquer une police personnalisée à toute l'app
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

config = load_config()
enterprise_name = config.get("enterprise", "MaEntreprise")

 # 🖼️ Logo + Titre + Nom entreprise
col1, col2 = st.columns([1, 4])
with col1:
    st.image("img/sentinellogo1.svg", width=200)  # ajuste le chemin et la taille
with col2:
    st.markdown(
        f"<h3 style='color:#306998; margin-top: 0;'>Bienvenue sur <span style='color:#FFD43B;'>Sentinel</span>, {enterprise_name} 👋</h3>", 
        unsafe_allow_html=True
    )
st.markdown("<hr style='margin-top:10px;margin-bottom:30px'>", unsafe_allow_html=True)

 

with st.sidebar:
    st.image("img/sentinellogo1.svg", width=180)  # ✅ version à jour
    st.markdown("Anticipez les risques, protégez votre réputation avec Sentinel, votre outil de veille intelligent.")
    st.markdown("Version 1.0")
    st.markdown("---")

# Menu dans la sidebar
with st.sidebar:
    page = option_menu(
        menu_title="",  # Titre du menu
        options=["Accueil", "Dashboard", "Configuration", "Lancer l'analyse"],
        icons=["house", "bar-chart", "gear", "search"],
        menu_icon="cast",  # icône du titre
        default_index=0,
        orientation="vertical",
        styles={
            "container": {"padding": "5px", "background-color": "#f0f2f6"},
            "icon": {"color": "black", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "2px",
                "--hover-color": "#eee",
            },
            "nav-link-selected": {"background-color": "#2f4faa", "color": "white"},
        }
    )


# Bouton de déconnexion dans la sidebar
if st.sidebar.button("Se déconnecter"):
    st.session_state.authentifie = False
    st.session_state.entreprise_id = None
    st.session_state.nom_affichage = ""
    st.rerun()

if 'show_about' not in st.session_state:
    st.session_state.show_about = False

if st.sidebar.button("À propos"):
    st.session_state.show_about = True

if st.session_state.show_about:
    with st.sidebar.expander("À propos", expanded=True):
        st.write("Cette application a été développée par PASSI Gloria-Jérémie, ingénieur en Génie numérique - Data Engineering.")
        st.write("Version 1.0 - 2025")
        if st.sidebar.button("Fermer"):
            st.session_state.show_about = False
            st.rerun()  # remplace st.rerun() qui n'existe pas

            
config = load_config()
enterprise_name = config.get("enterprise", "MaEntreprise")

# Page 1 : Accueil
if page == "Accueil":

    st.markdown("""
    <div style="background-color:#000080;padding:20px;border-radius:10px;margin-bottom:20px">
        <h1 style="color:white;text-align:center">Veille Informationnelle</h1>
        <p style="color:white;text-align:center">Résultats d'analyse de la réputation en ligne</p>
    </div>
    """, unsafe_allow_html=True)


    st.write("Articles mentionnant explicitement votre entreprise.")
    articles = load_articles()

    if articles:
        # Créer un DataFrame avec les articles
        df = pd.DataFrame(articles)

        # --- Ajout des filtres ---
        unique_sources = df['source'].dropna().unique().tolist()
        unique_status = df['status'].dropna().unique().tolist()

        selected_sources = st.multiselect("Filtrer par source :", unique_sources, default=unique_sources)
        selected_status = st.multiselect("Filtrer par statut :", unique_status, default=unique_status)

        # Appliquer les filtres au DataFrame
        df = df[df['source'].isin(selected_sources)]
        df = df[df['status'].isin(selected_status)]

        # Calcul du score d'état de santé basé sur le statut et sentiment des articles
        health_score = 0
        total_articles = len(df)

        for a in df.itertuples():
            if a.status == "Critique":
                health_score -= 2
            elif a.status == "A surveiller":
                health_score -= 1
            else:
                health_score += 0

            if a.sentiment == "Négatif":
                health_score -= 1
            elif a.sentiment == "Positif":
                health_score += 1

        max_possible_score = total_articles * 2
        min_possible_score = total_articles * -3
        normalized_score = (health_score - min_possible_score) / (max_possible_score - min_possible_score) * 100 if total_articles > 0 else 0

        st.subheader("État de santé de la réputation")

        if normalized_score >= 75:
            health_status = "Bonne"
            health_color = "green"
        elif normalized_score >= 50:
            health_status = "Moyenne"
            health_color = "orange"
        else:
            health_status = "Critique"
            health_color = "red"

        st.markdown(f"""
        <div style="background-color: {health_color}; padding: 20px; border-radius: 10px; text-align: center;">
            <h3 style="color: white;">État de santé de l'entreprise</h3>
            <p style="color: white;">Cela met l'accent sur l'évaluation et le suivi des sources à surveiller.</p>
            <h1 style="color: white;">{int(normalized_score)}%</h1>
            <p style="color: white;">Reputation: {health_status}</p>
        </div>
        """, unsafe_allow_html=True)

        # Afficher les articles filtrés
        for a in df[::-1].itertuples():
            status_emoji = ""
            if a.status == "A surveiller":
                status_emoji = "⚠️"
            elif a.status == "Critique":
                status_emoji = "🚨"

            sentiment_color = "green"
            if a.sentiment == "Négatif":
                sentiment_color = "red"
            elif a.sentiment == "Neutre":
                sentiment_color = "orange"

            with st.expander(f"{status_emoji} {a.title}"):
                st.markdown(f"**Source :** {a.source}")
                st.markdown(f"**Date :** {a.published}")
                st.markdown(f"**Statut :** {a.status}")
                st.markdown(f"**Sentiment :** :{sentiment_color}[{a.sentiment}]")
                if a.danger_keywords:
                    st.markdown(f"**Mots-clés détectés :** {', '.join(a.danger_keywords)}")
                st.markdown(a.summary)
                st.markdown(f"[Lire l'article]({a.link})")

    else:
        st.info("Aucun article trouvé. Veuillez lancer l'analyse.")

# Page 2 : Configuration

elif page == "Configuration":

   
    
    st.markdown("""
    <div style="background-color:#2C3E50;padding:20px;border-radius:10px;margin-bottom:16px">
        <h1 style="color:white;text-align:center">Configuration de l'application</h1>
        
    </div>
    """, unsafe_allow_html=True)


    
    # Nom de l'entreprise
    enterprise_input = st.text_input("Nom de l'entreprise", value=enterprise_name)

    # Deux colonnes côte à côte pour les boutons
    col1, col2, col3, col4 = st.columns([3, 3, 3, 3])

    with col1:
        if st.button("💾 Enregistrer le nom"):
            config["enterprise"] = enterprise_input
            save_config(config)
            st.success("✅ Nom de l'entreprise mis à jour !")
     
    with col2:
        if st.button("🗑️ Vider les articles pertinents"):
            def clear_articles_file():
                with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            if os.path.exists(ARTICLES_FILE):
                clear_articles_file()
                st.success("✅ Fichier vidé avec succès.")
            else:
                st.warning("⚠️ Le fichier n'existe pas.")
    
    with col3:
        if st.button("🧹 Vider les mots-clés dangereux"):
            def clear_keywords():
                with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            if os.path.exists(KEYWORDS_FILE):
                clear_keywords()
                st.success("✅ Mots-clés vidés avec succès.")
            else:
                st.warning("⚠️ Le fichier des mots-clés n'existe pas.")
    with col4:
        if st.button("🔌 Vider les sources RSS"):
            def clear_sources():
                with open(SOURCES_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            if os.path.exists(SOURCES_FILE):
                clear_sources()
                st.success("✅ Sources RSS vidées avec succès.")
            else:
                st.warning("⚠️ Le fichier des sources RSS n'existe pas.")
    
    # Ligne de séparation visuelle
    st.markdown("---")
    
    # Gestion des sources
    st.markdown("""
<div style="background-color:#FF8C00; padding:10px 20px; border-radius:8px; margin-top:20px; margin-bottom:10px;">
    <h3 style="color:white; margin:0;">Surveillance des sources RSS </h3>
</div>
""", unsafe_allow_html=True)


    sources = load_sources()

    for i, s in enumerate(sources):
        col1, col2 = st.columns([5,1])
        col1.write(s)
        if col2.button("❌", key=f"suppr_{i}"):
            sources.pop(i)
            save_sources(sources)
            

    new_source = st.text_input("Ajouter une nouvelle source RSS")
    if st.button("Ajouter") and new_source:
        sources.append(new_source)
        save_sources(sources)
        st.success("Source ajoutée avec succès !")

    # Gestion des Mots-clés
    st.markdown("---")
    st.markdown("""
<div style="background-color:#922B21; padding:10px 20px; border-radius:8px; margin-top:20px; margin-bottom:10px;">
    <h3 style="color:white; margin:0;">Mots ou phrases clés</h3>
</div>
""", unsafe_allow_html=True)

    keywords = load_keywords()

    for i, kw in enumerate(keywords):
        col1, col2 = st.columns([5, 1])
        col1.write(kw)
        if col2.button("❌", key=f"suppr_kw_{i}"):
            keywords.pop(i)
            save_keywords(keywords)
        

    new_keyword = st.text_input("Ajouter un mot-clé dangereux")
    if st.button("Ajouter mot-clé") and new_keyword:
        keywords.append(new_keyword)
        save_keywords(keywords)
        st.success("Mot-clé ajouté avec succès !")

# Page 3 : Lancer l'analyse
elif page == "Lancer l'analyse":
   
    st.markdown("""
    <div style="background-color:#ffde59;padding:20px;border-radius:10px;margin-bottom:20px">
        <h1 style="color:white;text-align:center">Analyse de la Réputation en Ligne</h1>
        <p style="color:white;text-align:center">Extraction et détection des informations </p>
    </div>
    """, unsafe_allow_html=True)

    # Injection de CSS pour styliser les colonnes en "cards"
    # CSS ciblant les containers Streamlit
    st.markdown("""
        <style>
        /* On stylise les colonnes/cards Streamlit via leurs classes */
        .stButton > button {
            width: 100%;
        }
        .css-1adrfps {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background-color: blue;  /* couleur de fond claire (bleu alice) */
            transition: box-shadow 0.3s ease-in-out;
        }
        .streamlit-expander, .css-1adrfps {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background-color: white;
            transition: box-shadow 0.3s ease-in-out;
        }
        .css-1adrfps:hover {
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }
        .card-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .card-desc {
            font-size: 14px;
            color: #555;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="card-title">Analyse des flux RSS</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-desc">Analysez les dernières actualités provenant de vos sources RSS.</div>', unsafe_allow_html=True)
        if st.button("Analyser les flux RSS"):
            with st.spinner("Analyse des flux RSS en cours..."):
                articles_rss = analyze_sources()
            st.success(f"{len(articles_rss)} articles trouvés via les flux RSS.")

    with col2:
        st.markdown('<div class="card-title">Mentions sur Google</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-desc">Recherchez les mentions de votre entreprise sur Google.</div>', unsafe_allow_html=True)
        if st.button("Analyser les mentions sur Google"):
            with st.spinner("Analyse des résultats Google en cours..."):
                articles_google = analyze_google_mentions()
            st.success(f"{len(articles_google)} mentions trouvées sur Google.")

    with col3:
        st.markdown('<div class="card-title">Analyse des vidéos YouTube</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-desc">Recherchez les vidéos liées à votre entreprise sur YouTube.</div>', unsafe_allow_html=True)
        if st.button("Analyser les vidéos YouTube"):
            with st.spinner("Recherche YouTube en cours..."):
                config = load_config()
                keywords = load_keywords()
                all_results = []
                for kw in keywords:
                    query = f"{config['enterprise']} {kw}"
                    results = search_youtube(query, max_results=3)
                    for video in results:
                        all_results.append({
                            "title": f"Vidéo YouTube : {video['title']}",
                            "summary": f"Chaîne : {video['channel']} — {video['description'][:200]}...",
                            "link": video["url"],
                            "source": "YouTube",
                            "published": datetime.now().isoformat(),
                            "status": "A surveiller",
                            "danger_keywords": [kw],
                            "sentiment": "Neutre"
                        })
                existing = load_articles()
                if not existing:
                    existing = []
                elif isinstance(existing, dict):
                    existing = [existing]
                updated = existing + all_results
                save_articles(updated)
            st.success(f"{len(all_results)} vidéos trouvées sur YouTube.")

# Page 4 : Dashboard - nouvelle page analytique
elif page == "Dashboard":

    from datetime import datetime, timedelta, timezone


    # --- Chargement des articles ---
    articles = load_articles()
    df = pd.DataFrame(articles if articles else [])

    # --- Conversion de la date de publication ---
    if 'published' in df.columns:
        df['published'] = pd.to_datetime(df['published'], errors='coerce')
        if not isinstance(df['published'].dtype, pd.DatetimeTZDtype):
            df['published'] = df['published'].dt.tz_localize('UTC')
    else:
        df['published'] = pd.NaT

    # --- Chargement des mots clés dangereux ---
    with open("data/mots_cles_dangereux.json", "r", encoding="utf-8") as f:
        mots_cles_dangereux = set(line.strip().lower() for line in f if line.strip())

    # --- Fonctions utilitaires ---

    def compter_articles_recents(df, jours=30):
        date_limite = datetime.now(timezone.utc) - timedelta(days=jours)
        # S’assurer que la colonne 'published' est timezone-aware UTC
        if not isinstance(df['published'].dtype, pd.DatetimeTZDtype):
            df['published'] = df['published'].dt.tz_localize('UTC')
        return df[df['published'] >= date_limite].shape[0]

    def extraire_mots_cles_dangereux(texte, mots_cles_dangereux):
        texte = texte.lower()
        mots = re.findall(r'\b\w+\b', texte)
        return [mot for mot in mots if mot in mots_cles_dangereux]

    def multiselect_with_select_all(label, options, default=None):
        if default is None:
            default = options
        all_selected = st.checkbox(f"Tout sélectionner - {label}", value=True, key=label+"_all")
        if all_selected:
            selection = st.multiselect(label, options, default=default, key=label)
        else:
            selection = st.multiselect(label, options, default=[], key=label)
        return selection

    # --- Timeline groupée par jour ---
    if not df['published'].isna().all():
        df_timeline = df.groupby(pd.Grouper(key='published', freq='D')).size().reset_index(name='count')
    else:
        df_timeline = pd.DataFrame(columns=['published', 'count'])


    # Calcul du score santé
    score = 0
    if not df.empty and 'sentiment' in df.columns:
        total = df.shape[0]
        positifs = df[df['sentiment'] == 'positif'].shape[0]
        score = int((positifs / total) * 100) if total > 0 else 0

    # Autres KPI
    nb_articles_recents = compter_articles_recents(df)
    nb_articles_total = df.shape[0]

    nb_google = df[df['source'] == 'Google Search'].shape[0] if 'source' in df.columns else 0
    nb_youtube = df[df['source'] == 'YouTube'].shape[0] if 'source' in df.columns else 0
    nb_rss = df[df['source'].str.contains("rss", case=False, na=False)].shape[0] if 'source' in df.columns else 0

    # --- Affichage principal ---
    st.markdown("""
    <div style="background-color:#05f4f9;padding:20px;border-radius:10px;margin-bottom:20px">
        <h1 style="color:white;text-align:center">Dashboard Analytique</h1>
        <p style="color:white;text-align:center">Vue d'ensemble des signaux de veille et des contenus sensibles</p>
    </div>
    """, unsafe_allow_html=True)

    # --- KPI ---
    st.subheader("Indicateurs Clés")
    col1, col2, col3, col4, col5 = st.columns(5)

    card_style = """
        background-color: {bgcolor};
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
    """

    color = "green" if score >= 70 else "orange" if score >= 40 else "red"
    etat = "Bon" if score >= 70 else "Moyen" if score >= 40 else "Critique"

    with col1:
        st.markdown(f"""
        <div style="{card_style.format(bgcolor=color)}">
            <h6>Score global de santé</h6>
            <h1>{score} %</h1>
            <p>État général : <b>{etat}</b></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="{card_style.format(bgcolor='#1f77b4')}">
            <h6>Nombre total d'articles</h6>
            <h1>{nb_articles_total}</h1>
            <p>Contenus collectés</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="{card_style.format(bgcolor='#ff7f0e')}">
            <h6>Mentions Google</h6>
            <h1>{nb_google}</h1>
            <p>Sources Google</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="{card_style.format(bgcolor='#9467bd')}">
            <h6>Mentions YouTube</h6>
            <h1>{nb_youtube}</h1>
            <p>Sources YouTube</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style="{card_style.format(bgcolor='#8c564b')}">
            <h6>Mentions RSS</h6>
            <h1>{nb_rss}</h1>
            <p>Sources RSS</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Visualisations principales ---
    st.subheader("Répartition et tendances")

    col_a, col_b = st.columns(2)
    with col_a:
        repartition_statut = df['status'].value_counts() if 'status' in df.columns else pd.Series()
        if not repartition_statut.empty:
            fig_statut = px.pie(values=repartition_statut.values, names=repartition_statut.index,
                                title="Répartition des statuts")
            st.plotly_chart(fig_statut, use_container_width=True)
        else:
            st.info("Données de statut non disponibles")

    with col_b:
        repartition_sentiment = df['sentiment'].value_counts() if 'sentiment' in df.columns else pd.Series()
        if not repartition_sentiment.empty:
            fig_sentiment = px.bar(repartition_sentiment, title="Répartition des sentiments")
            st.plotly_chart(fig_sentiment, use_container_width=True)
        else:
            st.info("Données de sentiment non disponibles")

    st.markdown("---")

    col_c, col_d = st.columns(2)
    with col_c:
        if 'published' in df.columns:
            df_timeline = df.groupby(pd.Grouper(key='published', freq='D')).size().reset_index(name='count')
            fig_timeline = px.line(df_timeline, x='published', y='count', title="Chronologie des articles")
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Données de publication non disponibles")

    with col_d:
        st.info("Analyse de tendance ou polarité ici")

    st.markdown("---")

    # --- Filtres et Treemap ---
    st.subheader("Analyse des mots clés sensibles")

    col_filtres, col_treemap = st.columns([1, 2.3])
    with col_filtres:
        st.markdown("### Filtres")
        sources = df['source'].dropna().unique() if 'source' in df.columns else []
        sentiments = df['sentiment'].dropna().unique() if 'sentiment' in df.columns else []
        source_filter = multiselect_with_select_all("Filtrer par source", options=sources)
        sentiment_filter = multiselect_with_select_all("Filtrer par sentiment", options=sentiments)

    filtered_df = df[
        (df['source'].isin(source_filter)) & (df['sentiment'].isin(sentiment_filter))
    ] if not df.empty else pd.DataFrame()

    mots = []
    for texte in filtered_df.get("summary", []):
        if isinstance(texte, str):
            mots.extend(extraire_mots_cles_dangereux(texte, mots_cles_dangereux))

    frequences = Counter(mots)
    top_mots = frequences.most_common(30)

    with col_treemap:
        if not top_mots:
            st.warning("Aucun mot dangereux trouvé avec les filtres sélectionnés.")
        else:
            df_mots = pd.DataFrame(top_mots, columns=["mot", "frequence"])
            fig = px.treemap(
                df_mots,
                path=["mot"],
                values="frequence",
                color="frequence",
                color_continuous_scale="Reds"
            )
            fig.update_layout(
                margin=dict(t=30, l=0, r=0, b=0),
                paper_bgcolor="#f5f5f5",
                plot_bgcolor="#f5f5f5",
                title="Treemap des mots dangereux",
                title_x=0.5,
                font=dict(size=14)
            )
            st.plotly_chart(fig, use_container_width=True)
