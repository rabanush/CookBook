# Kochbuch App - Deployment Guide

## Standalone Deployment (ohne Emergent)

Diese App wurde vollständig von Emergent-Abhängigkeiten befreit und kann eigenständig deployed werden.

## Voraussetzungen

1. **Docker & Docker Compose** installiert
2. **Google Gemini API Key** (kostenlos bei https://aistudio.google.com/apikey)

## Schnellstart

### 1. Environment Variables konfigurieren

```bash
cp .env.example .env
```

Öffne `.env` und trage deinen Google API Key ein:

```
GOOGLE_API_KEY=dein_google_api_key_hier
```

### 2. App starten

```bash
docker-compose up -d
```

Die App ist nun erreichbar unter:
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **MongoDB**: localhost:27017

### 3. App stoppen

```bash
docker-compose down
```

### 4. App mit Daten löschen

```bash
docker-compose down -v
```

## Production Deployment

### Mit eigenem Domain

1. Ersetze in `docker-compose.yml` die Umgebungsvariable:
   ```yaml
   - REACT_APP_BACKEND_URL=https://api.deine-domain.de
   ```

2. Konfiguriere Reverse Proxy (z.B. Nginx/Caddy) für HTTPS

3. Verwende Docker Compose Production Override:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Entwicklung

### Backend lokal starten

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

### Frontend lokal starten

```bash
cd frontend
yarn install
yarn start
```

## Features

- ✅ Rezepte erstellen, bearbeiten, löschen
- ✅ KI-generierte Kochanleitungen (Gemini 3 Flash)
- ✅ KI-generierte Rezeptbilder (Gemini Nano Banana)
- ✅ Zutaten-Management
- ✅ Filter nach Kalorien, Protein, Bewertung
- ✅ Vintage Kochbuch Design
- ✅ MongoDB Datenbank
- ✅ Docker ready

## Troubleshooting

### Fehler: "AI-Funktion nicht konfiguriert"

→ Google API Key in `.env` fehlt oder ungültig

### Backend startet nicht

```bash
docker-compose logs backend
```

### Frontend kann Backend nicht erreichen

→ Überprüfe `REACT_APP_BACKEND_URL` in `docker-compose.yml`

## Kosten

- **MongoDB**: Kostenlos (selbst gehostet)
- **Hosting**: Abhängig von Provider (z.B. DigitalOcean $5/Monat)
- **Google Gemini API**: Großzügiges kostenloses Kontingent, danach Pay-as-you-go

## Support

Bei Fragen oder Problemen: GitHub Issues