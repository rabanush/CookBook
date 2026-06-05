# 🚀 Kochbuch App - Deployment Anleitung

## ✅ Nur EINE Stelle für Google API Key!

---

## 📦 Docker Deployment (Empfohlen)

### Schritt 1: Dateien auf Server kopieren

Kopieren Sie den kompletten `/app` Ordner auf Ihren Server.

### Schritt 2: Google API Key eintragen

**NUR DIESE DATEI bearbeiten:**
```bash
nano backend/.env
```

Fügen Sie diese Zeile hinzu:
```
GOOGLE_API_KEY=IHR_GOOGLE_API_KEY_HIER
```

Die Datei sollte so aussehen:
```env
MONGO_URL=mongodb://mongodb:27017
DB_NAME=cookbook
CORS_ORIGINS=*
API_KEY=
GOOGLE_API_KEY=AIzaSy...IhrKeyHier
```

### Schritt 3: Docker starten

```bash
cd /pfad/zu/app
docker-compose up -d
```

### Schritt 4: App aufrufen

- Frontend: http://localhost (oder http://ihre-server-ip)
- Backend: http://localhost:8001

**FERTIG!** 🎉

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
```

---

## 🔑 Google API Key holen

1. Gehen Sie zu: https://aistudio.google.com/apikey
2. Erstellen Sie einen neuen API Key (kostenlos)
3. Kopieren Sie den Key
4. Tragen Sie ihn in `backend/.env` ein

---

## 🌐 Production mit Domain

### Frontend URL anpassen

Bearbeiten Sie `docker-compose.yml`:
```yaml
frontend:
  environment:
    - REACT_APP_BACKEND_URL=https://ihre-domain.de
```

### SSL einrichten

```bash
# Nginx installieren (falls nicht vorhanden)
sudo apt install nginx

# SSL mit Let's Encrypt
sudo certbot --nginx -d ihre-domain.de
```

---

## ❓ Troubleshooting

### Backend startet nicht
```bash
docker-compose logs backend
```
→ Häufigste Ursache: `GOOGLE_API_KEY` fehlt in `backend/.env`

### KI-Funktionen funktionieren nicht
```bash
# Prüfen ob API Key gesetzt ist
docker-compose exec backend env | grep GOOGLE_API_KEY
```

### MongoDB Connection Error
```bash
# MongoDB neu starten
docker-compose restart mongodb
```

---

## 💰 Kosten

- Server: $5-10/Monat
- Google Gemini API: Kostenlos (großzügiges Limit)
- Domain: ~$10/Jahr
- **Total: ~$5-10/Monat**

---

## 📋 Checkliste vor Go-Live

- [ ] Google API Key in `backend/.env` eingetragen
- [ ] `docker-compose up -d` erfolgreich
- [ ] Frontend erreichbar (http://localhost)
- [ ] Rezept erstellen funktioniert
- [ ] KI-Anleitung generieren funktioniert
- [ ] KI-Bild generieren funktioniert
- [ ] (Optional) SSL/HTTPS eingerichtet
- [ ] (Optional) Domain konfiguriert

---

**Das war's! Nur EINE Datei bearbeiten, Docker starten, fertig! 🚀**