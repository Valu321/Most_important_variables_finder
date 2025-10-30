# 🚀 Instrukcja wdrożenia aplikacji na DigitalOcean

## 📋 Wymagania wstępne

- Konto na [DigitalOcean](https://www.digitalocean.com)
- Konto na [Langfuse](https://langfuse.com) (dla monitoringu LLM)
- Klucz API OpenAI
- Git zainstalowany lokalnie
- Docker (opcjonalnie, do testowania lokalnego)

---

## 📝 KROK 1: Konfiguracja Langfuse

### 1.1. Utwórz konto na Langfuse
1. Przejdź na [cloud.langfuse.com](https://cloud.langfuse.com)
2. Zarejestruj się / zaloguj się
3. Po zalogowaniu otrzymasz:
   - **LANGFUSE_PUBLIC_KEY** (Public Key)
   - **LANGFUSE_SECRET_KEY** (Secret Key)

### 1.2. Skonfiguruj projekt w Langfuse
1. W dashboardzie Langfuse kliknij "Create Project"
2. Nadaj mu nazwę (np. "feature-analysis-app")
3. Zanotuj klucze API - będą potrzebne w kroku 3

---

## 📦 KROK 2: Przygotowanie aplikacji lokalnie

### 2.1. Sklonuj repozytorium (jeśli nie masz)
```bash
git clone <your-repo-url>
cd Homework
```

### 2.2. Zainstaluj zależności
```bash
pip install -r requirements.txt
```

### 2.3. Utwórz plik `.env`
```bash
cp env.example .env
```

### 2.4. Edytuj plik `.env` i uzupełnij dane:
```env
# OpenAI API
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 2.5. Przetestuj aplikację lokalnie
```bash
streamlit run app.py
```

Aplikacja powinna być dostępna na `http://localhost:8501`

---

## 🐳 KROK 3: Budowanie i testowanie obrazu Docker

### 3.1. Zbuduj obraz Docker
```bash
docker build -t feature-analysis-app .
```

### 3.2. Przetestuj obraz lokalnie
```bash
docker run -p 8501:8501 --env-file .env feature-analysis-app
```

Aplikacja powinna działać na `http://localhost:8501`

---

## 🚀 KROK 4: Wdrożenie na DigitalOcean

### 4.1. Utwórz konto na DigitalOcean
1. Przejdź na [digitalocean.com](https://www.digitalocean.com)
2. Zarejestruj się (możesz dostać $200 free credits na start)

### 4.2. Utwórz Droplet (serwer)
1. W dashboardzie DigitalOcean kliknij "Create" → "Droplets"
2. Wybierz:
   - **Ubuntu 22.04 (LTS)**
   - **Regular plan** (minimum 1GB RAM)
   - **Region** najbliższy Tobie
   - **Authentication**: SSH key lub Password
3. Kliknij "Create Droplet"
4. Zaczekaj na utworzenie serwera (około 1 minuty)
5. Zanotuj adres IP swojego droplet

### 4.3. Połącz się z serwerem
```bash
ssh root@<YOUR_SERVER_IP>
```

Jeśli używasz Windows, użyj [PuTTY](https://www.putty.org/) lub WSL

---

## 📥 KROK 5: Instalacja narzędzi na serwerze

### 5.1. Zaktualizuj system
```bash
apt update && apt upgrade -y
```

### 5.2. Zainstaluj Docker
```bash
# Zainstaluj Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Dodaj użytkownika do grupy docker
usermod -aG docker $USER
```

### 5.3. Zainstaluj Git
```bash
apt install git -y
```

### 5.4. Zainstaluj Docker Compose
```bash
apt install docker-compose -y
```

### 5.5. Konfiguracja Firewall (WYMAGANE dla publicznego dostępu)
```bash
# Zainstaluj i skonfiguruj UFW (firewall)
apt install ufw -y

# Zezwól na SSH (WAŻNE! Bez tego stracisz dostęp)
ufw allow 22/tcp

# Zezwól na port aplikacji Streamlit
ufw allow 8501/tcp

# Jeśli korzystasz z HTTP/HTTPS przez Nginx
ufw allow 80/tcp
ufw allow 443/tcp

# Włącz firewall
ufw --force enable

# Sprawdź status
ufw status
```

**⚠️ UWAGA:** Bez tego kroku aplikacja może nie być dostępna publicznie!

---

## 🔧 KROK 6: Konfiguracja aplikacji na serwerze

### 6.1. Sklonuj repozytorium na serwerze
```bash
cd /root
git clone <YOUR_REPO_URL> feature-analysis
cd feature-analysis
```

### 6.2. Utwórz plik `.env`
```bash
nano .env
```

Wklej konfigurację:
```env
OPENAI_API_KEY=your_openai_key_here
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

Zapisz: `Ctrl+O`, Enter, `Ctrl+X`

### 6.3. Zbuduj obraz Docker
```bash
docker build -t feature-analysis-app .
```

---

## 🎯 KROK 7: Uruchomienie aplikacji

### 7.1. Uruchom kontener Docker
```bash
docker run -d \
  --name feature-analysis \
  --restart=always \
  -p 8501:8501 \
  --env-file .env \
  feature-analysis-app
```

### 7.2. Sprawdź status aplikacji
```bash
docker ps
docker logs feature-analysis
```

---

## 🌐 KROK 8: Konfiguracja domeny (opcjonalne)

### 8.1. Dodaj domenę w DigitalOcean
1. W dashboardzie przejdź do "Networking" → "Domains"
2. Dodaj swoją domenę
3. Skonfiguruj rekordy DNS:
   - **A**: `@` → IP Twojego droplet
   - **A**: `www` → IP Twojego droplet

### 8.2. Zainstaluj Nginx jako reverse proxy
```bash
apt install nginx -y
```

### 8.3. Utwórz konfigurację Nginx
```bash
nano /etc/nginx/sites-available/feature-analysis
```

Wklej:
```nginx
server {
    listen 80;
    server_name twoja-domena.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 8.4. Aktywuj konfigurację
```bash
ln -s /etc/nginx/sites-available/feature-analysis /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 8.5. Zainstaluj SSL (Let's Encrypt)
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d twoja-domena.com
```

---

## 📊 KROK 9: Monitoring w Langfuse

### 9.1. Sprawdź metryki
1. Przejdź na [cloud.langfuse.com](https://cloud.langfuse.com)
2. Wybierz swój projekt
3. Otwórz sekcję "Traces"
4. Zobaczysz wszystkie wywołania LLM z metrykami:
   - **Latencja** (czas odpowiedzi)
   - **Koszt** wywołań API
   - **Jakość** odpowiedzi
   - **Tokens** użyte (wejściowe i wyjściowe)
   - **Prompts** - dokładne prompty wysłane do API

### 9.2. Badaj szczegóły
- Kliknij na dowolny trace aby zobaczyć szczegóły
- Zobacz dokładny prompt i odpowiedź
- Sprawdź metadane (typ problemu, liczba cech, etc.)

---

## 🔄 KROK 10: Aktualizacja aplikacji

### 10.1. Pull nowych zmian
```bash
cd /root/feature-analysis
git pull
```

### 10.2. Zbuduj nowy obraz
```bash
docker build -t feature-analysis-app .
```

### 10.3. Zatrzymaj stary kontener
```bash
docker stop feature-analysis
docker rm feature-analysis
```

### 10.4. Uruchom nowy kontener
```bash
docker run -d \
  --name feature-analysis \
  --restart=always \
  -p 8501:8501 \
  --env-file .env \
  feature-analysis-app
```

---

## 🛠️ Rozwiązywanie problemów

### Problem: Aplikacja nie startuje
```bash
# Sprawdź logi
docker logs feature-analysis

# Sprawdź czy port jest zajęty
netstat -tulpn | grep 8501
```

### Problem: Brak metryk w Langfuse
- Sprawdź czy klucze API są poprawne w pliku `.env`
- Sprawdź logi aplikacji: `docker logs feature-analysis`
- Upewnij się, że `LANGFUSE_ENABLED=True` w kodzie

### Problem: Błąd importu Langfuse
```bash
# Sprawdź czy zainstalowano bibliotekę
pip list | grep langfuse

# Zainstaluj ponownie
pip install langfuse
```

### Problem: Port nie odpowiada
```bash
# Sprawdź firewall
ufw status
ufw allow 8501

# Sprawdź czy Docker słucha
docker ps
```

---

## 📈 Monitoring i metryki

### Darmowa konfiguracja (podstawowa):
- **Langfuse Cloud**: Darmowy plan z 1GB danych/miesiąc
- **DigitalOcean**: Od $4/miesiąc dla najtańszego droplet

### Rekomendowane:
- **DigitalOcean**: $12/miesiąc (2GB RAM) dla lepszej wydajności
- **Langfuse Pro**: $20/miesiąc dla zaawansowanych metryk

---

## ✅ Checklist wdrożenia

- [ ] Konto na DigitalOcean utworzone
- [ ] Konto na Langfuse utworzone
- [ ] Klucze API skonfigurowane
- [ ] Docker zainstalowany na serwerze
- [ ] **Firewall skonfigurowany (port 8501 otwarty)** ⚠️
- [ ] Aplikacja zbudowana i przetestowana lokalnie
- [ ] Aplikacja wdrożona na DigitalOcean
- [ ] Domena skonfigurowana (opcjonalne)
- [ ] SSL zainstalowany (opcjonalne)
- [ ] Aplikacja dostępna publicznie (test z innego komputera)
- [ ] Metryki w Langfuse działają poprawnie
- [ ] Rozważono bezpieczeństwo (uwierzytelnianie, rate limiting)

---

## 🔒 Bezpieczeństwo i dostęp publiczny

### ✅ Co działa:
- Aplikacja będzie dostępna publicznie dla wszystkich użytkowników
- Użytkownicy mogą wczytywać własne pliki CSV i korzystać z aplikacji
- Dane są przetwarzane po stronie serwera

### ⚠️ Ważne informacje o bezpieczeństwie:

1. **Brak uwierzytelniania**: 
   - Aplikacja **nie ma** mechanizmu logowania
   - **Każdy** kto zna adres IP/domenę może korzystać z aplikacji
   - Rozważ dodanie uwierzytelniania dla produkcji

2. **Koszty API**:
   - Jeśli używasz OpenAI API, koszty będą naliczane za każde użycie
   - Każdy użytkownik może generować zapytania do ChatGPT
   - Monitoruj zużycie API w dashboardzie OpenAI

3. **Ograniczenie dostępu** (opcjonalne):
   Jeśli chcesz ograniczyć dostęp, możesz:
   - Dodać uwierzytelnianie Streamlit: utwórz plik `.streamlit/config.toml`
   - Użyj Nginx basic auth (dodaj w konfiguracji Nginx)
   - Dodaj IP whitelist w DigitalOcean firewall

4. **Bezpieczeństwo kluczy API**:
   - Klucze API są bezpiecznie przechowywane w pliku `.env`
   - Plik `.env` nie jest udostępniany użytkownikom (tylko na serwerze)

### 🚀 Dla produkcji rekomenduje się:
- Dodanie uwierzytelniania (hasło lub OAuth)
- Monitoring zużycia zasobów
- Rate limiting dla API calls
- Backup danych i logów

---

## 📞 Wsparcie

W przypadku problemów:
1. Sprawdź logi: `docker logs feature-analysis`
2. Sprawdź dokumentację: [docs.langfuse.com](https://docs.langfuse.com)
3. Sprawdź status DigitalOcean: [status.digitalocean.com](https://status.digitalocean.com)
