"""
Comparaison de 2 encodeurs (embeddings) pour le RAG médical.

- all-MiniLM-L6-v2          : généraliste, anglais/multilingue léger, 384 dim
- dangvantuan/sentence-camembert-base : spécialisé français, 768 dim

Pour chaque encodeur :
1. on indexe les 5 PDFs dans un ChromaDB séparé (./chroma_compare/<nom_modele>)
2. on lance les mêmes questions de test
3. on affiche les chunks récupérés + leur score de similarité

Lancer : python compare_encoders.py
"""
import os
import shutil
import time

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

DOCS_DIR = "./documents"
COMPARE_DIR = "./chroma_compare"

ENCODERS = {
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-camembert-base": "dangvantuan/sentence-camembert-base",
}

TEST_QUESTIONS = [
    "Quels sont les traitements du diabète de type 2 ?",
    "Quels sont les premiers signes de la maladie d'Alzheimer ?",
    "Quelles sont les options de traitement du cancer du poumon ?",
    "Comment se déroule le parcours de soins d'un patient diabétique ?",
]


def load_and_split_docs():
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for fname in sorted(os.listdir(DOCS_DIR)):
        if fname.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(DOCS_DIR, fname))
            pages = loader.load()
            docs.extend(splitter.split_documents(pages))
    return docs


def sanitize(text: str) -> str:
    """Retire les caractères hors de la table d'impression console Windows (cp1252)."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


def build_vectorstore_for(model_name: str, persist_dir: str, docs, force_rebuild: bool):
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    if os.path.exists(persist_dir) and not force_rebuild:
        return Chroma(persist_directory=persist_dir, embedding_function=embeddings), 0.0
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
    t0 = time.time()
    vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=persist_dir)
    elapsed = time.time() - t0
    return vectorstore, elapsed


def run_comparison(force_rebuild: bool = False):
    docs = load_and_split_docs()
    print(f"{len(docs)} chunks a indexer pour chaque encodeur\n")

    out_lines = []
    results = {}
    for label, model_name in ENCODERS.items():
        persist_dir = os.path.join(COMPARE_DIR, label)
        print(f"=== {label} ({model_name}) ===")
        vectorstore, elapsed = build_vectorstore_for(model_name, persist_dir, docs, force_rebuild)
        msg = f"Pret en {elapsed:.1f}s" if elapsed else "Charge depuis le cache"
        print(msg + "\n")
        results[label] = vectorstore

    for question in TEST_QUESTIONS:
        header = f"\n{'='*80}\nQUESTION : {question}\n{'='*80}"
        print(header)
        out_lines.append(header)
        for label, vectorstore in results.items():
            sub = f"\n--- {label} ---"
            print(sub)
            out_lines.append(sub)
            hits = vectorstore.similarity_search_with_score(question, k=3)
            for i, (doc, score) in enumerate(hits, 1):
                source = os.path.basename(doc.metadata.get("source", "?"))
                preview = doc.page_content.replace("\n", " ")[:150]
                line1 = f"  [{i}] score={score:.4f} source={source}"
                line2 = f"      {preview}..."
                print(sanitize(line1))
                print(sanitize(line2))
                out_lines.append(line1)
                out_lines.append(line2)

    with open("comparaison_encodeurs_resultats.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print("\nResultats complets ecrits dans comparaison_encodeurs_resultats.txt")


if __name__ == "__main__":
    import sys
    run_comparison(force_rebuild="--rebuild" in sys.argv)
