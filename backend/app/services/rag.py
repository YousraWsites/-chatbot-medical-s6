from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
    vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_DIR)
    vectorstore.persist()
    print(f"{len(docs)} chunks indexés dans ChromaDB")

def get_vectorstore():
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

def get_rag_response(question: str, history: list) -> str:
    vectorstore = get_vectorstore()
    retriever = vectorstore.similarity_search(question, k=4)
    context = "\n\n".join([doc.page_content for doc in retriever])

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

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text
