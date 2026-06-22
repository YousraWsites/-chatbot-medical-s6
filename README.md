# SAE BUT3 — Chatbot médical RAG

Chatbot médical informatif basé sur un pipeline RAG (Retrieval-Augmented Generation). Projet SAE BUT3 S6 (Mr FAYE & Mme AZZAG).

## Production

**URL : https://sae.amanawebagency.com**

Stack en prod : FastAPI + Streamlit + ChromaDB + Gemini 2.5 Flash, déployée sur le serveur Amana corporate.
Procédure complète : voir [`DEPLOY.md`](./DEPLOY.md).

## Stack

| Couche | Techno |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + SQLAlchemy |
| LLM | Google Gemini 2.5 Flash (prod) / OpenRouter Mistral (dev) |
| RAG | LangChain + ChromaDB |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (comparé avec CamemBERT + mpnet, voir `NOTES_PROJET.md`) |
| Recherche web (bonus) | DuckDuckGo (`ddgs`) — fallback automatique si retrieval insuffisant |
| Auth | JWT (PyJOSE + bcrypt) |
| DB | SQLite |
| Sources documentaires | HAS + INCa (Haute Autorité de Santé + Institut National du Cancer) |

## Lancement en local

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # remplir OPENROUTER_API_KEY (gratuit sur openrouter.ai)
uvicorn main:app --reload --port 8000

# Frontend (dans un autre terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Streamlit ouvre automatiquement http://localhost:8501.

## Variables d'environnement

Voir [`.env.example`](./.env.example). Au minimum :

- `SECRET_KEY`, `ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=60` (JWT auth)
- `LLM_PROVIDER=openrouter` (défaut, dev) ou `gemini` (prod)
- Selon `LLM_PROVIDER` : `OPENROUTER_API_KEY` ou `GEMINI_API_KEY`

## Documentation

- [`NOTES_PROJET.md`](./NOTES_PROJET.md) — décisions techniques, comparaison encodeurs, lien avec le cours, bonus DuckDuckGo
- [`SKILLS.md`](./SKILLS.md) — compétences couvertes par le projet (référentiel SAE)
- [`DEPLOY.md`](./DEPLOY.md) — déploiement complet sur sae.amanawebagency.com
- [`render.yaml`](./render.yaml) — alternative déploiement Render + Streamlit Cloud (originale)

## Domaine spécialisé

**Médical** (parmi les 7 domaines imposés par le sujet) — sous-spécialité patient-info :
- Diabète de type 2
- Maladie d'Alzheimer
- Cancer du poumon

Sources documentaires : 5 PDFs officiels (HAS, INCa), 971 chunks indexés. Toutes les réponses sont traçables.

> ⚠️ Le chatbot est **informatif uniquement** — il ne remplace pas un avis médical, et le rappelle dans chaque réponse.
