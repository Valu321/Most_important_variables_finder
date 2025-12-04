FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Instalacja zależności systemowych dla PyCaret (libgomp1 jest krytyczny)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Instalacja bibliotek Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]