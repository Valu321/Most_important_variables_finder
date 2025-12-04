# 🚀 Instrukcja Wdrożenia na DigitalOcean App Platform

Ta instrukcja przeprowadzi Cię przez proces wdrożenia aplikacji **Most Important Variables Finder** (zasilanej przez GPT-4o-mini) na chmurę DigitalOcean.

## 💡 Dlaczego GPT-4o-mini?

W zaktualizowanym kodzie używamy modelu `gpt-4o-mini`, ponieważ:

- **Cena**: Jest znacznie tańszy niż `gpt-3.5-turbo`
- **Inteligencja**: Osiąga lepsze wyniki w rozumowaniu i analizie danych
- **Szybkość**: Generuje odpowiedzi szybciej, co znacząco poprawia UX aplikacji

## ✅ KROK 1: Przygotowanie Repozytorium GitHub

Upewnij się, że w głównym katalogu projektu na swoim komputerze masz następujące pliki:

- `app.py`
- `requirements.txt`
- `Dockerfile`
- `app.yaml` (zaktualizowany o Twoją nazwę repozytorium)

Zatwierdź wszystkie zmiany i wyślij je na GitHub:

```bash
git add .
git commit -m "Przygotowanie do wdrożenia: GPT-4o-mini + Docker"
git push origin main
```

## 📊 KROK 2: Konfiguracja Langfuse (Monitoring LLM)

Zanim wdrożysz aplikację, przygotuj monitoring, aby śledzić koszty i jakość odpowiedzi modelu.

### Załóż konto / Zaloguj się

Przejdź na [cloud.langfuse.com](https://cloud.langfuse.com).

### Utwórz Projekt

1. Kliknij **New Project**
2. Nazwij go: `Most_important_variables_finder`

### Pobierz Klucze API

1. Wybierz **Settings** → **API Keys**
2. Kliknij **Create new API keys**
3. Skopiuj **Public Key** i **Secret Key**. Będą one potrzebne w Kroku 5.
4. **Host** (dla chmury UE): `https://cloud.langfuse.com`

## ☁️ KROK 3: Utworzenie Aplikacji w DigitalOcean

1. Zaloguj się do **DigitalOcean Cloud Panel**
2. W menu po lewej kliknij **Apps** → **Create App**
3. Wybierz **GitHub** jako źródło kodu (Service Provider)
4. Wybierz swoje repozytorium: `Most_important_variables_finder`
5. Upewnij się, że wybrana gałąź to `main`
6. Kliknij **Next**

## ⚙️ KROK 4: Konfiguracja Zasobów

DigitalOcean powinien automatycznie wykryć plik `app.yaml` lub `Dockerfile`.

1. Kliknij **Edit Plan** przy nazwie swojego serwisu (domyślnie może to być nazwa repozytorium)

### Wybór Pamięci RAM (Krytyczne!)

> ⚠️ **Uwaga**: Plan "Basic XXS" (512MB RAM) nie zadziała – biblioteka PyCaret wymaga więcej pamięci operacyjnej do instalacji i działania.

- Wybierz **Basic S** (1GB RAM - $12/miesiąc) lub dla większej stabilności **Basic M** (2GB RAM - $24/miesiąc)
- Zatwierdź wybór przyciskiem **Save**

## 🔑 KROK 5: Zmienne Środowiskowe (Secrets)

W sekcji **"Environment Variables"** (podczas konfiguracji lub w ustawieniach aplikacji po utworzeniu) dodaj swoje klucze API.

> **Ważne**: Kliknij **Encrypt** przy kluczach API, aby były bezpieczne.

| Nazwa Zmiennej          | Wartość                                           | Typ        |
|------------------------|---------------------------------------------------|------------|
| `OPENAI_API_KEY`        | Twój klucz API OpenAI (zaczyna się od `sk-...`)  | Secret 🔒  |
| `LANGFUSE_PUBLIC_KEY`   | Twój Public Key z Langfuse (z Kroku 2)           | Secret 🔒  |
| `LANGFUSE_SECRET_KEY`   | Twój Secret Key z Langfuse (z Kroku 2)           | Secret 🔒  |
| `LANGFUSE_HOST`         | `https://cloud.langfuse.com`                      | Plain Text |
| `PORT`                  | `8501`                                            | Plain Text |

## 🚀 KROK 6: Uruchomienie

1. Kliknij **Next**, przejrzyj podsumowanie i na końcu kliknij **Create Resources**
2. Wdrożenie potrwa kilka minut (budowanie kontenera z PyCaret jest czasochłonne, więc bądź cierpliwy)
3. Po zakończeniu otrzymasz publiczny adres URL aplikacji w formacie:
   ```
   https://most-important-variables-finder-xxxxx.ondigitalocean.app
   ```

## 🛠️ Rozwiązywanie problemów

### Deploy Error (Health Check Timeout)

Jeśli aplikacja nie wstaje na czas (status "Unhealthy"), wejdź w zakładkę **Settings** → wybierz swój komponent → **Health Check** i zwiększ **Initial Delay** do **120 sekund**.

### Out of Memory (OOM) / Restartowanie się aplikacji

Jeśli aplikacja pomyślnie się zbuduje, ale resetuje się podczas analizy danych, oznacza to brak pamięci RAM. W takim przypadku wejdź w **Settings** i zwiększ plan (**Instance Size**) na wersję z **2GB RAM**.
