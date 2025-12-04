# 📊 Aplikacja do Analizy Ważności Cech (Feature Importance App)

Kompleksowe narzędzie AutoML oparte na Streamlit i PyCaret, które automatycznie analizuje dane, trenuje modele (Regresja/Klasyfikacja) i identyfikuje kluczowe cechy. Aplikacja wykorzystuje OpenAI (GPT-4o-mini) do generowania wniosków biznesowych oraz Langfuse do monitorowania LLM.

## 🚀 Funkcjonalności

- **AutoML**: Automatyczny wybór modelu (Random Forest, XGBoost, LightGBM) przy użyciu PyCaret
- **Inteligentna Analiza**: Wykrywanie typu problemu (Regresja vs Klasyfikacja)
- **AI Insights**: Opisy biznesowe generowane przez GPT-4o-mini
- **Monitoring**: Pełna obserwowalność kosztów i jakości dzięki Langfuse

## 🛠️ Struktura Projektu

```
.
├── app.py              # Główna logika aplikacji
├── app.yaml            # Konfiguracja DigitalOcean App Platform
├── Dockerfile          # Środowisko uruchomieniowe (naprawia zależności systemowe PyCaret)
├── requirements.txt    # Biblioteki Python
└── .env                # Zmienne środowiskowe (nie commitować!)
```

## ⚙️ Uruchomienie Lokalne

### Klonowanie i instalacja

```bash
git clone <twoje-repo>
cd feature-analysis-app
pip install -r requirements.txt
```

### Konfiguracja (.env)

Utwórz plik `.env`:

```env
OPENAI_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Start

```bash
streamlit run app.py
```

### Alternatywnie z Dockerem

```bash
docker build -t feature-app .
docker run -p 8501:8501 --env-file .env feature-app
```

## ☁️ Wdrożenie (DigitalOcean App Platform)

Aplikacja jest gotowa do wdrożenia "jednym kliknięciem" dzięki plikom `app.yaml` i `Dockerfile`.

### Krok 1: Przygotowanie

- Upewnij się, że masz konto na Langfuse i wygenerowane klucze API
- Upewnij się, że kod jest na GitHubie (bez pliku `.env`!)

### Krok 2: Utworzenie Aplikacji

1. W panelu DigitalOcean wybierz **Apps** → **Create App**
2. Wybierz **GitHub** i wskaż swoje repozytorium (branch `main`)
3. Platforma wykryje `Dockerfile` automatycznie

### Krok 3: Zasoby (Krytyczne!)

1. Kliknij **Edit Plan**
2. Wybierz plan **Basic S** (1GB RAM) lub wyższy ($12/miesiąc)

> ⚠️ **Ostrzeżenie**: Plan 512MB RAM nie wystarczy dla biblioteki PyCaret (spowoduje błąd Out of Memory).

### Krok 4: Zmienne Środowiskowe (Secrets)

W sekcji **Environment Variables** dodaj klucze i zaznacz **Encrypt**:

| Klucz                | Wartość                    |
|---------------------|----------------------------|
| `OPENAI_API_KEY`     | `sk-...`                   |
| `LANGFUSE_PUBLIC_KEY`| `pk-lf-...`                |
| `LANGFUSE_SECRET_KEY`| `sk-lf-...`                |
| `LANGFUSE_HOST`      | `https://cloud.langfuse.com`|
| `PORT`               | `8501`                     |

### Krok 5: Wdrożenie

Kliknij **Create Resources**. Budowanie potrwa kilka minut. Po zakończeniu otrzymasz publiczny link `https://...ondigitalocean.app`.

## 🤝 Wsparcie

W przypadku błędu **Health Check Timeout** podczas wdrożenia, zwiększ parametr `initial_delay_seconds` w ustawieniach komponentu w DigitalOcean.
