FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

# STREAMLIT_BASE_URL_PATH peut être défini (ex: "app") pour servir Streamlit sous /app/
# en prod derrière Caddy, tout en gardant un serveur local à la racine pour Yousra.
ENV STREAMLIT_BASE_URL_PATH=""

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8501/${STREAMLIT_BASE_URL_PATH}/_stcore/health || \
        curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["sh", "-c", "streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true \
    --server.baseUrlPath=${STREAMLIT_BASE_URL_PATH} \
    --browser.gatherUsageStats=false"]
