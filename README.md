# 📊 Aplikacja do Analizy Ważności Cech (Feature Importance App)

Kompleksowe narzędzie AutoML oparte na Streamlit i PyCaret, które automatycznie analizuje dane, trenuje modele (Regresja/Klasyfikacja) i identyfikuje kluczowe cechy wpływające na wynik.

Aplikacja wykorzystuje model OpenAI (GPT-4o-mini) do generowania biznesowych opisów wyników oraz Langfuse do monitorowania jakości działania LLM.

---

## 🚀 Główne funkcjonalności

### 🧠 Inteligentna Analiza

- **Smart Preprocessing**: Automatyczna konwersja czasu (np. "MM:SS") na sekundy oraz inteligentne czyszczenie typów numerycznych
- **Safety Guard**: System automatycznie wykrywa problemy z danymi (np. zbyt wiele unikalnych klas w klasyfikacji) i bezpiecznie przełącza tryb na Regresję, aby uniknąć błędów
- **Auto-Detection**: Heurystyczne rozpoznawanie typu problemu (Klasyfikacja vs Regresja)
- **Auto-Delimiter Detection**: Automatyczne wykrywanie separatora w plikach CSV (przecinek, średnik, tabulator, pipe)

### 🛡️ Stabilność i Bezpieczeństwo

- **Memory Guard** 🆕: Wbudowany monitor pamięci RAM działający w tle, zapobiegający awariom (OOM Kill) na mniejszych instancjach chmurowych
- **RODO/GDPR**: Dane przetwarzane są wyłącznie w pamięci RAM (brak zapisu na dysku). Do AI wysyłane są tylko zanonimizowane nazwy kolumn i statystyki
- **File Size Limit**: Ochrona przed przeciążeniem - maksymalny rozmiar pliku 10MB

### 📈 Funkcje Biznesowe

- **Obsługa plików**: CSV oraz Excel (.xlsx)
- **Wizualizacja**: Interaktywne wykresy ważności cech (Plotly)
- **AI Reports**: Automatyczne raporty biznesowe generowane przez GPT-4o-mini

---

## 🛠️ Stos technologiczny

| Kategoria | Technologie |
|-----------|-------------|
| **Frontend** | Streamlit |
| **ML Core** | PyCaret, Scikit-learn, Pandas, NumPy |
| **System** | psutil (monitoring zasobów) |
| **AI/LLM** | OpenAI API (GPT-4o-mini) |
| **Observability** | Langfuse |
| **Infrastruktura** | Docker, DigitalOcean App Platform |

---

## 💻 Instalacja i uruchomienie lokalne

### 1. Wymagania

- **Python 3.10+** (Zalecane ze względu na kompatybilność PyCaret)
- **Klucz API OpenAI** (do generowania opisów)

### 2. Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/Valu321/Most_important_variables_finder.git
cd Most_important_variables_finder

# Utworzenie środowiska wirtualnego
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Instalacja zależności
pip install -r requirements.txt
```

### 3. Konfiguracja (.env)

Utwórz plik `.env` w głównym katalogu:

```env
OPENAI_API_KEY=sk-twoj-klucz-api
# Opcjonalnie dla Langfuse:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Uruchomienie

```bash
streamlit run app.py
```

Aplikacja dostępna pod adresem: `http://localhost:8501`

---

## 📖 Jak używać?

1. **Panel boczny**: Wgraj plik z danymi (CSV lub Excel)
2. **Konfiguracja**: Wybierz kolumnę docelową (Target), którą chcesz przewidywać
3. **Tryb**: Zostaw "Auto" lub wymuś typ problemu (Klasyfikacja/Regresja)
4. **Analiza**: Kliknij **"Rozpocznij Analizę"**
5. **Wyniki**: Obserwuj pasek postępu i zużycie pamięci. Po zakończeniu otrzymasz wykres i raport AI

---

## ☁️ Wdrożenie (Deployment)

Szczegółowe instrukcje dotyczące budowania obrazów Docker oraz wdrażania na platformy chmurowe (DigitalOcean App Platform) znajdują się w dedykowanym pliku:

👉 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

---

## 📂 Struktura projektu

```
.
├── app.py                  # Główna logika aplikacji (Streamlit + PyCaret)
├── app_copy.py             # Narzędzie diagnostyczne do testowania pamięci (Memory Leak Test)
├── requirements.txt        # Zależności Python
├── Dockerfile              # Konfiguracja obrazu Docker (zawiera libgomp1)
├── app.yaml                # Konfiguracja DigitalOcean App Platform
├── README.md               # Ten plik
└── DEPLOYMENT_GUIDE.md     # Instrukcja wdrożenia
```

---

## 🤝 Wsparcie

Jeśli napotkasz problemy:

- Sprawdź sekcję **Rozwiązywanie problemów** w [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- Upewnij się, że masz odpowiednią ilość pamięci RAM (min. 1GB, zalecane 2GB)
- Sprawdź logi aplikacji w przypadku błędów PyCaret/LightGBM
