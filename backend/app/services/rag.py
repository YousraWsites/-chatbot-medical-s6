import os
import requests
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "./documents")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

# Score = distance L2 (plus bas = plus pertinent) avec all-MiniLM-L6-v2.
# Au-delà de ce seuil, les chunks ne sont plus assez liés à la question
# -> on bascule sur une recherche web pour ne pas répondre "à côté".
RELEVANCE_THRESHOLD = 0.9

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_vectorstore():
    docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    for fname in os.listdir(DOCS_DIR):
        if fname.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(DOCS_DIR, fname))
            pages = loader.load()
            docs.extend(splitter.split_documents(pages))
    Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_DIR)
    print(f"{len(docs)} chunks indexés dans ChromaDB")

def get_vectorstore():
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

def reformulate_search_query(question: str) -> str:
    """Transforme une phrase de patient en requête de recherche médicale propre.

    Sans ça, une phrase comme "j'ai de la fièvre" est interprétée par le moteur
    de recherche comme une demande de traduction (résultats Reverso/Collins...)
    plutôt qu'une question médicale.
    """
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "mistralai/mistral-small-3.2-24b-instruct",
                "messages": [{
                    "role": "user",
                    "content": (
                        "Transforme cette phrase d'un patient en une requête de recherche web "
                        "concise pour trouver une information médicale fiable (symptômes, causes, "
                        "traitement...). Réponds uniquement avec la requête, sans explication, sans guillemets.\n\n"
                        f"Phrase du patient : {question}"
                    ),
                }],
            },
            timeout=10,
        )
        reformulated = response.json()["choices"][0]["message"]["content"].strip()
        return reformulated or question
    except Exception:
        return question


def web_search(question: str, max_results: int = 3) -> str:
    try:
        query = reformulate_search_query(question)
        results = DDGS().text(query, max_results=max_results)
        return "\n\n".join(f"{r['title']} : {r['body']} (source: {r['href']})" for r in results)
    except Exception:
        return ""


def _call_openrouter(prompt: str) -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        json={
            "model": os.getenv("OPENROUTER_MODEL", "mistralai/mistral-small-3.2-24b-instruct"),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    response = model.generate_content(prompt)
    return response.text


def _call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    return _call_openrouter(prompt)


def get_rag_response(question: str, history: list) -> tuple[str, str]:
    """Retourne (réponse, source) où source vaut "doc" ou "web"."""
    doc_context = ""
    needs_web_search = True
    try:
        if os.path.exists(CHROMA_DIR):
            vectorstore = get_vectorstore()
            hits = vectorstore.similarity_search_with_score(question, k=4)
            doc_context = "\n\n".join(doc.page_content for doc, _ in hits)
            needs_web_search = not hits or min(score for _, score in hits) > RELEVANCE_THRESHOLD
    except Exception:
        doc_context = ""

    source = "web" if needs_web_search else "doc"

    web_context = web_search(question) if needs_web_search else ""

    history_text = ""
    for msg in history[-6:]:  # garder les 6 derniers messages
        role = "Patient" if msg["role"] == "user" else "Chatbot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un assistant médical informatif. Tu réponds en priorité à partir des documents médicaux officiels fournis.
S'il n'y a pas assez d'information dans les documents, tu peux utiliser le contexte web ci-dessous, en précisant que l'info vient du web et non des documents officiels.
IMPORTANT : Tu n'es pas un médecin. Tes réponses sont informatives uniquement et ne remplacent pas un avis médical.

Contexte médical extrait des documents officiels (HAS/INCa) :
{doc_context or "Aucun document pertinent trouvé."}

Contexte web (DuckDuckGo, à utiliser seulement si les documents ci-dessus sont insuffisants) :
{web_context or "Non utilisé."}

Historique de la conversation :
{history_text}

Question du patient : {question}

Réponse :"""

    return _call_llm(prompt), source
