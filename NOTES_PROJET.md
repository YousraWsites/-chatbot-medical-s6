# SAE Chatbot LLM S6 — Notes projet

## Domaine choisi
**Médical** — chatbot patient-info (informatif uniquement, pas de diagnostic)

---

## A tester / comparer

### Encodeurs (Embeddings)
- Tester plusieurs encodeurs et comparer les résultats RAG
- Ex : `sentence-transformers/all-MiniLM-L6-v2`, `CamemBERT` (pour le français médical)

### LLMs à tester
- [ ] Mistral
- [ ] DeepSeek
- [ ] Ollama (local)
- Comparer qualité des réponses médicales + vitesse + coût

---

## Fonctionnalités obligatoires

### Auth & Sessions
- [ ] Créer un compte / Se connecter
- [ ] Gestion des sessions utilisateur
- [ ] Historique des conversations (par session)

### RAG
- [ ] Indexation de documents médicaux (PDF, fiches)
- [ ] Pipeline LangChain + ChromaDB
- [ ] Intégrer les méthodes du cours du prof

---

## Bonus

### DuckDuckGo Search
- Intégrer un moteur de recherche web (DuckDuckGo API) pour enrichir les réponses
- Utile quand la question dépasse la base documentaire

---

## Cours du prof (Mr FAYE & Mme AZZAG)

### Séance 2 — RNNs (base des modèles séquentiels)
- Les RNNs traitent des **données séquentielles** (texte, audio, séries temporelles)
- Chaque mot est représenté par un **vecteur** (one-hot ou embedding)
- Architecture : `h_t = a(W_h[x_t, h_{t-1}] + b_h)` — l'état caché = mémoire du modèle
- Types : Many-to-One (analyse sentiment), Many-to-Many (traduction), One-to-Many (génération)
- Problèmes : **vanishing gradient** sur longues séquences
- Keras : input shape = `(nb_exemples, nb_timestamps, nb_features)`
- Couche `Embedding` : chaque mot → vecteur dense, nb params = `taille_vocab × dim_embedding`

### Séance 3 — LSTM & GRU (solutions aux limites des RNNs)
- **LSTM** : 2 mémoires (état caché `h` + état cellule `C`), 3 portes (forget, input, output)
- **GRU** : version simplifiée, moins de paramètres, plus rapide
- Utiles pour capturer des **dépendances longues** dans le texte médical

### Séance 4 — Architecture Transformer (base des LLMs modernes)
- **Embedding** : convertit tokens → vecteurs denses dans un espace continu
  - Capture les relations sémantiques entre mots
  - Appris pendant l'entraînement
- **Positional Encoding** : ajoute l'info de position au vecteur d'embedding
  - Formule : `PE(pos, 2i) = sin(pos / 10000^(2i/d_model))`
- **Self-Attention** : matrices Q (query), K (key), V (value) dérivées de l'entrée X
  - Permet à chaque token de "regarder" tous les autres tokens
- **Multi-Head Self-Attention** : plusieurs têtes d'attention en parallèle → richer representations
- **Layer Normalization + Residual Connections** : stabilise l'entraînement, résout vanishing gradient
- **Feed Forward Networks** : transformation non-linéaire position par position
- **Cross-Attention** : interaction encoder ↔ decoder (utile pour seq2seq)
- **Masked Self-Attention** : empêche le modèle de "voir" les tokens futurs pendant l'entraînement
- Hugging Face `pipeline` : interface simple pour utiliser des transformers pré-entraînés

### Ce que ça implique pour notre projet RAG
- Le **texte médical** sera tokenisé puis converti en **embeddings** (vecteurs)
- L'encodeur (ex: `sentence-transformers`) produit ces embeddings pour l'indexation
- **Tester plusieurs encodeurs** : différentes dimensions, différentes qualités sémantiques
- La similarité cosinus entre embeddings = moteur de recherche du RAG
- Le LLM (Mistral/DeepSeek) est lui-même un Transformer avec self-attention

---

## Stack retenue
| Partie | Techno |
|---|---|
| Frontend | React JS |
| Backend | FastAPI |
| LLM | Mistral / DeepSeek / Ollama (à comparer) |
| RAG | LangChain + ChromaDB |
| DB | SQLAlchemy + SQLite |
| Déploiement | Render ou Railway |
