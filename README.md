# 🍳 Kochbuch App - Standalone Deployment

### Schritt 1: OHNE API Key (Grund Setup)

frontend/.env Datei erstellenen
REACT_APP_BACKEND_URL=URL
```bash
docker-compose up -d
```

**Fertig!** App läuft auf http://localhost bzw der angegebenen URL

### Schritt 2: MIT API Key (KI-Features) Für die Bilderstellungs KI muss ein Abrechnungskonto für Gemini erstellt werden.

in `docker-compose.yml` eintragen (Zeile 29):

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

## 🌐 Production Deployment

### Auf VPS/Server:

```bash
# 1. Git Clone
git clone https://github.com/rabanush/CookBook.git
cd CookBook

# 2. API Key setzen (optional)
GOOGLE_API_KEY=IhrKey

# 3. Frontend mit Backend verknüpfen über .env file

# 4. Starten
docker-compose up -d

# 5. Öffnen
# http://server-ip

---

## ⚠️ Sicherheit

**Wenn Sie den API Key in `docker-compose.yml` eintragen:**

⚠️ **NICHT nach Git pushen!**

**Besser:**
```bash
# Immer als Umgebungsvariable
export GOOGLE_API_KEY=IhrKey

