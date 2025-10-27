# Użyj oficjalnego obrazu Python
FROM python:3.11-slim

# Ustaw zmienne środowiskowe
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Utwórz katalog roboczy
WORKDIR /app

# Skopiuj pliki requirements
COPY requirements.txt .

# Zainstaluj zależności systemowe i Python
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj resztę plików aplikacji
COPY . .

# Utwórz użytkownika nie-root
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Ustaw port dla Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Uruchom aplikację
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
