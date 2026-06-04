from fastapi import FastAPI, APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Key from environment (optional)
API_KEY = os.environ.get('API_KEY', '')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Middleware for API key validation (only if API_KEY is set)
async def verify_api_key(request: Request, call_next):
    # Only check /api/sync endpoint and only if API_KEY is configured
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

class RecipeCreate(BaseModel):
    name: str
    calories: int = Field(ge=0)
    protein: int = Field(ge=0)
    carbs: int = Field(ge=0)
    fat: int = Field(ge=0)
    ingredient_ids: List[str] = []

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    calories: Optional[int] = Field(default=None, ge=0)
    protein: Optional[int] = Field(default=None, ge=0)
    carbs: Optional[int] = Field(default=None, ge=0)
    fat: Optional[int] = Field(default=None, ge=0)
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    ingredient_ids: Optional[List[str]] = None

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

# ============ INGREDIENTS ENDPOINTS ============

@api_router.post("/ingredients", response_model=Ingredient)
async def create_ingredient(ingredient: IngredientCreate):
    if not ingredient.name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    
    # Check if ingredient already exists
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
    
    # Get ingredient details
    ingredients = []
    for ing_id in recipe.ingredient_ids:
        ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
        if ing:
            ingredients.append(RecipeIngredient(
                ingredient_id=ing["id"],
                ingredient_name=ing["name"]
            ))
    
    recipe_obj = Recipe(
        name=recipe.name.strip(),
        calories=recipe.calories,
        protein=recipe.protein,
        carbs=recipe.carbs,
        fat=recipe.fat,
        ingredients=ingredients
    )
    
    doc = recipe_obj.model_dump()
    await db.recipes.insert_one(doc)
    return recipe_obj

@api_router.get("/recipes", response_model=List[Recipe])
async def get_recipes(
    search: Optional[str] = None,
    min_calories: Optional[int] = None,
    max_calories: Optional[int] = None,
    min_rating: Optional[int] = None,
    ingredient_ids: Optional[str] = None
):
    query = {}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    if min_calories is not None:
        query["calories"] = query.get("calories", {})
        query["calories"]["$gte"] = min_calories
    
    if max_calories is not None:
        query["calories"] = query.get("calories", {})
        query["calories"]["$lte"] = max_calories
    
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}
    
    if ingredient_ids:
        ing_list = ingredient_ids.split(",")
        query["ingredients.ingredient_id"] = {"$all": ing_list}
    
    recipes = await db.recipes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return recipes

@api_router.get("/recipes/match", response_model=List[dict])
async def match_recipes_by_ingredients(ingredient_ids: str, max_missing: int = 2):
    """Find recipes that match given ingredients, allowing up to max_missing ingredients to be absent"""
    if not ingredient_ids:
        return []
    
    ing_list = ingredient_ids.split(",")
    
    # Get all recipes
    all_recipes = await db.recipes.find({}, {"_id": 0}).to_list(1000)
    
    matches = []
    for recipe in all_recipes:
        recipe_ing_ids = [ing["ingredient_id"] for ing in recipe.get("ingredients", [])]
        
        # Skip recipes with no ingredients
        if not recipe_ing_ids:
            continue
        
        # Count how many ingredients match
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
    
    # Sort by missing count and match percentage
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
        for ing_id in update_data["ingredient_ids"]:
            ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
            if ing:
                ingredients.append(RecipeIngredient(
                    ingredient_id=ing["id"],
                    ingredient_name=ing["name"]
                ).model_dump())
        update_data["ingredients"] = ingredients
        del update_data["ingredient_ids"]
    
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

# ============ SYNC ENDPOINT (for Android App) ============

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()