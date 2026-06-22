# Déploiement — sae.amanawebagency.com

> Procédure de mise en prod du chatbot médical sur le serveur Amana corporate.
> Setup réalisé le 2026-06-22 par Yannis. Cible : présentation SAE BUT3.

## URL de production

**https://sae.amanawebagency.com**

- Stack déployée : 2 containers Docker derrière Caddy reverse proxy (Let's Encrypt automatique)
- Serveur : `amana-prod-01` (Hostinger, alias SSH `amana`)
- LLM en prod : **Google Gemini 2.5 Flash** (mutualise la clé du chatbot Amana)
- LLM en dev local : OpenRouter / Mistral (config par défaut du code, voir `.env.example`)

## Architecture

```
sae.amanawebagency.com  ──→  Caddy (reverse proxy + Let's Encrypt + CSP)
                              │  /srv/amana/caddy/Caddyfile
                              ▼
                       amana-sae-web  (Streamlit, port 8501)
                              │  réseau Docker interne amana-net
                              │  API_URL=http://amana-sae-api:8000
                              ▼
                       amana-sae-api  (FastAPI + LangChain + Gemini)
                              │  volume Docker amana-sae-data
                              ▼
                          /app/data/
                          ├── chroma_db/    (vector store persistant)
                          └── chatbot.db    (SQLite users + sessions)
```

L'API n'est **pas exposée publiquement** — accessible uniquement via le frontend Streamlit sur le réseau Docker `amana-net`.

## Variables d'environnement

Voir `.env.example`. Sur le serveur, le `.env` est dans `/srv/amana/sae/.env` (mode 600, owner root).

| Variable | En prod (sae.amanawebagency.com) | En dev local (Yousra) |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `openrouter` (défaut) |
| `GEMINI_API_KEY` | clé Google AI Studio | non utilisé |
| `GEMINI_MODEL` | `gemini-2.5-flash` | non utilisé |
| `OPENROUTER_API_KEY` | vide | clé `sk-or-v1-...` |
| `OPENROUTER_MODEL` | (défaut) | `mistralai/mistral-small-3.2-24b-instruct` |
| `SECRET_KEY` | généré via `openssl rand -hex 32` | au choix |
| `CHROMA_DIR` | `/app/data/chroma_db` | `./chroma_db` (défaut) |
| `DATABASE_URL` | `sqlite:////app/data/chatbot.db` | `sqlite:///./chatbot.db` (défaut) |
| `DOCS_DIR` | `/app/documents` | `./documents` (défaut) |

Le code reste **compatible local** : sans variable env, il garde le comportement original de Yousra (OpenRouter + paths relatifs).

## Procédure de déploiement initial (référence)

> Toutes les commandes sont à exécuter depuis ta machine de dev, l'alias SSH `amana` route vers le serveur.

### 1. Pousser le code sur le serveur

```bash
rsync -avz --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='chroma_db/' --exclude='chatbot.db' --exclude='.env' \
  /chemin/local/-chatbot-medical-s6/ amana:/tmp/sae-deploy/

ssh amana 'sudo mkdir -p /srv/amana/sae && \
           sudo rsync -a --delete /tmp/sae-deploy/ /srv/amana/sae/ && \
           sudo chown -R yannis:yannis /srv/amana/sae && \
           rm -rf /tmp/sae-deploy'
```

### 2. Créer le `.env` (secrets)

```bash
ssh amana 'sudo bash -c "cat > /srv/amana/sae/.env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

LLM_PROVIDER=gemini
GEMINI_API_KEY=<récupérer depuis /srv/amana/chatbot/.env ou Google AI Studio>
GEMINI_MODEL=gemini-2.5-flash

OPENROUTER_API_KEY=
OPENROUTER_MODEL=mistralai/mistral-small-3.2-24b-instruct
EOF
chown root:root /srv/amana/sae/.env && chmod 600 /srv/amana/sae/.env"'
```

### 3. Build + run les containers

```bash
ssh amana 'cd /srv/amana/sae && \
           sudo docker compose -f docker-compose.prod.yml build && \
           sudo docker compose -f docker-compose.prod.yml up -d'
```

Le build prend ~7-8 min la première fois (pip install + pre-download du modèle MiniLM).

Au démarrage, l'API exécute `build_vectorstore()` qui parcourt `backend/documents/*.pdf` et indexe ~971 chunks dans Chroma. Compte ~1-2 min avant que l'API soit fonctionnelle (le healthcheck a `start_period: 180s`).

### 4. Ajouter le vhost Caddy

```bash
ssh amana 'sudo cp /srv/amana/caddy/Caddyfile /srv/amana/caddy/Caddyfile.bak-$(date +%F)
           sudo bash -c "cat /srv/amana/sae/deploy/caddy-sae.amanawebagency.com.caddy >> /srv/amana/caddy/Caddyfile"
           sudo docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
           sudo docker kill --signal=USR1 caddy'
```

Caddy obtient le cert Let's Encrypt automatiquement (compte ~10s la première fois).

### 5. Vérifications

```bash
# Status containers
ssh amana 'sudo docker ps --filter "name=amana-sae"'

# Headers de sécurité
curl -skI https://sae.amanawebagency.com/ | grep -iE "csp|hsts|x-frame|x-content"

# Test E2E (depuis le container API)
ssh amana 'sudo docker exec amana-sae-api curl -sS http://localhost:8000/'
# → {"message":"Chatbot Médical API is running"}
```

## Mise à jour du code après modification

```bash
# 1. Rsync les nouveaux fichiers
rsync -avz --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='chroma_db/' --exclude='chatbot.db' --exclude='.env' \
  /chemin/local/ amana:/tmp/sae-deploy/

ssh amana 'sudo rsync -a --delete \
            --exclude=".env" \
            /tmp/sae-deploy/ /srv/amana/sae/ && \
           rm -rf /tmp/sae-deploy'

# 2. Rebuild + redeploy
ssh amana 'cd /srv/amana/sae && \
           sudo docker compose -f docker-compose.prod.yml up -d --build'
```

## Ré-indexer le corpus (si on ajoute des PDFs)

Le code réindexe automatiquement au démarrage **si le dossier `/app/data/chroma_db` est vide**. Pour forcer une réindexation :

```bash
ssh amana 'sudo docker exec amana-sae-api rm -rf /app/data/chroma_db && \
           sudo docker restart amana-sae-api'
```

Compte ~1-2 min pour l'indexation des 5 PDFs HAS/INCa actuels.

## Logs & debugging

```bash
# Logs API en temps réel
ssh amana 'sudo docker logs -f amana-sae-api'

# Logs frontend Streamlit
ssh amana 'sudo docker logs -f amana-sae-web'

# Logs Caddy spécifiques au vhost
ssh amana 'sudo tail -f /var/log/caddy/sae.amanawebagency.com.log'

# Vérifier les ressources
ssh amana 'sudo docker stats amana-sae-api amana-sae-web --no-stream'
```

## Rollback

```bash
ssh amana 'cd /srv/amana/sae && sudo docker compose -f docker-compose.prod.yml down'

# Retirer le vhost Caddy (restaurer le backup créé à l'étape 4)
ssh amana 'sudo cp /srv/amana/caddy/Caddyfile.bak-YYYY-MM-DD /srv/amana/caddy/Caddyfile && \
           sudo docker kill --signal=USR1 caddy'
```

Les données utilisateur (SQLite + Chroma) restent dans le volume Docker `sae_amana-sae-data` — survit à un `down`, perdues uniquement avec `down -v` (à éviter).

## Hardening appliqué (skill `amana-server-hardening`)

- ✅ Containers en `no-new-privileges`, `cap_drop: ALL`, `pids_limit: 200`, `mem_limit`
- ✅ Healthchecks sur les 2 containers
- ✅ Logging json-file rotation 10MB × 3
- ✅ Réseau Docker isolé `amana-net` (external)
- ✅ Volume persistant nommé pour data
- ✅ `.env` mode 600 owner root, jamais commit
- ✅ Caddy reverse proxy avec Let's Encrypt auto
- ✅ Headers sécurité : HSTS, X-Content-Type-Options, Referrer-Policy, CSP, Permissions-Policy
- ✅ CSP adaptée à Streamlit (autorise `unsafe-eval` pour les workers React + WebSocket pour rerun)
- ✅ API interne uniquement (pas de port exposé hors `amana-net`)

## Limites connues

- **SQLite SQLite** : les comptes utilisateurs créés en prod survivent aux restarts (volume Docker persistant), mais ne survivent pas à un `down -v`. Pour la SAE c'est acceptable.
- **Pas de rate limit** côté FastAPI (slowapi non configuré). À ajouter si exposition à des trolls.
- **CORS `*`** dans le code de Yousra — sans danger actuellement car l'API n'est pas exposée publiquement, mais à durcir si on l'expose.
- **Cold start ML** : la 1ère requête après un restart du backend re-charge le modèle MiniLM en RAM (~5s), puis tout est cache hit.

## Alternative : déploiement Render + Streamlit Cloud

Le fichier `render.yaml` à la racine du repo est conservé pour le déploiement original prévu par Yousra (Render gratuit + Streamlit Cloud). Si tu veux re-déployer ailleurs sans dépendre de l'infra Amana, c'est la procédure de secours — voir section "Déploiement" de `NOTES_PROJET.md`.

Différence principale : sur Render, la SQLite et Chroma sont effacés à chaque cold start (disque éphémère du free tier), alors que sur amana-prod-01 ils sont persistants.
