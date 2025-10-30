# 📊 Aplikacja do znajdowania najważniejszych cech w zbiorze danych

Aplikacja Streamlit do automatycznej analizy ważności cech w zbiorach danych CSV. System automatycznie rozpoznaje typ problemu (klasyfikacja/regresja), buduje najlepszy model i wyświetla najważniejsze cechy wpływające na zmienną docelową.

## 🚀 Szybkie wdrożenie

### DigitalOcean App Platform (ZALECANE - najprostsze)
Zobacz: [DEPLOYMENT_APP_PLATFORM.md](DEPLOYMENT_APP_PLATFORM.md) - kompletna instrukcja wdrożenia na App Platform.

### DigitalOcean Droplet (zaawansowane)
Zobacz: [DEPLOYMENT.md](DEPLOYMENT.md) - instrukcja wdrożenia na serwerze Droplet z Dockerem.

## 🚀 Funkcjonalności

- **Wczytywanie danych CSV** - intuicyjny interfejs do wczytywania plików
- **Automatyczne rozpoznawanie typu problemu** - klasyfikacja vs regresja
- **Budowa najlepszego modelu** - wykorzystanie PyCaret do automatycznego wyboru modelu
- **Analiza ważności cech** - ranking najważniejszych zmiennych
- **Wizualizacja wyników** - interaktywne wykresy i tabele
- **Opis słowny przez ChatGPT** - automatyczne generowanie wniosków i rekomendacji przez AI

## 📋 Wymagania

- Python 3.8+
- Conda (zalecane) lub pip

## 🛠️ Instalacja

### Opcja 1: Conda (zalecana)

```bash
# Aktywuj środowisko conda
conda activate od_zera_do_ai

# Dodaj kanał conda-forge
conda config --append channels conda-forge

# Zainstaluj Streamlit
conda install -y streamlit

# Zainstaluj PyCaret z wszystkimi zależnościami
conda install -y 'pycaret[full]'

# Zainstaluj pozostałe biblioteki
pip install plotly openai python-dotenv
```

### Opcja 2: Pip

```bash
# Zainstaluj wszystkie zależności
pip install -r requirements.txt
```

## 🏃‍♂️ Uruchomienie

```bash
# Uruchom aplikację
streamlit run app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8501`

## 🔑 Konfiguracja OpenAI API

Aby korzystać z automatycznego generowania opisów przez ChatGPT:

1. **Uzyskaj klucz API** na [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. **Stwórz plik `.env`** w głównym katalogu projektu:
   ```bash
   cp env_template.txt .env
   ```
3. **Edytuj plik `.env`** i dodaj swój klucz:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

**Uwaga:** Bez klucza API aplikacja będzie działać, ale opis będzie podstawowy.

## 📊 Jak używać

1. **Wczytaj dane** - użyj panelu po lewej stronie, aby wczytać plik CSV
2. **Wybierz kolumnę docelową** - określ, którą kolumnę chcesz przewidywać
3. **Rozpocznij analizę** - aplikacja automatycznie:
   - Określi typ problemu (klasyfikacja/regresja)
   - Zbuduje najlepszy model używając PyCaret
   - Wyświetli najważniejsze cechy
   - Wygeneruje opis wyników przez ChatGPT 🤖

## 📋 Wymagania dla danych

- **Format**: CSV
- **Minimalna liczba wierszy**: 10
- **Typy kolumn**: numeryczne lub kategoryczne
- **Wartości brakujące**: maksymalnie 70% w każdej kolumnie
- **Kolumna docelowa**: powinna być jasno określona

## 🔧 Architektura

Aplikacja składa się z następujących komponentów:

- **Interfejs użytkownika** (Streamlit) - wczytywanie danych i wyświetlanie wyników
- **Analiza danych** (Pandas) - przetwarzanie i czyszczenie danych
- **Machine Learning** (PyCaret) - automatyczny wybór i trenowanie modeli
- **Wizualizacja** (Plotly) - interaktywne wykresy i tabele

## 📈 Przykładowe wyniki

Aplikacja wyświetla:
- Ranking najważniejszych cech z procentowym udziałem
- Interaktywny wykres słupkowy
- Szczegółową tabelę z wynikami
- Opis słowny z wnioskami i rekomendacjami

## 🐛 Rozwiązywanie problemów

### Błąd instalacji PyCaret
```bash
# Spróbuj zainstalować bezpośrednio z conda-forge
conda install -c conda-forge pycaret
```

### Problemy z pamięcią
- Użyj mniejszych zbiorów danych
- Usuń kolumny z dużą liczbą wartości brakujących

### Błędy OpenAI API
- Sprawdź czy klucz API jest poprawny w pliku `.env`
- Upewnij się, że masz środki na koncie OpenAI
- Sprawdź połączenie internetowe

### Błędy podczas analizy
- Sprawdź czy kolumna docelowa ma odpowiedni typ danych
- Upewnij się, że dane mają wystarczającą liczbę wierszy

## 📝 Licencja

Ten projekt jest częścią kursu "Od zera do AI" i jest przeznaczony do celów edukacyjnych.

## 🤝 Wsparcie

W przypadku problemów, skontaktuj się przez kanał Discord: `#projekt-app_most_important_variables`
