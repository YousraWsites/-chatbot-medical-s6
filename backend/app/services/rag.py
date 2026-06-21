from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
import requests
import os

load_dotenv()

CHROMA_DIR = "./chroma_db"
DOCS_DIR = "./documents"

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

def get_rag_response(question: str, history: list) -> str:
    context = ""
    try:
        if os.path.exists(CHROMA_DIR):
            vectorstore = get_vectorstore()
            retriever = vectorstore.similarity_search(question, k=4)
            context = "\n\n".join([doc.page_content for doc in retriever])
    except Exception:
        context = ""

    history_text = ""
    for msg in history[-6:]:  # garder les 6 derniers messages
        role = "Patient" if msg["role"] == "user" else "Chatbot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un assistant médical informatif. Tu réponds uniquement à partir des documents médicaux fournis.
IMPORTANT : Tu n'es pas un médecin. Tes réponses sont informatives uniquement et ne remplacent pas un avis médical.

Contexte médical extrait des documents :
{context}

Historique de la conversation :
{history_text}

Question du patient : {question}

Réponse :"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        json={"model": "mistralai/mistral-small-3.2-24b-instruct", "messages": [{"role": "user", "content": prompt}]}
    )
    return response.json()["choices"][0]["message"]["content"]
