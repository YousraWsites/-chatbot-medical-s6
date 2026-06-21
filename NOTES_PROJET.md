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
| Frontend | Streamlit (plus rapide que React pour la deadline) |
| Backend | FastAPI |
| LLM | OpenRouter → `mistralai/mistral-small-3.2-24b-instruct` |
| RAG | LangChain + ChromaDB |
| DB | SQLAlchemy + SQLite |
| Déploiement | Render + Streamlit Cloud |

---

## Pourquoi on utilise un LLM "tout fait" (Mistral, Gemini...) ?

La SAE ne demande PAS de créer un LLM from scratch — c'est impossible en BUT 3.
Le vrai travail demandé c'est **intégrer et orchestrer** :
- Le pipeline **RAG** : découper les docs, les encoder en vecteurs, stocker dans ChromaDB, faire la recherche sémantique
- Le **backend** : auth, sessions, historique
- Le **frontend** : interface de chat
- Le **prompt engineering** : comment formuler la question pour avoir une bonne réponse médicale
- La **comparaison des encodeurs** : quel modèle d'embedding donne les meilleurs résultats
- La **comparaison des LLMs** : Mistral vs DeepSeek, lequel répond mieux sur des questions médicales

> Analogie : c'est comme construire une voiture. Tu n'inventes pas le moteur (= le LLM),
> mais tu construis tout autour : châssis, direction, freins, tableau de bord.
> Le prof le sait — il a mis "HuggingFace, OpenRouter, Gemini" dans le sujet exprès.

---

## LLMs testés et pourquoi

### Gemini (google.generativeai) — ABANDONNÉ
- **Problème 1** : package `google.generativeai` déprécié → migrer vers `google.genai`
- **Problème 2** : quota free tier épuisé (limite 0 requêtes sur `gemini-2.0-flash` et `gemini-1.5-flash`)
- **Raison** : la clé a été créée sur un projet Google sans quota free tier suffisant

### OpenRouter — RETENU ✅
- Plateforme qui agrège plusieurs LLMs (Mistral, DeepSeek, LLaMA...)
- Nouveau compte = crédit gratuit sans carte bancaire
- Avantage SAE : changer de modèle = changer juste une ligne de code
- Modèles `:free` testés : tous indisponibles fin juin 2026
- **Modèle retenu** : `mistralai/mistral-small-3.2-24b-instruct` (fonctionne avec le crédit offert)
- Réponse testée sur "c'est quoi le diabète ?" → réponse cohérente et complète ✅

### Bugs rencontrés et solutions
| Bug | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: langchain.text_splitter` | LangChain a déplacé le module | `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| `ValueError: password cannot be longer than 72 bytes` | Conflit passlib/bcrypt | Remplacer passlib par `import bcrypt` directement |
| `500 Internal Server Error` sur /chat | ChromaDB vide au démarrage | Try/except si `chroma_db/` n'existe pas encore |
| `google.genai 404 NOT_FOUND` | Mauvais nom de modèle | Utiliser OpenRouter à la place |

---

## Documents médicaux indexés (sources officielles)

| Fichier | Source | URL | Sujet |
|---|---|---|---|
| `diabete_type2_HAS.pdf` | Haute Autorité de Santé | has-sante.fr | Stratégie thérapeutique diabète type 2 |
| `diabete_parcours_soins_HAS.pdf` | Haute Autorité de Santé | has-sante.fr | Parcours de soins diabète adulte |
| `alzheimer_HAS.pdf` | Haute Autorité de Santé | has-sante.fr | Parcours de soins troubles neurocognitifs/Alzheimer |
| `alzheimer_essentiel_HAS.pdf` | Haute Autorité de Santé | has-sante.fr | L'essentiel Alzheimer (4 pages synthèse) |
| `cancer_poumon_ecancer.pdf` | INCa (Institut National du Cancer) | e-cancer.fr | Traitements des cancers du poumon |

**Pourquoi ces sources ?**
- HAS (Haute Autorité de Santé) = référence officielle française pour les recommandations médicales
- INCa = référence nationale pour les cancers
- Toutes les sources sont publiques, gratuites, fiables et en français

