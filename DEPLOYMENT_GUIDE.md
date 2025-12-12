# ☁️ Instrukcja Wdrożenia (Deployment Guide)

Projekt jest zoptymalizowany pod kątem konteneryzacji (Docker) oraz chmury DigitalOcean App Platform. Poniżej znajdują się szczegóły techniczne.

---

## 🐳 Docker

Aplikacja wymaga specyficznych bibliotek systemowych (m.in. `libgomp1` dla LightGBM/PyCaret), które są już uwzględnione w `Dockerfile`.

### 1. Budowanie obrazu

```bash
docker build -t feature-app .
```

### 2. Uruchomienie kontenera

Uruchomienie wymaga przekazania zmiennych środowiskowych.

```bash
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="sk-twoj-klucz..." \
  feature-app
```

**Alternatywnie z plikiem `.env`:**

```bash
docker run -p 8501:8501 --env-file .env feature-app
```

### 🔍 Healthcheck

Kontener posiada wbudowany Healthcheck:

- **Endpoint**: `http://localhost:8501/_stcore/health`
- **Interval**: 30s
- **Retries**: 3

---

## 🌊 DigitalOcean App Platform

Repozytorium zawiera plik `app.yaml`, który definiuje infrastrukturę (Infrastructure as Code).

### Specyfikacja instancji (app.yaml)

| Parametr | Wartość |
|----------|---------|
| **Service Name** | `feature-analysis-service` |
| **Region** | Frankfurt (fra) |
| **Port** | `8501` |
| **Health Check Path** | `/_stcore/health` |

### ⚠️ Wymagania Pamięciowe (Ważne!)

> **PyCaret jest biblioteką pamięciożerną.** Analiza plików CSV w połączeniu z treningiem modeli wymaga odpowiednich zasobów.

| Plan | RAM | Status |
|------|-----|--------|
| **Basic XXS** | 512MB | ❌ Niewystarczający - aplikacja zostanie zabita przez OOM Killer |
| **Basic S** | 1GB | ✅ Minimum - $12/miesiąc |
| **Basic M** | 2GB | ✅ Zalecane - $24/miesiąc |

### Proces Wdrożenia ("Click to Deploy")

1. Zaloguj się do **DigitalOcean**
2. Przejdź do **Apps** → **Create App**
3. Wybierz **GitHub** jako źródło kodu i wskaż to repozytorium
4. Platforma powinna automatycznie wykryć plik `app.yaml` lub `Dockerfile`

#### Environment Variables

W sekcji konfiguracji musisz ręcznie dodać **Secrets** (klucze nie są w `app.yaml` ze względów bezpieczeństwa):

| Zmienna | Typ | Wymagane |
|---------|-----|----------|
| `OPENAI_API_KEY` | Secret 🔒 | Tak (dla użytkowników - model SaaS) |
| `LANGFUSE_PUBLIC_KEY` | Secret 🔒 | Opcjonalnie |
| `LANGFUSE_SECRET_KEY` | Secret 🔒 | Opcjonalnie |
| `LANGFUSE_HOST` | Plain Text | Opcjonalnie (domyślnie: `https://cloud.langfuse.com`) |
| `PORT` | Plain Text | Tak (domyślnie: `8501`) |

> **Uwaga**: W modelu SaaS użytkownicy podają własny klucz OpenAI w aplikacji, więc `OPENAI_API_KEY` po stronie serwera może pozostać puste.

5. Kliknij **Deploy**

---

## 🛠️ Rozwiązywanie problemów (Troubleshooting)

### ❌ Aplikacja restartuje się podczas "Trenowanie modeli..."

**Objawy**: Aplikacja nagle się restartuje podczas trenowania modeli.

**Przyczyna**: To klasyczny objaw braku pamięci RAM (OOM - Out Of Memory).

**Rozwiązanie**:

1. **Sprawdź logi w DigitalOcean**: Szukaj komunikatu `Error 137` lub `OOM Killed`
2. **Użyj Memory Guarda**: W aplikacji widać wykres "Status Pamięci". Jeśli linia dochodzi do 100% tuż przed restartem, musisz zwiększyć plan hostingu (Scale Up)
3. **Diagnostyka**: W repozytorium znajduje się plik `app_copy.py`. Możesz tymczasowo zmienić `ENTRYPOINT` w `Dockerfile` na `streamlit run app_copy.py`, aby uruchomić narzędzie do testowania limitów pamięci ("Diagnostyka Pamięci na DigitalOcean")

### ❌ Błędy PyCaret / LightGBM

**Objawy**: Błędy związane z `libgomp.so.1` podczas uruchamiania.

**Rozwiązanie**:

Upewnij się, że używasz dostarczonego `Dockerfile`. Zawiera on linię:

```dockerfile
RUN apt-get update && apt-get install -y ... libgomp1
```

Jeśli budujesz własny Dockerfile, dodaj:

```dockerfile
RUN apt-get update && apt-get install -y libgomp1
```

### ⏱️ Health Check Timeout

**Objawy**: Aplikacja nie wstaje na czas, status "Unhealthy".

**Rozwiązanie**:

1. Wejdź w **Settings** → wybierz swój komponent → **Health Check**
2. Zwiększ **Initial Delay** do **120 sekund**
3. Zwiększ **Interval** do **60 sekund**

---

## 📊 Monitorowanie

Aplikacja posiada wbudowany monitor pamięci, który można obserwować w czasie rzeczywistym podczas analizy danych. Wykres pokazuje:

- Aktualne zużycie pamięci RAM
- Trend zużycia w czasie
- Ostrzeżenia przed osiągnięciem limitu

---

## 🔒 Bezpieczeństwo

- Wszystkie klucze API są przechowywane jako **Secrets** w DigitalOcean
- Dane użytkowników nie są zapisywane na dysku
- Do AI wysyłane są tylko zanonimizowane statystyki
- Aplikacja działa w modelu SaaS - każdy użytkownik używa własnego klucza OpenAI

---

## 📝 Przydatne linki

- [DigitalOcean App Platform Documentation](https://docs.digitalocean.com/products/app-platform/)
- [Docker Documentation](https://docs.docker.com/)
- [PyCaret Documentation](https://pycaret.org/)
