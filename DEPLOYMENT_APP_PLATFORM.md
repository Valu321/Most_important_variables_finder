# 🚀 Wdrożenie aplikacji na DigitalOcean App Platform

Kompleksowa instrukcja wdrożenia aplikacji Streamlit na DigitalOcean App Platform - najprostsze podejście bez zarządzania serwerami.

## 📋 Zalety App Platform vs Droplet

✅ **Automatyczne zarządzanie** - DigitalOcean zarządza infrastrukturą  
✅ **Automatyczny SSL** - certyfikaty HTTPS są dodawane automatycznie  
✅ **Auto-scaling** - możliwość automatycznego skalowania  
✅ **Zero-downtime deployments** - aktualizacje bez przestojów  
✅ **Prostsza konfiguracja** - nie trzeba konfigurować Docker, firewall, Nginx  
✅ **Monitoring wbudowany** - metryki i logi dostępne od razu  

---

## 🎯 KROK 1: Przygotowanie repozytorium GitHub

### 1.1. Utwórz repozytorium na GitHub
```bash
# Jeśli jeszcze nie masz repozytorium
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 1.2. Sprawdź strukturę projektu
Upewnij się, że masz w repozytorium:
- ✅ `app.py` - główna aplikacja
- ✅ `requirements.txt` - zależności Python
- ✅ `app.yaml` - konfiguracja App Platform (opcjonalna, ale zalecana)
- ✅ `Dockerfile` - opcjonalne (App Platform może zbudować automatycznie)

---

## 🔧 KROK 2: Konfiguracja pliku app.yaml

### 2.1. Edytuj plik `app.yaml`

W pliku `app.yaml` zaktualizuj:
- `repo: YOUR_GITHUB_USERNAME/YOUR_REPO_NAME` - nazwa Twojego repozytorium
- `branch: main` - gałąź do wdrożenia (zazwyczaj `main` lub `master`)
- `instance_size_slug` - rozmiar instancji:
  - `basic-xxs` - $5/miesiąc (1 vCPU, 512MB RAM) - **zalecane do startu**
  - `basic-xs` - $12/miesiąc (1 vCPU, 1GB RAM)
  - `basic-s` - $24/miesiąc (1 vCPU, 2GB RAM) - **dla większych zbiorów danych**

### 2.2. Zatwierdź zmiany w Git
```bash
git add app.yaml
git commit -m "Add App Platform configuration"
git push
```

---

## 🌐 KROK 3: Utworzenie aplikacji w DigitalOcean

### 3.1. Zaloguj się do DigitalOcean
1. Przejdź na [digitalocean.com](https://www.digitalocean.com)
2. Zaloguj się lub utwórz konto (możesz dostać $200 kredytów na start)

### 3.2. Utwórz nową aplikację
1. W dashboardzie kliknij **"Apps"** → **"Create App"**
2. Wybierz **"GitHub"** jako źródło kodu
3. Połącz swoje konto GitHub (jeśli pierwszy raz)
4. Wybierz repozytorium z aplikacją
5. Wybierz gałąź (`main` lub `master`)

### 3.3. Konfiguracja aplikacji
DigitalOcean automatycznie wykryje:
- ✅ **Build Type**: Python
- ✅ **Build Command**: automatycznie zainstaluje zależności z `requirements.txt`
- ✅ **Run Command**: będzie używać komendy z `app.yaml` lub można ustawić ręcznie:
   ```
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

**Jeśli nie ma `app.yaml`:**
- **Source Directory**: `/` (katalog główny)
- **Build Command**: `pip install -r requirements.txt`
- **Run Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- **HTTP Port**: `8501`