**Pourquoi 3 maladies / 5 docs pour commencer ?**
- Pour la SAE : on n'a pas besoin de 50 docs. Le but est de **montrer que le RAG fonctionne** sur un périmètre maîtrisé
- Diabète + Alzheimer + Cancer poumon = 3 domaines médicaux différents (métabolique, neurologique, oncologique) → montre que le système est généraliste
- 2 docs sur le diabète car c'est une maladie complexe avec beaucoup d'info → meilleure démonstration du RAG
- On peut **ajouter des docs facilement** plus tard sans changer une ligne de code (c'est la force du RAG)

---

## C'est quoi le RAG ?

**RAG = Retrieval-Augmented Generation**

Sans RAG :
> Question → LLM → Réponse (depuis la mémoire générale du modèle, peut halluciner)

Avec RAG :
> Question → **Recherche dans nos docs** → Contexte pertinent + Question → LLM → Réponse **basée sur nos documents**

**Comment ça marche concrètement :**
1. **Indexation** (une seule fois) : les PDFs sont découpés en petits morceaux (chunks), chaque chunk est converti en vecteur (embedding) et stocké dans ChromaDB
2. **À chaque question** : la question est aussi convertie en vecteur, on cherche les chunks les plus proches (similarité cosinus), on les envoie au LLM comme contexte
3. **Le LLM répond** en se basant sur ces chunks → réponses plus précises, moins d'hallucinations

**Analogie prof :** c'est exactement ce que le cours appelle "Retrieval" — utiliser les embeddings (Séance 4) pour faire de la recherche sémantique dans une base vectorielle

---

## Pipeline RAG — Étapes détaillées

### Étape 1 — Chargement des PDFs
```python
PyPDFLoader("diabete_type2_HAS.pdf")
```
LangChain lit chaque page du PDF et extrait le texte brut.

### Étape 2 — Découpage en chunks
```python
RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
```
Le texte entier est trop grand pour un LLM → on le découpe en **petits morceaux de 500 caractères**.

`chunk_overlap=50` → les 50 derniers caractères d'un chunk sont répétés au début du suivant.
**Pourquoi ?** Pour ne pas couper une phrase en plein milieu et perdre le contexte entre deux chunks.

Exemple :
```
[...Le diabète de type 2 est caractérisé par une résistance à l'insuline...]
         chunk 1 (500 chars)          |overlap 50| chunk 2 (500 chars)
```

### Étape 3 — Encodage en vecteurs (Embeddings)
```python
HuggingFaceEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
```
Chaque chunk est transformé en un **vecteur de 384 nombres**.
C'est ce que le prof explique en Séance 4 — l'embedding capture le **sens sémantique** du texte.

Exemple :
```
"diabète résistance insuline" → [0.23, -0.41, 0.87, ..., 0.12]  ← 384 dimensions
"hyperglycémie glucose sang"  → [0.21, -0.38, 0.91, ..., 0.09]  ← très proche !
"recette de cuisine"          → [-0.54, 0.22, -0.33, ..., 0.67] ← très loin
```
La proximité entre vecteurs = similarité de sens (similarité cosinus).

### Étape 4 — Stockage dans ChromaDB
```python
Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
```
Tous les vecteurs sont stockés dans **ChromaDB** (base de données vectorielle).
Différence avec une BDD classique : on ne cherche pas par ID mais par **similarité de vecteurs**.

### Étape 5 — Recherche à chaque question (RAG en action)
```python
vectorstore.similarity_search(question, k=4)
```
1. La question de l'utilisateur est encodée en vecteur (même modèle d'embedding)
2. ChromaDB trouve les **4 chunks les plus proches** (similarité cosinus)
3. Ces 4 chunks sont envoyés au LLM comme **contexte**
4. Le LLM génère une réponse basée sur ces extraits de nos documents officiels

**Résultat :** réponses précises, traçables, basées sur HAS/INCa → moins d'hallucinations

---

## Comparaison des encodeurs (21 juin 2026)

Script : `backend/compare_encoders.py` — indexe les 5 PDFs avec 2 encodeurs différents
dans des ChromaDB séparés (`backend/chroma_compare/`), puis lance 4 questions médicales
de test et compare les chunks récupérés. Résultats complets : `backend/comparaison_encodeurs_resultats.txt`.

