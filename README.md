# Familien-Kochbuch Web-Anwendung

Eine moderne, responsive Kochbuch-Webanwendung mit "Worn Recipe Journal" Design.

## Features

### Rezeptverwaltung
- ✅ Rezepte erstellen, bearbeiten und löschen
- ✅ Nährwertangaben (Kalorien, Protein, Kohlenhydrate, Fett)
- ✅ Zutaten zu Rezepten hinzufügen
- ✅ Rezepte mit 1-5 Sternen bewerten
- ✅ Rezepte als "gekocht" markieren

### Such- und Filterfunktionen
- ✅ Textsuche nach Rezeptnamen
- ✅ Filterung nach Bewertung (1-5 Sterne)
- ✅ Filterung nach Kalorienbereich (Min/Max)
- ✅ Intelligente Rezeptsuche nach vorhandenen Zutaten
- ✅ "Fast-Match" Funktion: Findet Rezepte, denen nur 1-2 Zutaten fehlen

### Design
- ✅ "Worn Recipe Journal" Ästhetik (alte Familien-Rezeptbuch-Optik)
- ✅ Pergament-Hintergrund mit warmen Beigetönen
- ✅ Gestrichelte Trenner im Karteikartendesign
- ✅ Handgeschriebene Schriftarten (Kalam, Special Elite)
- ✅ Responsive für PC und iPad (Hoch- und Querformat)

### API für Android-App
- ✅ `/api/sync` Endpunkt für gekochte Rezepte
- ✅ API-Key-Authentifizierung (optional über Umgebungsvariable)

## Tech-Stack

- **Frontend**: React 19, Axios, Lucide Icons, Sonner (Toasts)
- **Backend**: FastAPI, Motor (MongoDB Async), Pydantic
- **Datenbank**: MongoDB
- **Styling**: Vanilla CSS mit Google Fonts

## API-Dokumentation

### Rezepte

- `GET /api/recipes` - Alle Rezepte abrufen
- `POST /api/recipes` - Neues Rezept erstellen
- `GET /api/recipes/{id}` - Einzelnes Rezept abrufen
- `PUT /api/recipes/{id}` - Rezept aktualisieren
- `DELETE /api/recipes/{id}` - Rezept löschen
- `POST /api/recipes/{id}/cooked` - Rezept als gekocht markieren

### Zutaten

- `GET /api/ingredients` - Alle Zutaten abrufen
- `POST /api/ingredients` - Neue Zutat erstellen
- `DELETE /api/ingredients/{id}` - Zutat löschen

### Intelligente Suche

- `GET /api/recipes/match?ingredient_ids={ids}&max_missing={num}` - Findet passende Rezepte

### Sync (für Android-App)

- `GET /api/sync?since={timestamp}` - Gekochte Rezepte seit Zeitstempel