from fastapi import FastAPI, APIRouter, HTTPException, Header, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
import time
import requests
import base64
import asyncio
from datetime import datetime, timezone
import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
API_KEY = os.environ.get('API_KEY', '')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

# Configure Google Generative AI
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# File storage directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File storage functions (local filesystem)
def save_file(file_id: str, data: bytes, content_type: str) -> str:
    """Save file to local storage"""
    file_path = UPLOAD_DIR / f"{file_id}.jpg"
    with open(file_path, 'wb') as f:
        f.write(data)
    return str(file_path)

def load_file(file_id: str) -> tuple[bytes, str]:
    """Load file from local storage"""
    file_path = UPLOAD_DIR / f"{file_id}.jpg"
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_id} not found")
    with open(file_path, 'rb') as f:
        data = f.read()
    return data, "image/jpeg"

# Middleware for API key validation
async def verify_api_key(request: Request, call_next):
    if request.url.path == "/api/sync" and API_KEY:
        x_api_key = request.headers.get("x-api-key")
        if x_api_key != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    response = await call_next(request)
    return response

app.middleware("http")(verify_api_key)

# ============ MODELS ============

class IngredientCreate(BaseModel):
    name: str

class Ingredient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str

class RecipeIngredient(BaseModel):
    ingredient_id: str
    ingredient_name: str
    amount: str = ""  # New: quantity like "200g", "2 Stück"

class RecipeCreate(BaseModel):
    name: str
    calories: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    servings: int = Field(default=1, ge=1)
    ingredient_ids: List[str] = []
    ingredient_amounts: List[str] = []  # Parallel array to ingredient_ids
    instructions: str = ""  # New: cooking instructions

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    calories: Optional[int] = Field(default=None, ge=0)
    protein: Optional[int] = Field(default=None, ge=0)
    carbs: Optional[int] = Field(default=None, ge=0)
    fat: Optional[int] = Field(default=None, ge=0)
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    servings: Optional[int] = Field(default=None, ge=1)
    total_weight: Optional[int] = Field(default=None, ge=0)
    ingredient_ids: Optional[List[str]] = None
    ingredient_amounts: Optional[List[str]] = None
    instructions: Optional[str] = None

