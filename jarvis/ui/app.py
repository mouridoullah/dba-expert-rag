"""
jarvis/ui/app.py - Interface Web Streamlit (Orchestrateur)
"""
import streamlit as st
from jarvis.retrieval.search import VectorSearch
from jarvis.llm.expert import Expert
from jarvis.config.settings import settings
from jarvis.config.validators import SearchQuery
from pydantic import ValidationError
from jarvis.core.logger import setup_logging
import logging

# Initialise les logs JSON dès le lancement de l'interface
setup_logging(logging.INFO)

# 1. Configuration de la page
st.set_page_config(
    page_title=settings.streamlit_page_title,
    layout=settings.streamlit_layout,
    page_icon="🧠"
)

st.title("Jarvis : Assistant DBA Senior")
st.markdown("*Architecture RAG V2 (Modulaire, Résiliente & Sécurisée)*")

# 2. Chargement des cerveaux en cache (pour ne pas les recharger à chaque clic)
@st.cache_resource
def load_jarvis():
    return VectorSearch(settings), Expert(settings)

search, expert = load_jarvis()

# 3. Mémoire Conversationnelle
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. L'Interface utilisateur
if question := st.chat_input("Posez votre question technique : Ex: Comment surveiller les deadlocks sur Postgres ?"):
    
    try:
        # 🛡️ LE BOUCLIER : On valide la question avant de polluer l'historique !
        validated_query = SearchQuery(question=question)
        question_propre = validated_query.question
        
        # Historique Safe : Ajouter la question (assainie)
        st.session_state.messages.append({"role": "user", "content": question_propre})
        
        with st.chat_message("user"):
            st.markdown(question_propre)
            
            # ÉTAPE A : Le Routage
            with st.status("🧠 Analyse et Routage IA...", expanded=False) as status:
                moteur, version = search.query_router(question_propre)
                st.write(f"📍 **Décision :** Moteur = `{moteur.upper()}` | Version = `{version.upper()}`")
                status.update(label="Routage terminé", state="complete", expanded=False)
            
            # ÉTAPE B : La Recherche Hybride
            with st.status("🔍 Recherche hybride en base de connaissances...", expanded=False) as status:
                context = search.hybrid_search(question_propre, moteur, version)
                st.write(f"Vecteurs et Textes : {len(context)} sources pertinentes analysées.")
                status.update(label="Recherche terminée", state="complete", expanded=False)
                
        # ÉTAPE C : Génération avec historique
        with st.chat_message("assistant"):
            with st.spinner("👨‍💻 L'Expert DBA rédige la réponse finale..."):
                history = st.session_state.messages[:-1]
                reponse = expert.generate_answer(question_propre, context, history)
                
            st.markdown(reponse)
            
            with st.expander(f"📑 Voir les {len(context)} sources expertes documentaires"):
                for idx, doc in enumerate(context):
                    st.markdown(f"**Source {idx+1} : {doc['titre_chapitre']}**")
                    st.text(doc['contenu'][:300] + "...\n")
                    
            st.session_state.messages.append({"role": "assistant", "content": reponse})
            
    except ValidationError as e:
        with st.chat_message("assistant"):
            st.error("⚠️ La question contient des caractères dangereux ou est invalide.")
    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"❌ Une erreur système est survenue : {e}")
        # Retrait de la question orpheline pour ne pas disjoncter l'historique
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop()