### 3.4. Konfiguracja zasobów
- **Instance Size**: Wybierz `Basic` → `Basic $5/mo` (512MB RAM) do startu
- **Instance Count**: `1` (możesz skalować później

---

## 🔑 KROK 4: Konfiguracja zmiennych środowiskowych

### 4.1. Dodaj Secrets (klucze API)
W sekcji **"Environment Variables"** dodaj:

1. **OPENAI_API_KEY**
   - Type: `SECRET`
   - Value: Twój klucz OpenAI API
   - ✅ Oznacz jako **Encrypted**

2. **LANGFUSE_PUBLIC_KEY**
   - Type: `SECRET`
   - Value: Twój publiczny klucz Langfuse
   - ✅ Oznacz jako **Encrypted**

3. **LANGFUSE_SECRET_KEY**
   - Type: `SECRET`
   - Value: Twój sekretny klucz Langfuse
   - ✅ Oznacz jako **Encrypted**

4. **LANGFUSE_HOST**
   - Type: `GENERAL`
   - Value: `https://cloud.langfuse.com`

5. **PORT**
   - Type: `GENERAL`
   - Value: `8501`
   - ⚠️ DigitalOcean może też automatycznie ustawić PORT, ale warto być explicit

6. **PYTHONUNBUFFERED**
   - Type: `GENERAL`
   - Value: `1`

### 4.2. Konto na Langfuse (jeśli jeszcze nie masz)
1. Przejdź na [cloud.langfuse.com](https://cloud.langfuse.com)
2. Utwórz konto (darmowy plan dostępny)
3. Utwórz nowy projekt
4. Skopiuj klucze API z dashboardu

---

## 🚀 KROK 5: Wdrożenie aplikacji

### 5.1. Przejrzyj konfigurację
Przed wdrożeniem sprawdź:
- ✅ Źródło kodu (GitHub repo i branch)
- ✅ Build i Run commands
- ✅ Zmienne środowiskowe
- ✅ Rozmiar instancji

### 5.2. Wdróż aplikację
1. Kliknij **"Next"** lub **"Review"**
2. Przejrzyj szczegóły i koszt
3. Kliknij **"Create Resources"**

**Pierwsze wdrożenie zajmuje ~5-10 minut:**
- Instalacja zależności (PyCaret może być długi)
- Budowa kontenera
- Start aplikacji

### 5.3. Monitoruj proces wdrożenia
W sekcji **"Runtime Logs"** zobaczysz:
- Instalację zależności Python
- Komunikaty z aplikacji Streamlit
- Ewentualne błędy

---

## ✅ KROK 6: Weryfikacja działania aplikacji

### 6.1. Sprawdź URL aplikacji
Po zakończeniu wdrożenia otrzymasz URL:
```
https://YOUR_APP_NAME-XXXXX.ondigitalocean.app
```

### 6.2. Przetestuj aplikację
1. Otwórz URL w przeglądarce
2. Powinna pojawić się strona z interfejsem aplikacji
3. Wczytaj przykładowy plik CSV (np. `sample_data.csv`)
4. Sprawdź czy analiza działa poprawnie

### 6.3. Sprawdź logi
W dashboardzie DigitalOcean:
- **Runtime Logs** - logi aplikacji w czasie rzeczywistym
- **Build Logs** - logi z procesu budowania
- **Metrics** - użycie CPU, pamięci, ruch sieciowy

---

## 🔄 KROK 7: Aktualizacja aplikacji

### 7.1. Wprowadź zmiany w kodzie
```bash
# Zmień kod lokalnie
# ...

# Zatwierdź zmiany
git add .
git commit -m "Update: opis zmian"
git push origin main
```

### 7.2. Automatyczne wdrożenie
App Platform automatycznie:
- ✅ Wykryje push do głównej gałęzi
- ✅ Rozpocznie nowe wdrożenie
- ✅ Zbuduje nową wersję aplikacji
- ✅ Wdroży bez przestojów (zero-downtime)

Możesz monitorować proces w dashboardzie DigitalOcean w sekcji **"Activity"**.

---

## 🌍 KROK 8: Konfiguracja domeny niestandardowej (opcjonalne)

### 8.1. Dodaj domenę w App Platform
1. W ustawieniach aplikacji przejdź do **"Settings"** → **"Domains"**
2. Kliknij **"Add Domain"**
3. Wpisz swoją domenę (np. `app.yourdomain.com`)
4. DigitalOcean automatycznie:
   - ✅ Skonfiguruje DNS
   - ✅ Zainstaluje SSL (Let's Encrypt)
   - ✅ Skieruje ruch na Twoją aplikację

### 8.2. Konfiguracja DNS
W panelu Twojego rejestratora domen dodaj rekord CNAME:
```
Type: CNAME
Name: app (lub @ dla głównej domeny)
Value: YOUR_APP_NAME-XXXXX.ondigitalocean.app
```

---

## 📊 KROK 9: Monitoring i metryki

### 9.1. Monitoring w DigitalOcean
W dashboardzie App Platform dostępne są:
- **CPU Usage** - użycie procesora
- **Memory Usage** - użycie pamięci
- **Request Rate** - liczba żądań HTTP
- **Response Time** - czas odpowiedzi
- **Error Rate** - wskaźnik błędów

### 9.2. Monitoring w Langfuse
1. Przejdź na [cloud.langfuse.com](https://cloud.langfuse.com)
2. Wybierz swój projekt
3. W sekcji **"Traces"** zobaczysz:
   - Wywołania API do ChatGPT
   - Koszty każdego wywołania
   - Latencję odpowiedzi
   - Użyte tokeny

---

## 🔒 Bezpieczeństwo w App Platform

### ✅ Co jest automatycznie zabezpieczone:
- **HTTPS/SSL** - certyfikaty są automatycznie zarządzane
- **Secrets** - klucze API są szyfrowane
- **Firewall** - tylko port 443/80 jest otwarty publicznie
- **Isolation** - aplikacja działa w izolowanym kontenerze

### ⚠️ Uwagi o bezpieczeństwie:
1. **Brak uwierzytelniania w aplikacji**:
   - Aplikacja jest dostępna publicznie dla każdego
   - Rozważ dodanie uwierzytelniania Streamlit

2. **Koszty API**:
   - Monitoruj zużycie OpenAI API
   - Ustaw alerty budżetowe w OpenAI

3. **Rate Limiting** (opcjonalne):
   - Możesz dodać rate limiting przez DigitalOcean Load Balancer
   - Lub implementować w samej aplikacji

---

## 💰 Koszty i optymalizacja

### Podstawowa konfiguracja:
- **Instance**: Basic $5/miesiąc (512MB RAM)
- **Bandwidth**: 1TB wliczone (więcej niż wystarczy)
- **Storage**: 1GB wliczone (wystarczy dla aplikacji)

**Razem: ~$5/miesiąc**

### Jeśli potrzebujesz więcej zasobów:
- Upgrade do `basic-xs` ($12/miesiąc) jeśli:
  - Aplikacja działa wolno
  - Masz błędy "out of memory"
  - Przetwarzasz duże zbiory danych (>100MB CSV)

### Dodatkowe koszty:
- **OpenAI API**: w zależności od użycia (~$0.002 per request)
- **Langfuse**: darmowy plan do 1GB danych/miesiąc
- **Domain**: jeśli kupisz domenę (~$10-15/rok)

---

## 🐛 Rozwiązywanie problemów

### Problem: Build się nie powiódł
```bash
# Sprawdź build logs w dashboardzie
# Częste przyczyny:
# - Błędy w requirements.txt
# - Brak zależności systemowych
# - Problem z PyCaret instalacją
```

**Rozwiązanie:**
- Sprawdź logi buildu w dashboardzie
- Przetestuj instalację lokalnie: `pip install -r requirements.txt`
- Upewnij się, że wszystkie zależności są w `requirements.txt`

### Problem: Aplikacja nie startuje
```bash
# Sprawdź runtime logs
# Sprawdź czy PORT jest ustawiony
```

**Rozwiązanie:**
- Sprawdź czy `$PORT` jest ustawiony w zmiennych środowiskowych
- Upewnij się, że run command używa `--server.address 0.0.0.0`
- Sprawdź health check endpoint

### Problem: Błąd "Out of Memory"
**Rozwiązanie:**
- Upgrade do większej instancji (np. `basic-xs`)
- Lub zoptymalizuj aplikację (mniejsze zbiory danych)

### Problem: Aplikacja działa wolno
**Rozwiązanie:**
- Upgrade do większej instancji
- Sprawdź metryki CPU i pamięci
- Optymalizuj kod przetwarzania danych

### Problem: Brak kluczy API
**Rozwiązanie:**
- Upewnij się, że dodałeś klucze jako **SECRETS** w App Platform
- Sprawdź czy nazwy zmiennych są poprawne (wielkość liter!)
- Aplikacja działa bez OpenAI, ale opisy będą podstawowe

---

## ✅ Checklist wdrożenia App Platform

- [ ] Repozytorium GitHub utworzone i kod wypushowany
- [ ] Plik `app.yaml` skonfigurowany i zatwierdzony
- [ ] Konto na DigitalOcean utworzone
- [ ] Konto na Langfuse utworzone (opcjonalne)
- [ ] Klucze API przygotowane
- [ ] Aplikacja utworzona w App Platform
- [ ] GitHub połączony z App Platform
- [ ] Zmienne środowiskowe (secrets) skonfigurowane
- [ ] Rozmiar instancji wybrany
- [ ] Pierwsze wdrożenie zakończone sukcesem
- [ ] Aplikacja dostępna pod URL DigitalOcean
- [ ] Przetestowana funkcjonalność aplikacji
- [ ] Monitoring skonfigurowany
- [ ] Domena niestandardowa dodana (opcjonalne)

---

## 📞 Wsparcie

### Przydatne linki:
- [DigitalOcean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/knowledge-base/tutorials/deploy)
- [Langfuse Documentation](https://langfuse.com/docs)

### W przypadku problemów:
1. Sprawdź **Runtime Logs** w dashboardzie App Platform
2. Sprawdź **Build Logs** jeśli build się nie udaje
3. Przetestuj aplikację lokalnie przed wdrożeniem
4. Sprawdź dokumentację DigitalOcean App Platform

---

## 🎉 Gratulacje!

Twoja aplikacja jest teraz dostępna publicznie na DigitalOcean App Platform! 🚀

Aplikacja automatycznie:
- ✅ Aktualizuje się przy każdym push do głównej gałęzi
- ✅ Ma automatyczny SSL/HTTPS
- ✅ Jest skalowalna i monitorowana
- ✅ Ma wbudowane backupy i high availability

