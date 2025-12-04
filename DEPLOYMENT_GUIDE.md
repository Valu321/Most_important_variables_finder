# 🚀 Instrukcja Wdrożenia na DigitalOcean App Platform

Ta instrukcja przeprowadzi Cię przez proces wdrożenia aplikacji **Most Important Variables Finder** (zasilanej przez GPT-4o-mini) na chmurę DigitalOcean.

## 💡 Dlaczego GPT-4o-mini?

W zaktualizowanym kodzie używamy modelu `gpt-4o-mini`, ponieważ:

- **Cena**: Jest znacznie tańszy niż `gpt-3.5-turbo`
- **Inteligencja**: Osiąga lepsze wyniki w rozumowaniu i analizie danych
- **Szybkość**: Generuje odpowiedzi szybciej, co znacząco poprawia UX aplikacji

## ✅ KROK 1: Przygotowanie Repozytorium GitHub

Upewnij się, że w głównym katalogu projektu na swoim komputerze masz następujące pliki:

- `app.py` (zaktualizowany o zabezpieczenia)
- `requirements.txt`
- `Dockerfile`
- `app.yaml` (zaktualizowany o Twoją nazwę repozytorium)

Zatwierdź wszystkie zmiany i wyślij je na GitHub:

```bash
git add .
git commit -m "Przygotowanie do wdrożenia: GPT-4o-mini + Bezpieczeństwo SaaS"
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

1. Kliknij **Edit Plan** przy nazwie swojego serwisu

### Wybór Pamięci RAM (Krytyczne!)

> ⚠️ **Uwaga**: Plan "Basic XXS" (512MB RAM) nie zadziała – biblioteka PyCaret wymaga więcej pamięci operacyjnej do instalacji i działania.

- Wybierz **Basic S** (1GB RAM - $12/miesiąc) lub dla większej stabilności **Basic M** (2GB RAM - $24/miesiąc)
- Zatwierdź wybór przyciskiem **Save**

## 🔑 KROK 5: Zmienne Środowiskowe (Secrets)

> **Model SaaS**: W tej wersji aplikacji przyjęliśmy model SaaS, gdzie użytkownik podaje własny klucz OpenAI w aplikacji.  
> Dlatego **NIE ustawiamy `OPENAI_API_KEY`** po stronie serwera, aby uniknąć naliczania kosztów na Twoje konto.

Dodaj tylko klucze monitoringu (Langfuse). Kliknij **Encrypt**, aby były bezpieczne.

| Nazwa Zmiennej          | Wartość                                           | Typ        | Uwagi                         |
|------------------------|---------------------------------------------------|------------|-------------------------------|
| `LANGFUSE_PUBLIC_KEY`   | Twój Public Key z Langfuse                        | Secret 🔒  | Wymagane                      |
| `LANGFUSE_SECRET_KEY`   | Twój Secret Key z Langfuse                        | Secret 🔒  | Wymagane                      |
| `LANGFUSE_HOST`         | `https://cloud.langfuse.com`                      | Plain Text | Wymagane                      |
| `PORT`                  | `8501`                                            | Plain Text | Wymagane                      |
| ~~`OPENAI_API_KEY`~~    | (Pomiń to pole)                                   | -          | Klucz podaje użytkownik w aplikacji |

## 🚀 KROK 6: Uruchomienie

1. Kliknij **Next**, przejrzyj podsumowanie i na końcu kliknij **Create Resources**
2. Wdrożenie potrwa kilka minut
3. Po zakończeniu otrzymasz publiczny adres URL aplikacji

## 🛠️ Rozwiązywanie problemów

### Błąd "Plik za duży"

Aplikacja ma wbudowany limit **10MB** dla plików CSV, aby chronić serwer przed przeciążeniem pamięci (DoS).

### Deploy Error (Health Check Timeout)

Jeśli aplikacja nie wstaje na czas, zwiększ **Initial Delay** w sekcji **Health Check** do **120 sekund**.

### Out of Memory (OOM)

Jeśli aplikacja resetuje się przy dużych plikach, zwiększ plan serwera na wersję z **2GB RAM**.
