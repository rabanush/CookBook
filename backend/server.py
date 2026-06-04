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
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone, ImageContent
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
API_KEY = os.environ.get('API_KEY', '')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Object Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "cookbook-app"
storage_key = None

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize object storage
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logging.info("Object storage initialized successfully")
        return storage_key
    except Exception as e:
        logging.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file to storage"""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple[bytes, str]:
    """Download file from storage"""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

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
    ingredients: List[RecipeIngredient] = []
    instructions: str = ""
    image_url: Optional[str] = None  # New: URL or storage path for recipe image
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
    
    existing = await db.ingredients.find_one({"name": ingredient.name.strip()}, {"_id": 0})
    if existing:
        return Ingredient(**existing)
    
    ingredient_obj = Ingredient(name=ingredient.name.strip())
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
        {"$sample": {"size": count}}
    ]
    recipes = await db.recipes.aggregate(pipeline).to_list(count)
    # Remove _id
    for recipe in recipes:
        recipe.pop("_id", None)
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
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI-Funktion nicht konfiguriert")
    
    try:
        # Build ingredient list text
        ing_text = ", ".join([f"{ing['amount']} {ing['name']}" if ing.get('amount') else ing['name'] 
                              for ing in request.ingredients])
        
        prompt = f"""Erstelle eine kurze, sachliche Kochanleitung für "{request.recipe_name}".

WICHTIG: Verwende NUR diese Zutaten (keine anderen hinzufügen!):
{ing_text}

Anforderungen:
- Kurze, einfache Sätze (max. 15 Wörter pro Satz)
- Keine Schachtelsätze oder Fachbegriffe
- Direkte Anweisungen im Aktiv
- Genaue Kochzeiten und Temperaturen
- Erwähne KEINE zusätzlichen Zutaten, die nicht oben aufgelistet sind
- 2-3 kurze Absätze

Beispiel guter Stil:
"Die Zutaten in einer Pfanne anbraten. 10 Minuten bei mittlerer Hitze garen. Mit Gewürzen abschmecken."

Schreibe ohne Nummerierung als fortlaufenden Text."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="Du schreibst moderne, prägnante Kochanleitungen. Verwende kurze, klare Sätze ohne Fachsprache. Sei direkt und praktisch. WICHTIG: Verwende nur die Zutaten, die explizit genannt werden."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        # Use non-streaming for this endpoint
        result = await chat.send_message(UserMessage(text=prompt))
        # Gemini returns string directly
        instructions = result if isinstance(result, str) else result.content
        
        return {"instructions": instructions}
        
    except Exception as e:
        logging.error(f"Error generating instructions: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler bei der KI-Generierung: {str(e)}")

@api_router.post("/recipes/generate-image")
async def generate_recipe_image(request: GenerateImageRequest):
    """Generate recipe image using AI"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI-Funktion nicht konfiguriert")
    
    try:
        # Create a vintage-style prompt that fits the cookbook aesthetic
        prompt = f"""Erstelle ein Bild von {request.recipe_name} im Stil eines alten Familienkochbuchs. 

Das Bild soll:
- Warm und einladend wirken
- Natürliches, weiches Licht haben
- Auf einer rustikalen Holzoberfläche oder vintage Tischdecke präsentiert sein
- Einen leicht nostalgischen, zeitlosen Look haben
- Das Gericht appetitlich und hausgemacht zeigen
- Erdige, warme Farbtöne bevorzugen (Beigetöne, warmes Braun, sanftes Gelb)

Stil: Professional food photography with vintage aesthetic, soft natural lighting, rustic presentation, warm tones, homemade comfort food look"""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are an expert food photographer specializing in vintage, nostalgic cookbook imagery."
        ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        
        # Generate image
        text_response, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
        
        if not images or len(images) == 0:
            raise HTTPException(status_code=500, detail="Kein Bild generiert")
        
        # Get the first image (already base64 encoded from Gemini)
        image_base64 = images[0]['data']
        
        return {"image_base64": image_base64, "content_type": images[0].get('mime_type', 'image/png')}
        
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler bei der Bild-Generierung: {str(e)}")

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
        # Read file data
        data = await file.read()
        
        # Generate unique storage path (with timestamp to avoid caching issues)
        ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        timestamp = int(time.time() * 1000)  # Milliseconds for uniqueness
        path = f"{APP_NAME}/recipes/{recipe_id}/{timestamp}_{uuid.uuid4()}.{ext}"
        
        # Upload to storage
        result = put_object(path, data, file.content_type)
        
        # Update recipe with new image path (overwrites old one)
        await db.recipes.update_one(
            {"id": recipe_id},
            {"$set": {"image_url": result["path"]}}
        )
        
        return {"message": "Bild hochgeladen", "path": result["path"]}
        
    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Upload: {str(e)}")

@api_router.get("/recipes/{recipe_id}/image")
async def get_recipe_image(recipe_id: str):
    """Get recipe image"""
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe or not recipe.get("image_url"):
        raise HTTPException(status_code=404, detail="Bild nicht gefunden")
    
    try:
        data, content_type = get_object(recipe["image_url"])
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logging.error(f"Error fetching image: {e}")
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")

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
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (non-critical): {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
