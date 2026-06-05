# Kochbuch App - Standalone Deployment

## 🎯 Vollständig Selbstständig

✅ Keine Emergent-Abhängigkeiten mehr
✅ Lokaler File Storage
✅ Docker-ready
✅ Eigener Google Gemini API Key

---

## 📦 Schnellstart (Docker)

### Voraussetzungen
- Docker & Docker Compose installiert
- Google Gemini API Key (kostenlos: https://aistudio.google.com/apikey)

### Installation

```bash
# 1. Repository klonen/herunterladen
cd /pfad/zu/kochbuch

# 2. Environment konfigurieren
cp .env.example .env

# 3. .env bearbeiten - WICHTIG!
nano .env
# Tragen Sie Ihren Google API Key ein:
# GOOGLE_API_KEY=AIza...IhrKeyHier

# 4. App starten
docker-compose up -d

# 5. Logs prüfen
docker-compose logs -f
```

### App erreichen
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **MongoDB**: localhost:27017

---

## 🔧 Verwaltung

```bash
# App stoppen
docker-compose down

# App neu starten
docker-compose restart

# Logs ansehen
docker-compose logs -f backend
docker-compose logs -f frontend

# Alle Daten löschen (MongoDB)
docker-compose down -v
```

---

## 🌐 Production Deployment

### Mit eigenem Domain

1. **Nginx Reverse Proxy** (empfohlen):
   ```nginx
   server {
       listen 80;
       server_name ihre-domain.de;
       
       location / {
           proxy_pass http://localhost:80;
       }
       
       location /api/ {
           proxy_pass http://localhost:8001;
       }
   }
   ```

2. **SSL mit Let's Encrypt**:
   ```bash
   sudo certbot --nginx -d ihre-domain.de
   ```

3. **Backend URL anpassen**:
   In `docker-compose.yml`:
   ```yaml
   environment:
     - REACT_APP_BACKEND_URL=https://ihre-domain.de
   ```

---

## 🎨 Features

- ✅ Rezepte erstellen, bearbeiten, löschen
- ✅ KI-generierte Kochanleitungen (Gemini 2.0 Flash)
- ✅ KI-generierte Rezeptbilder (Gemini 2.0)
- ✅ Zutaten-Management
- ✅ Filter nach Kalorien, Protein, Bewertung
- ✅ Vintage Kochbuch Design (Worn Recipe Journal)
- ✅ Responsive (Desktop & Tablet)
- ✅ MongoDB Datenbank
- ✅ Lokaler File Storage

---

## 💰 Kosten

| Service | Kosten |
|---------|--------|
| **Server** | $5-10/Monat (DigitalOcean, Hetzner) |
| **Google Gemini API** | Kostenlos (15 req/min), dann $0.000125/1K tokens |
| **MongoDB** | Kostenlos (selbst gehostet) |
| **Domain** | ~$10/Jahr |
| **SSL** | Kostenlos (Let's Encrypt) |

**Total:** ~$5-10/Monat + Domain

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
docker-compose logs backend
# Häufige Ursache: Google API Key fehlt in .env
```

### Frontend kann Backend nicht erreichen
```bash
# Prüfe REACT_APP_BACKEND_URL in docker-compose.yml
# Für lokale Tests: http://localhost:8001
# Für Production: https://ihre-domain.de
```

### MongoDB Connection Error
```bash
# Prüfe ob MongoDB Container läuft
docker-compose ps
# MongoDB neu starten
docker-compose restart mongodb
```

### KI-Funktionen funktionieren nicht
```bash
# 1. Prüfe API Key in .env
cat .env | grep GOOGLE_API_KEY

# 2. Backend Logs prüfen
docker-compose logs backend | grep -i error

# 3. API Key testen
curl https://generativelanguage.googleapis.com/v1/models?key=IHR_KEY
```

---

## 📂 Projekt-Struktur

```
/app/
├── backend/
│   ├── server.py          # FastAPI Server
│   ├── requirements.txt   # Python Dependencies
│   ├── .env               # Backend Config
│   └── uploads/           # Uploaded Images
├── frontend/
│   ├── src/
│   │   ├── App.js         # React Main Component
│   │   └── App.css        # Vintage Styling
│   ├── package.json       # Node Dependencies
│   └── .env               # Frontend Config
├── docker-compose.yml     # Docker Orchestration
├── Dockerfile.backend     # Backend Container
├── Dockerfile.frontend    # Frontend Container
├── nginx.conf             # Reverse Proxy Config
└── .env.example           # Environment Template
```

---

## 🔐 Sicherheit

### Production Empfehlungen:

1. **API Key Schutz**:
   - Nie in Git committen
   - Environment Variables verwenden
   - Key regelmäßig rotieren

2. **MongoDB Absicherung**:
   ```yaml
   # docker-compose.yml
   environment:
     MONGO_INITDB_ROOT_USERNAME: admin
     MONGO_INITDB_ROOT_PASSWORD: sicheres_passwort
   ```

3. **Firewall**:
   ```bash
   # Nur Port 80/443 öffnen
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **HTTPS erzwingen** (Nginx):
   ```nginx
   if ($scheme != "https") {
       return 301 https://$host$request_uri;
   }
   ```

---

## 📊 Monitoring

### Logs überwachen
```bash
# Alle Logs
docker-compose logs -f

# Nur Backend
docker-compose logs -f backend

# Nur Frontend
docker-compose logs -f frontend

# Nur Fehler
docker-compose logs | grep -i error
```

### Ressourcen überwachen
```bash
# Container Stats
docker stats

# Disk Usage
docker system df
```

---

## 🚀 Updates

```bash
# Code aktualisieren
git pull  # (falls Git verwendet wird)

# Container neu bauen
docker-compose build

# Mit neuen Containern starten
docker-compose up -d
```

---

## 📝 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs: `docker-compose logs`
2. Prüfen Sie die Troubleshooting-Sektion
3. Erstellen Sie ein GitHub Issue (falls Repository vorhanden)

---

## 📜 Lizenz

Dieses Projekt ist für private und kommerzielle Nutzung frei verfügbar.