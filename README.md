# 🍳 Kochbuch App - Standalone Deployment

## ✅ Vollständig unabhängig von Emergent

- Keine Emergent-Dependencies
- Lokaler File Storage
- Eigener Google Gemini API Key
- Docker-ready

---

## 🚀 Schnellstart (Docker)

### Voraussetzungen
- Docker & Docker Compose installiert
- Google Gemini API Key (optional, nur für KI-Features)

### Installation in 3 Schritten

```bash
# 1. Google API Key eintragen (optional)
nano backend/.env
# Ändern Sie: GOOGLE_API_KEY=IhrKeyHier

# 2. Docker Container starten
docker-compose up -d

# 3. App öffnen
# http://localhost (oder http://ihre-server-ip)
```

**Das war's! Die App läuft jetzt.** 🎉

---

## 📋 Features

✅ Rezepte erstellen, bearbeiten, löschen
✅ Zutaten-Management
✅ Filter (Kalorien, Protein, Bewertung)
✅ Suche
✅ KI-generierte Kochanleitungen (Gemini 2.0 Flash)
✅ KI-generierte Rezeptbilder (Gemini 2.0)
✅ Vintage "Worn Recipe Journal" Design
✅ Responsive (Desktop & Tablet)

---

## 🔧 Verwaltung

```bash
# Status prüfen
docker-compose ps

# Logs ansehen
docker-compose logs -f

# Neu starten
docker-compose restart

# Stoppen
docker-compose down

# Alles löschen (inkl. Daten)
docker-compose down -v
```

---

## 🔑 Google API Key Setup

### Warum?
Nur für KI-Features:
- KI-Anleitung generieren
- KI-Bild generieren

**Rezepte & Zutaten funktionieren OHNE API Key!**

### Wie?

1. **API Key holen** (kostenlos):
   https://aistudio.google.com/apikey

2. **Eintragen**:
   ```bash
   nano backend/.env
   ```
   
   Ändern Sie:
   ```
   GOOGLE_API_KEY=IhrKeyHier
   ```

3. **Backend neu starten**:
   ```bash
   docker-compose restart backend
   ```

---

## 🌐 Production Deployment

### Mit eigener Domain

1. **Domain auf Server zeigen** (A-Record)

2. **SSL einrichten** (Let's Encrypt):
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d ihre-domain.de
   ```

3. **Fertig!** App läuft unter `https://ihre-domain.de`

---

## 📁 Projekt-Struktur

```
/app/
├── backend/              # FastAPI Backend
│   ├── server.py        # API Endpoints
│   ├── .env             # Backend Config (API Key hier!)
│   └── requirements.txt
├── frontend/             # React Frontend
│   ├── src/
│   │   ├── App.js       # Hauptkomponente
│   │   └── App.css      # Vintage Styling
│   ├── .env             # Frontend Config
│   └── package.json
├── docker-compose.yml    # Orchestrierung
├── Dockerfile.backend    # Backend Container
├── Dockerfile.frontend   # Frontend Container
├── nginx.conf           # Reverse Proxy
└── README.md            # Diese Datei
```

---

## ❓ Mehrere Dockerfiles?

**JA, das ist korrekt!**

- `Dockerfile.backend` → Python/FastAPI Container
- `Dockerfile.frontend` → Node Build + Nginx Container
- `docker-compose.yml` → Verbindet beide + MongoDB

**Sie müssen NUR `docker-compose up -d` ausführen!**

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
docker-compose logs backend
```
Häufigste Ursache: MongoDB noch nicht bereit → warten Sie 10 Sekunden

### Frontend zeigt "Cannot reach backend"
```bash
docker-compose logs nginx
```
Prüfen Sie: Backend läuft? `docker-compose ps`

### KI-Funktionen funktionieren nicht
```bash
# API Key prüfen
docker-compose exec backend env | grep GOOGLE_API_KEY

# Sollte zeigen: GOOGLE_API_KEY=Ihr_Key
```

### MongoDB Connection Error
```bash
docker-compose restart mongodb
docker-compose restart backend
```

---

## 💰 Kosten

| Service | Kosten |
|---------|--------|
| Server (VPS) | $5-10/Monat |
| Google Gemini API | Kostenlos (15 req/min) |
| MongoDB | Kostenlos (selbst gehostet) |
| Domain | ~$10/Jahr |
| SSL | Kostenlos (Let's Encrypt) |
| **Total** | **~$5-10/Monat** |

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `docker-compose logs`
2. Status prüfen: `docker-compose ps`
3. Neu starten: `docker-compose restart`

---

## 📝 Lizenz

Freie Nutzung für private und kommerzielle Zwecke.

---

**Viel Spaß mit Ihrer Kochbuch-App! 🍳**