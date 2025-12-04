# 📊 Aplikacja do Analizy Ważności Cech (Feature Importance App)

Kompleksowe narzędzie AutoML oparte na Streamlit i PyCaret, które automatycznie analizuje dane, trenuje modele (Regresja/Klasyfikacja) i identyfikuje kluczowe cechy. Aplikacja wykorzystuje najnowszy model OpenAI (GPT-4o-mini) do generowania biznesowych opisów wyników oraz Langfuse do monitorowania działania LLM.

## 🚀 Funkcjonalności

- **Automatyczne wykrywanie problemu**: System sam rozpoznaje, czy dane wymagają modelu klasyfikacji czy regresji
- **AutoML (PyCaret)**: Trenuje i porównuje wiele modeli (Random Forest, XGBoost, LightGBM), wybierając najlepszy
- **Wizualizacja**: Interaktywne wykresy ważności cech przy użyciu Plotly
- **AI Insights**: Automatyczne generowanie opisów biznesowych i wniosków przez integrację z OpenAI API (model GPT-4o-mini)
- **Monitoring (Observability)**: Śledzenie kosztów i jakości zapytań do LLM dzięki integracji z Langfuse

## 🛠️ Stos technologiczny

- **Frontend**: Streamlit
- **ML Core**: PyCaret, Scikit-learn, Pandas
- **LLM**: OpenAI API (GPT-4o-mini)
- **Observability**: Langfuse
- **Deployment**: Docker, DigitalOcean App Platform

## ⚙️ Instalacja i uruchomienie lokalne

### Wymagania wstępne

- Python 3.10 lub nowszy (zalecane ze względu na stabilność PyCaret)
- Klucz API OpenAI (wymagany do generowania opisów)

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/Valu321/Most_important_variables_finder.git
cd Most_important_variables_finder
```

### 2. Utworzenie środowiska wirtualnego (zalecane)

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 4. Konfiguracja zmiennych środowiskowych

Utwórz plik `.env` na podstawie wzoru (lub skopiuj poniższe):

```env
OPENAI_API_KEY=sk-twoj-klucz-api
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 5. Uruchomienie aplikacji

```bash
streamlit run app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8501`

## 🐳 Uruchomienie z Dockerem

Aplikacja posiada gotową konfigurację Docker, co jest zalecane ze względu na złożoność zależności PyCaret.

**Zbuduj obraz:**

```bash
docker build -t feature-app .
```

**Uruchom kontener:**

```bash
docker run -p 8501:8501 --env-file .env feature-app
```

## ☁️ Wdrożenie (DigitalOcean App Platform)

Projekt jest skonfigurowany do automatycznego wdrożenia na DigitalOcean App Platform przy użyciu pliku `app.yaml` i `Dockerfile`.

1. Utwórz aplikację w panelu DigitalOcean wybierając źródło GitHub
2. Platforma powinna automatycznie wykryć plik `Dockerfile` (zdefiniowane w `app.yaml`)
3. **Ważne**: Wybierz plan **Basic S** (1GB RAM) lub wyższy. Plan 512MB jest niewystarczający dla PyCaret
4. Dodaj klucze API (`OPENAI_API_KEY` itd.) w sekcji **Environment Variables** jako **Secrets**

Szczegółowe instrukcje wdrożenia znajdziesz w pliku `DEPLOYMENT_GUIDE.md`.

## 📂 Struktura projektu

```
.
├── app.py                      # Główny plik aplikacji Streamlit
├── app.yaml                    # Konfiguracja wdrożenia DigitalOcean App Platform
├── Dockerfile                  # Konfiguracja obrazu Docker
├── requirements.txt            # Zależności Python
├── .env                        # Zmienne środowiskowe (nie commitować!)
├── .gitignore                  # Pliki ignorowane przez Git
├── .dockerignore               # Pliki ignorowane przez Docker (build context)
└── DEPLOYMENT_GUIDE.md         # Instrukcja wdrożenia
```

## 🤝 Wsparcie

Jeśli napotkasz problemy z instalacją PyCaret, upewnij się, że masz zainstalowane biblioteki systemowe (np. `libgomp1` na Linuxie - jest to obsłużone w dołączonym `Dockerfile`).
