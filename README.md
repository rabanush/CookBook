# 🍳 Kochbuch App - Standalone Deployment

## 🚀 Schnellstart (2 Schritte!)

### Variante 1: OHNE API Key (nur Rezepte & Zutaten)

frontend/.env Datei erstellenen
REACT_APP_BACKEND_URL=URL
```bash
docker-compose up -d
```

**Fertig!** App läuft auf http://localhost

### Variante 2: MIT API Key (KI-Features)

```bash
# API Key als Umgebungsvariable setzen
export GOOGLE_API_KEY=IhrGoogleAPIKey
docker-compose up -d
```

**ODER** direkt in `docker-compose.yml` eintragen (Zeile 29):

```yaml
- GOOGLE_API_KEY=AIzaSy...IhrKeyHier
```

---

## ✅ Features

**OHNE API Key:**
- ✅ Rezepte erstellen, bearbeiten, löschen
- ✅ Zutaten-Management
- ✅ Filter (Kalorien, Protein, Rating)
- ✅ Suche
- ✅ Bilder hochladen

**MIT API Key (optional):**
- 🤖 KI-generierte Kochanleitungen
- 🖼️ KI-generierte Rezeptbilder

---

## 🔑 Google API Key

**Nur für KI-Features! Rezepte funktionieren ohne.**

1. **Key holen** (kostenlos): https://aistudio.google.com/apikey

2. **Option A: Als Umgebungsvariable**
   ```bash
   export GOOGLE_API_KEY=IhrKey
   docker-compose up -d
   ```

3. **Option B: Direkt in docker-compose.yml**
   Öffne `docker-compose.yml`, Zeile 29:
   ```yaml
   - GOOGLE_API_KEY=AIzaSy...IhrKeyHier
   ```

---

## 📁 Projekt-Struktur

```
/app/
├── backend/              # FastAPI Backend
│   ├── server.py
│   └── requirements.txt
├── frontend/             # React Frontend
│   ├── src/
│   └── package.json
├── Dockerfile.backend    # Python Container
├── Dockerfile.frontend   # React + Nginx Container
├── docker-compose.yml    # ← EINZIGE Config-Datei!
├── nginx.conf
└── README.md
```

**Keine .env Dateien mehr! Alles in docker-compose.yml.**

---

## 🔧 Verwaltung

```bash
# Starten
docker-compose up -d

# Stoppen
docker-compose down

# Logs ansehen
docker-compose logs -f

# Neu bauen (nach Code-Änderungen)
docker-compose build
docker-compose up -d

# Alles löschen (inkl. Daten!)
docker-compose down -v
```

---

## 🌐 Production Deployment

### Auf VPS/Server:

```bash
# 1. Git Clone
git clone https://github.com/ihr-repo/kochbuch.git
cd kochbuch

# 2. API Key setzen (optional)
export GOOGLE_API_KEY=IhrKey

# 3. Starten
docker-compose up -d

# 4. Öffnen
# http://server-ip
```

### Mit Domain & SSL:

```bash
# Nginx Reverse Proxy
sudo apt install nginx certbot python3-certbot-nginx

# SSL einrichten
sudo certbot --nginx -d ihre-domain.de
```

---

## ⚠️ Sicherheit

**Wenn Sie den API Key in `docker-compose.yml` eintragen:**

⚠️ **NICHT nach Git pushen!**

**Besser:**
```bash
# Immer als Umgebungsvariable
export GOOGLE_API_KEY=IhrKey
docker-compose up -d
```

**Oder:**
```bash
# In .bashrc / .zshrc
echo 'export GOOGLE_API_KEY=IhrKey' >> ~/.bashrc
```

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
docker-compose logs backend
```

### Frontend zeigt Fehler
```bash
docker-compose logs frontend
```

### MongoDB Connection Error
```bash
docker-compose restart mongodb
docker-compose restart backend
```

### Ports bereits belegt
```bash
# In docker-compose.yml Ports ändern:
# "8080:80"  statt "80:80"
# "8002:8001" statt "8001:8001"
```

---

## 💰 Kosten

- Server: $5-10/Monat (DigitalOcean, Hetzner)
- Google Gemini: Kostenlos (15 req/min)
- Domain: ~$10/Jahr
- **Total: ~$5-10/Monat**

---

## 📝 Lizenz

Freie Nutzung für private und kommerzielle Zwecke.
