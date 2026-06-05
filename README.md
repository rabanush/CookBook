# Kochbuch App

## Schnellstart

### Vor dem ersten Start:

```bash
# 1. .env Dateien erstellen (aus Templates)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. (Optional) Google API Key eintragen
nano backend/.env
# Ändern Sie: GOOGLE_API_KEY=IhrKey

# 3. Docker starten
docker-compose up -d

# 4. App öffnen
# http://localhost
```

## Struktur

```
/app/
├── backend/
│   ├── .env.example      # Template (IN GIT)
│   ├── .env              # Ihre Config (NICHT in Git)
│   └── ...
├── frontend/
│   ├── .env.example      # Template (IN GIT)
│   ├── .env              # Ihre Config (NICHT in Git)
│   └── ...
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── nginx.conf
```

## .env Dateien in Git?

**NEIN!** Aus Sicherheitsgründen:
- `.env` Dateien sind in `.gitignore`
- NUR `.env.example` Templates sind in Git
- Beim Deployment: Template kopieren und ausfüllen

## Deployment auf Server

```bash
# 1. Code auf Server
git clone https://github.com/ihr-repo/kochbuch.git
cd kochbuch

# 2. .env Dateien erstellen
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. API Key eintragen
nano backend/.env

# 4. Starten
docker-compose up -d
```

## Features

✅ Rezepte CRUD
✅ Zutaten Management  
✅ KI-Anleitungen (Gemini)
✅ KI-Bilder (Gemini)
✅ Filter & Suche
✅ Vintage Design

## Kosten

- Server: $5-10/Monat
- Google Gemini: Kostenlos (15 req/min)
- Total: ~$5-10/Monat