class Recipe(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    calories: int
    protein: int
    carbs: int
    fat: int
    rating: int = 0
    servings: int = 1
    total_weight: Optional[int] = None
    ingredients: List[RecipeIngredient] = []
    instructions: str = ""
    image_url: Optional[str] = None  # New: URL or storage path for recipe image
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SyncQueueEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipe_id: str
    name: str
    calories: int
    protein: int
    carbs: int
    fat: int
    timestamp_cooked: int

class GenerateInstructionsRequest(BaseModel):
    recipe_name: str
    ingredients: List[dict]  # [{"name": "Mehl", "amount": "200g"}]

class GenerateImageRequest(BaseModel):
    recipe_name: str

# ============ INGREDIENTS ENDPOINTS ============

@api_router.post("/ingredients", response_model=Ingredient)
async def create_ingredient(ingredient: IngredientCreate):
    if not ingredient.name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    
    # Capitalize first letter
    capitalized_name = ingredient.name.strip().capitalize()
    
    existing = await db.ingredients.find_one({"name": capitalized_name}, {"_id": 0})
    if existing:
        return Ingredient(**existing)
    
    ingredient_obj = Ingredient(name=capitalized_name)
    doc = ingredient_obj.model_dump()
    await db.ingredients.insert_one(doc)
    return ingredient_obj

@api_router.get("/ingredients", response_model=List[Ingredient])
async def get_ingredients():
    ingredients = await db.ingredients.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    return ingredients

@api_router.delete("/ingredients/{ingredient_id}")
async def delete_ingredient(ingredient_id: str):
    result = await db.ingredients.delete_one({"id": ingredient_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Zutat nicht gefunden")
    return {"message": "Zutat gelöscht"}

# ============ RECIPES ENDPOINTS ============

@api_router.post("/recipes", response_model=Recipe)
async def create_recipe(recipe: RecipeCreate):
    if not recipe.name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    
    # Get ingredient details with amounts
    ingredients = []
    for idx, ing_id in enumerate(recipe.ingredient_ids):
        ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
        if ing:
            amount = recipe.ingredient_amounts[idx] if idx < len(recipe.ingredient_amounts) else ""
            ingredients.append(RecipeIngredient(
                ingredient_id=ing["id"],
                ingredient_name=ing["name"],
                amount=amount
            ))
    
    recipe_obj = Recipe(
        name=recipe.name.strip(),
        calories=recipe.calories,
        protein=recipe.protein,
        carbs=recipe.carbs,
        fat=recipe.fat,
        servings=recipe.servings,
        ingredients=ingredients,
        instructions=recipe.instructions
    )
    
    doc = recipe_obj.model_dump()
    await db.recipes.insert_one(doc)
    return recipe_obj

@api_router.get("/recipes", response_model=List[Recipe])
async def get_recipes(
    search: Optional[str] = None,
    max_calories: Optional[int] = None,
    min_protein: Optional[int] = None,
    min_rating: Optional[int] = None,
    ingredient_ids: Optional[str] = None
):
    query = {}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    if max_calories is not None:
        query["calories"] = {"$lte": max_calories}
    
    if min_protein is not None:
        query["protein"] = {"$gte": min_protein}
    
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}
    
    if ingredient_ids:
        ing_list = ingredient_ids.split(",")
        query["ingredients.ingredient_id"] = {"$all": ing_list}
    
    recipes = await db.recipes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return recipes

@api_router.get("/recipes/random")
async def get_random_recipes(count: int = 6):
    """Get random recipes for discover page"""
    pipeline = [
        {"$sample": {"size": count}},
        {"$project": {"_id": 0}}
    ]
    recipes = await db.recipes.aggregate(pipeline).to_list(count)
    return recipes

@api_router.get("/recipes/match", response_model=List[dict])
async def match_recipes_by_ingredients(ingredient_ids: str, max_missing: int = 2):
    """Find recipes that match given ingredients, allowing up to max_missing ingredients to be absent"""
    if not ingredient_ids:
        return []
    
    ing_list = ingredient_ids.split(",")
    
    all_recipes = await db.recipes.find({}, {"_id": 0}).to_list(1000)
    
    matches = []
    for recipe in all_recipes:
        recipe_ing_ids = [ing["ingredient_id"] for ing in recipe.get("ingredients", [])]
        
        # Skip recipes with no ingredients
        if not recipe_ing_ids:
            continue
        
        matching = set(ing_list) & set(recipe_ing_ids)
        missing_count = len(recipe_ing_ids) - len(matching)
        
        if missing_count <= max_missing:
            missing_ings = []
            for ing_id in recipe_ing_ids:
                if ing_id not in ing_list:
                    ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
                    if ing:
                        missing_ings.append(ing["name"])
            
            matches.append({
                **recipe,
                "missing_count": missing_count,
                "missing_ingredients": missing_ings,
                "match_percentage": int((len(matching) / len(recipe_ing_ids) * 100))
            })
    
    matches.sort(key=lambda x: (x["missing_count"], -x["match_percentage"]))
    
    return matches

@api_router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str):
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return recipe

@api_router.put("/recipes/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: str, recipe_update: RecipeUpdate):
    existing = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    
    update_data = recipe_update.model_dump(exclude_unset=True)
    
    # Update ingredients if provided
    if "ingredient_ids" in update_data:
        ingredients = []
        amounts = update_data.get("ingredient_amounts", [])
        for idx, ing_id in enumerate(update_data["ingredient_ids"]):
            ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
            if ing:
                amount = amounts[idx] if idx < len(amounts) else ""
                ingredients.append(RecipeIngredient(
                    ingredient_id=ing["id"],
                    ingredient_name=ing["name"],
                    amount=amount
                ).model_dump())
        update_data["ingredients"] = ingredients
        del update_data["ingredient_ids"]
        if "ingredient_amounts" in update_data:
            del update_data["ingredient_amounts"]
    
    await db.recipes.update_one({"id": recipe_id}, {"$set": update_data})
    
    updated = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    return updated

@api_router.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str):
    result = await db.recipes.delete_one({"id": recipe_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return {"message": "Rezept gelöscht"}

@api_router.post("/recipes/{recipe_id}/cooked")
async def mark_recipe_cooked(recipe_id: str):
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    
    sync_entry = SyncQueueEntry(
        recipe_id=recipe_id,
        name=recipe["name"],
        calories=recipe["calories"],
        protein=recipe["protein"],
        carbs=recipe["carbs"],
        fat=recipe["fat"],
        timestamp_cooked=int(time.time())
    )
    
    doc = sync_entry.model_dump()
    await db.sync_queue.insert_one(doc)
    
    return {"message": "Rezept als gekocht markiert", "timestamp": sync_entry.timestamp_cooked}

# ============ AI FEATURES ============


@api_router.post("/recipes/generate-instructions")
async def generate_instructions(request: GenerateInstructionsRequest):
    """Generate cooking instructions using AI"""
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API Key nicht konfiguriert. Bitte GOOGLE_API_KEY in .env setzen.")
    
    try:
        # Build ingredient list text
        ing_text = ", ".join([f"{ing['amount']} {ing['name']}" if ing.get('amount') else ing['name'] 
                              for ing in request.ingredients])
        
        prompt = f"""Erstelle eine kurze, sachliche Kochanleitung für "{request.recipe_name}".

WICHTIG: Verwende NUR diese Zutaten:
{ing_text}

AUSNAHMEN (darfst du immer verwenden, auch wenn nicht aufgelistet):
- Wasser
- Alle gängigen Gewürze (Salz, Pfeffer, Paprika, Oregano, Thymian, Basilikum, Knoblauch, etc.)
- Olivenöl oder Sonnenblumenöl (gib an welches!)

WICHTIG ZU ÖL: Sage explizit WELCHES Öl verwendet werden soll (Olivenöl ODER Sonnenblumenöl). Beide sind vorhanden.

FEHLENDE ESSENTIELLE ZUTATEN:
Prüfe, ob für dieses Gericht "{request.recipe_name}" eine ESSENTIELLE Hauptzutat fehlt (z.B. Nudeln bei Spaghetti, Reis bei Risotto, Brot bei Sandwich, Fleisch bei Schnitzel, Eier bei Omelette, etc.).
Wenn eine solche Zutat fehlt, beginne die Anleitung mit:
"⚠️ HINWEIS: Für dieses Gericht wird [ZUTAT] benötigt, die nicht in der Zutatenliste aufgeführt ist."

Anforderungen:
- Kurze, einfache Sätze (max. 15 Wörter pro Satz)
- Keine Schachtelsätze oder Fachbegriffe
- Direkte Anweisungen im Aktiv
- Genaue Kochzeiten und Temperaturen
- Erwähne KEINE zusätzlichen Zutaten außer den Ausnahmen und dem Hinweis zu fehlenden Hauptzutaten
- 2-3 kurze Absätze

Beispiel guter Stil:
"Die Zutaten in einer Pfanne mit Olivenöl anbraten. 10 Minuten bei mittlerer Hitze garen. Mit Salz, Pfeffer und Paprika abschmecken."

Schreibe ohne Nummerierung als fortlaufenden Text."""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )
        
        instructions = response.text
        
        return {"instructions": instructions}
        
    except Exception as e:
        logging.error(f"Error generating instructions: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler bei der KI-Generierung: {str(e)}")


@api_router.post("/recipes/generate-image")
async def generate_recipe_image(request: GenerateImageRequest):
    import urllib.request
    import urllib.error
    import json

    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API Key fehlt")

    try:
        translation_model = genai.GenerativeModel('gemini-2.5-flash')
        translation_prompt = (
            f"Translate the German food '{request.recipe_name}' to English. "
            "Add a short, logical serving context if necessary (e.g., 'in a bowl with milk' for cereal, "
            "'in a rustic baking dish' for lasagna, 'in a deep bowl' for soup). "
            "Return ONLY the English description, nothing else."
        )
        
        translation_response = await asyncio.to_thread(
            translation_model.generate_content,
            translation_prompt
        )
        english_recipe_name = translation_response.text.strip()

        prompt = (
            f"Bright, highly detailed, appetizing food photography of: {english_recipe_name}. "
            "CRITICAL SCENE SETUP: The food is served in appropriate antique ceramic tableware "
            "(such as a rustic ceramic plate, or a deep ceramic bowl depending on the food). "
            "Underneath the tableware is a light-colored vintage fabric napkin, possibly with crochet or lace. "
            "The napkin and tableware rest on a warm, medium-brown wooden plank table. "
            "A vintage silver fork or spoon rests on the table. "
            "BACKGROUND: Softly blurred background showing a bright multi-pane window. "
            "On the windowsill, there are small terracotta pots containing green kitchen herbs. "
            "LIGHTING: Soft, diffused, bright daylight coming from the background window. "
            "High resolution, photorealistic, cinematic food styling."
        )

        model = "imagen-4.0-fast-generate-001"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={GOOGLE_API_KEY}"

        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9"
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        response = await asyncio.to_thread(urllib.request.urlopen, req)
        response_data = json.loads(response.read().decode('utf-8'))

        if 'predictions' in response_data and len(response_data['predictions']) > 0:
            b64_image = response_data['predictions'][0].get('bytesBase64Encoded')
            if b64_image:
                return {"image_base64": b64_image}

        raise HTTPException(status_code=500, detail="Google API lieferte kein Bild zurück.")

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        raise HTTPException(status_code=500, detail=f"Google API Fehler: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Bildgenerierung: {str(e)}")

#@api_router.post("/recipes/generate-image")
#async def generate_recipe_image(request: GenerateImageRequest):
#    import urllib.request
#    import urllib.error
#    import json
#    import asyncio
#
#    if not GOOGLE_API_KEY:
#        raise HTTPException(status_code=500, detail="Google API Key fehlt")
#
#    try:
#        prompt = (
#            f"Professional food photography of {request.recipe_name}. "
#	    "Widescreen format, landscape orientation, 16:9 aspect ratio. "
#            "Warm and inviting atmosphere, soft natural lighting, "
#            "presented on a rustic wooden surface or vintage tablecloth. "
#            "Lightly nostalgic and timeless look, homemade and appetizing appearance. "
#            "Prefer earthy, warm color tones such as beige, warm brown, and soft yellow. "
#            "Style: Vintage aesthetic, rustic presentation, warm tones, homemade comfort food, high resolution."
#        )
#
#        model = "gemini-2.5-flash-image"
#        url = (
#            f"https://generativelanguage.googleapis.com/v1beta/models/"
#            f"{model}:generateContent?key={GOOGLE_API_KEY}"  # ← Variable genutzt
#        )
#
#        payload = {
#            "contents": [
#                {
#                    "parts": [
#                        {"text": prompt}
#                    ]
#                }
#            ],
#            "generationConfig": {
#                "responseModalities": ["IMAGE"]
#            }
#        }
#
#        req = urllib.request.Request(
#            url,
#            data=json.dumps(payload).encode("utf-8"),
#            headers={"Content-Type": "application/json"},
#            method="POST"
#        )
#
#        response = await asyncio.to_thread(urllib.request.urlopen, req)
#        response_data = json.loads(response.read().decode("utf-8"))
#
#        candidates = response_data.get("candidates", [])
#        if candidates:
#            parts = candidates[0].get("content", {}).get("parts", [])
#            for part in parts:
#                if "inlineData" in part:
#                    b64_image = part["inlineData"].get("data")
#                    if b64_image:
#                        return {"image_base64": b64_image}
#
#        raise HTTPException(
#            status_code=500,
#            detail="Gemini API lieferte kein Bild zurück.")
#
#    except urllib.error.HTTPError as e:
#        error_body = e.read().decode("utf-8")
#        raise HTTPException(
#            status_code=500,
#            detail=f"Google API Fehler: {error_body}"
#        )
#    except Exception as e:
#        raise HTTPException(
#            status_code=500,
#            detail=f"Fehler bei der Bildgenerierung: {str(e)}"
#        )


# ============ IMAGE UPLOAD ============

@api_router.post("/recipes/{recipe_id}/upload-image")
async def upload_recipe_image(recipe_id: str, file: UploadFile = File(...)):
    """Upload image for a recipe"""
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien sind erlaubt")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to local filesystem
        save_file(recipe_id, content, file.content_type)
        
        # Update recipe with image URL
        image_url = f"/uploads/{recipe_id}.jpg"
        await db.recipes.update_one(
            {"id": recipe_id},
            {"$set": {"image_url": image_url, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"message": "Bild hochgeladen", "image_url": image_url}
        
    except Exception as e:
        logging.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Hochladen")

@api_router.get("/recipes/{recipe_id}/image")
async def get_recipe_image(recipe_id: str):
    """Get recipe image"""
    try:
        data, content_type = load_file(recipe_id)
        return Response(content=data, media_type=content_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden")
    except Exception as e:
        logging.error(f"Image retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Bildes")
    
# ============ SYNC ENDPOINT ============

@api_router.get("/sync", response_model=List[SyncQueueEntry])
async def sync_cooked_recipes(since: int = 0):
    """Get all cooked recipes since the given timestamp"""
    query = {"timestamp_cooked": {"$gt": since}}
    entries = await db.sync_queue.find(query, {"_id": 0}).sort("timestamp_cooked", -1).to_list(1000)
    return entries

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    logger.info("App started - ready to serve")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