| Encodeur | Dimensions | Spécialité |
|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` (actuel) | 384 | généraliste multilingue |
| `dangvantuan/sentence-camembert-base` | 768 | français spécialisé |

**Constat :**
- Les scores des deux modèles ne sont pas comparables directement (échelles différentes selon la dimension d'embedding), mais dans les deux cas plus le score est bas, plus le chunk est pertinent.
- Sur les 4 questions testées, les deux encodeurs retrouvent bien le bon document source (diabète → bon PDF diabète, Alzheimer → bon PDF Alzheimer, etc.) — le RAG fonctionne avec les deux.
- Différence qualitative : sur la question Alzheimer, `all-MiniLM-L6-v2` remonte en 1er résultat une **référence bibliographique** (bruit, peu utile), alors que `sentence-camembert-base` remonte directement un passage de présentation de la maladie (plus pertinent). CamemBERT, entraîné spécifiquement sur du français, semble mieux capter le sens des phrases médicales françaises et moins se laisser distraire par du texte non sémantique (citations, numéros de page).
- Inconvénient CamemBERT : modèle plus lourd (768 dim vs 384) → indexation ~4x plus longue (270s vs 71s sur nos 971 chunks) et embeddings plus volumineux à stocker.

**Décision :** garder `all-MiniLM-L6-v2` en prod pour la rapidité (le projet est en français mais les écarts de pertinence restent mineurs), mais documenter `sentence-camembert-base` comme alternative testée et plus précise sur le français — répond à l'exigence "tester plusieurs encodeurs et comparer".

---

## État avancé (21 juin 2026)
- [x] Structure projet créée
- [x] Repo GitHub : https://github.com/YousraWsites/-chatbot-medical-s6
- [x] Backend FastAPI opérationnel
- [x] Auth JWT (register/login)
- [x] Sessions + historique en base
- [x] Frontend Streamlit opérationnel
- [x] LLM connecté (OpenRouter/Mistral) → chatbot répond ✅
- [x] Documents médicaux ajoutés dans `backend/documents/` (5 PDFs HAS/INCa)
- [x] Indexation ChromaDB (RAG actif) — 971 chunks indexés
- [x] Comparaison encodeurs (MiniLM vs CamemBERT, voir ci-dessus)
- [x] Préparation déploiement (Render + Streamlit Cloud) — voir ci-dessous, reste à faire les étapes manuelles sur les dashboards
- [x] Bonus DuckDuckGo (recherche web, voir ci-dessous)

---

## Bonus DuckDuckGo — recherche web (21 juin 2026)

**Objectif :** enrichir les réponses quand la question dépasse la base documentaire (les 3 maladies indexées : diabète, Alzheimer, cancer du poumon).

**Implémentation** (`backend/app/services/rag.py`) :
- Librairie : `ddgs` (fork maintenu de `duckduckgo-search`)
- À chaque question, on calcule le score de similarité (distance L2) des chunks ChromaDB les plus proches
- Seuil `RELEVANCE_THRESHOLD = 0.9` : si le meilleur score dépasse ce seuil (= aucun chunk vraiment pertinent), on déclenche `web_search()` qui interroge DuckDuckGo et injecte les résultats dans le prompt, avec leurs sources (titre + URL)
- Le prompt précise au LLM de prioriser les documents officiels (HAS/INCa) et de n'utiliser le web qu'en complément, en le signalant explicitement dans sa réponse

**Tests faits :**
- Question hors périmètre ("symptômes de la grippe", score min ≈ 0.99 > seuil) → web search déclenché, réponse basée sur ameli.fr / Institut Pasteur, sources citées ✅
- Question dans le périmètre ("traitements du diabète de type 2", score min ≈ 0.38 < seuil) → pas de recherche web, réponse basée uniquement sur les PDFs HAS, sources citées ✅

**Pourquoi un seuil de score plutôt que "toujours chercher sur le web" ?**
Pour rester cohérent avec l'objectif du projet (réponses traçables basées sur des sources médicales officielles) : le web n'est qu'un filet de sécurité quand la base documentaire ne couvre pas le sujet, pas une source par défaut.

---

## Déploiement — préparation (21 juin 2026)

**Problème identifié :** `chroma_db/` est dans `.gitignore` (régénéré en local). Sur Render,
le disque du tier gratuit est éphémère (vidé à chaque redéploiement/redémarrage) →
le backend doit pouvoir se ré-indexer seul au démarrage.

**Changements faits :**
- `backend/main.py` : événement `startup` qui appelle `build_vectorstore()` si `chroma_db/` n'existe pas
- `backend/app/services/rag.py` : retrait de l'appel `.persist()` déprécié (Chroma persiste automatiquement)
- `frontend/app.py` : `API_URL` lu depuis `st.secrets["API_URL"]` (Streamlit Cloud) avec fallback `os.getenv("API_URL")` puis `http://localhost:8000` en local
- `frontend/requirements.txt` créé (streamlit, requests)
- `render.yaml` créé à la racine du repo (Infrastructure as Code pour Render)

**Étapes manuelles restantes (dashboards) :**

1. **Render (backend)**
   - Créer un compte sur render.com, connecter le repo GitHub `-chatbot-medical-s6`
   - "New +" → "Blueprint" → Render détecte `render.yaml` automatiquement
   - Renseigner les secrets demandés : `SECRET_KEY` (générer une valeur aléatoire), `OPENROUTER_API_KEY` (celle du `.env` local)
   - Noter l'URL générée par Render (ex: `https://chatbot-medical-api.onrender.com`)
   - ⚠️ Limite tier gratuit : le service "s'endort" après inactivité → 1er appel après veille peut être lent (cold start + ré-indexation ChromaDB), et `chatbot.db` (SQLite) est aussi effacé à chaque redéploiement → comptes/historique perdus. Acceptable pour une démo SAE, à mentionner à l'oral si besoin.

2. **Streamlit Cloud (frontend)**
   - Créer un compte sur share.streamlit.io, connecter le même repo
   - "New app" → main file path : `frontend/app.py`
   - Dans "Advanced settings" → "Secrets", ajouter :
     ```
     API_URL = "https://chatbot-medical-api.onrender.com"
     ```
     (remplacer par l'URL réelle notée à l'étape 1)
   - Déployer

3. **Vérifier** : créer un compte sur le site déployé, lancer une conversation, vérifier que le RAG répond bien avec du contexte médical.
