import { useState, useEffect, useCallback, useMemo } from "react";
import "@/App.css";
import axios from "axios";
import { Plus, Search, Star, ChefHat, X, Edit2, Trash2, Filter, Sparkles, Upload, Camera, ArrowLeft, Shuffle, Minus } from "lucide-react";
import { toast } from "sonner";
import { BrowserRouter, Routes, Route, useNavigate, useParams, Link, useLocation } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/recipe/:id" element={<RecipeDetailPage />} />
        <Route path="/discover" element={<DiscoverPage />} />
      </Routes>
    </BrowserRouter>
  );
}

// ============ HOME PAGE ============
function HomePage() {
  const navigate = useNavigate();
  const [recipes, setRecipes] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [filteredRecipes, setFilteredRecipes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [showIngredientMatch, setShowIngredientMatch] = useState(false);
  const [matchedRecipes, setMatchedRecipes] = useState([]);
  const [recentlyUsedIngredients, setRecentlyUsedIngredients] = useState([]);
  const [editIngredientsMode, setEditIngredientsMode] = useState(false);
  const [deletingIngredientId, setDeletingIngredientId] = useState(null);
  const [filters, setFilters] = useState({
    minRating: 0,
    maxCalories: "",
    minProtein: ""
  });
  const [newIngredient, setNewIngredient] = useState("");
  const [filteredIngredients, setFilteredIngredients] = useState([]);
  const [formData, setFormData] = useState({
    name: "",
    calories: "",
    protein: "",
    carbs: "",
    fat: "",
    servings: 1,
    ingredient_ids: [],
    ingredient_amounts: [],
    instructions: "",
    image_url: null
  });
  const [generatingInstructions, setGeneratingInstructions] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [generatedImageBase64, setGeneratedImageBase64] = useState(null);
  const [uploadedImageFile, setUploadedImageFile] = useState(null);

  // Memoized sorted ingredients for sidebar (Performance optimization)
  const sortedSidebarIngredients = useMemo(() => {
    if (!Array.isArray(ingredients)) return [];
    return [...ingredients].sort((a, b) => {
      const aRecent = recentlyUsedIngredients.indexOf(a.id);
      const bRecent = recentlyUsedIngredients.indexOf(b.id);
      
      if (aRecent !== -1 && bRecent !== -1) return aRecent - bRecent;
      if (aRecent !== -1) return -1;
      if (bRecent !== -1) return 1;
      return a.name.localeCompare(b.name);
    });
  }, [ingredients, recentlyUsedIngredients]);

  // Memoized sorted ingredients for form (Performance optimization)
  const sortedFormIngredients = useMemo(() => {
    if (!Array.isArray(ingredients)) return [];
    return [...ingredients].sort((a, b) => {
      const aSelected = formData.ingredient_ids.includes(a.id);
      const bSelected = formData.ingredient_ids.includes(b.id);
      
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      
      const aRecent = recentlyUsedIngredients.indexOf(a.id);
      const bRecent = recentlyUsedIngredients.indexOf(b.id);
      
      if (aRecent !== -1 && bRecent !== -1) return aRecent - bRecent;
      if (aRecent !== -1) return -1;
      if (bRecent !== -1) return 1;
      
      return a.name.localeCompare(b.name);
    });
  }, [ingredients, formData.ingredient_ids, recentlyUsedIngredients]);

  const fetchRecipes = useCallback(async (currentFilters) => {
    try {
      const params = {
        search: searchTerm,
        minRating: currentFilters.minRating > 0 ? currentFilters.minRating : undefined,
        max_calories: currentFilters.maxCalories || undefined,
        min_protein: currentFilters.minProtein || undefined,
      };
      const response = await axios.get(`${API}/recipes`, { params });
      if (Array.isArray(response.data)) {
        setRecipes(response.data);
        setFilteredRecipes(response.data);
      } else {
        console.error("API /recipes did not return an array:", response.data);
        setRecipes([]);
        setFilteredRecipes([]);
      }
    } catch (error) {
      toast.error("Fehler beim Laden der Rezepte");
      setRecipes([]);
      setFilteredRecipes([]);
    }
  }, [searchTerm]);

  const fetchIngredients = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/ingredients`);
      if (Array.isArray(response.data)) {
        setIngredients(response.data);
      } else {
        console.error("API /ingredients did not return an array:", response.data);
        setIngredients([]);
      }
    } catch (error) {
      toast.error("Fehler beim Laden der Zutaten");
      setIngredients([]);
    }
  }, []);

  // This effect now triggers re-fetching from the backend when filters change.
  useEffect(() => {
    fetchRecipes(filters);
  }, [filters, searchTerm, fetchRecipes]);

  useEffect(() => {
    fetchIngredients();
  }, [fetchIngredients]);

  const generateInstructions = async () => {
    if (!formData.name || formData.ingredient_ids.length === 0) {
      toast.error("Bitte Namen und Zutaten angeben");
      return;
    }

    setGeneratingInstructions(true);
    try {
      const ingredientsData = formData.ingredient_ids.map((id, idx) => {
        const ing = ingredients.find(i => i.id === id);
        return {
          name: ing?.name || "",
          amount: formData.ingredient_amounts[idx] || ""
        };
      });

      const response = await axios.post(`${API}/recipes/generate-instructions`, {
        recipe_name: formData.name,
        ingredients: ingredientsData
      });

      setFormData({ ...formData, instructions: response.data.instructions });
      toast.success("Kochanleitung erstellt!");
    } catch (error) {
      toast.error("Fehler bei der KI-Generierung");
    } finally {
      setGeneratingInstructions(false);
    }
  };

  const generateImage = async () => {
    if (!formData.name) {
      toast.error("Bitte Rezeptnamen angeben");
      return;
    }

    setGeneratingImage(true);
    try {
      const response = await axios.post(`${API}/recipes/generate-image`, {
        recipe_name: formData.name
      });

      setGeneratedImageBase64(response.data.image_base64);
      toast.success("Bild erstellt!");
    } catch (error) {
      toast.error("Fehler bei der Bild-Generierung");
    } finally {
      setGeneratingImage(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Comprehensive validation
    if (!formData.name.trim()) {
      toast.error("Name ist erforderlich");
      return;
    }

    if (!formData.instructions.trim()) {
      toast.error("Kochanleitung ist erforderlich");
      return;
    }

    if (formData.ingredient_ids.length === 0) {
      toast.error("Mindestens eine Zutat ist erforderlich");
      return;
    }

    if (!generatedImageBase64 && !uploadedImageFile && !editingRecipe?.image_url) {
      toast.error("Bild ist erforderlich (KI generieren oder hochladen)");
      return;
    }

    if (formData.calories < 0 || formData.protein < 0 || formData.carbs < 0 || formData.fat < 0) {
      toast.error("Nährwerte müssen positiv sein");
      return;
    }

    try {
      let finalImageUrl = editingRecipe?.image_url || null;

      // Step 1: Upload image if a new one is present
      if (generatedImageBase64) {
        const uploadResponse = await axios.post(`${API}/recipes/upload-base64-image`, {
          image_base64: generatedImageBase64,
        });
        finalImageUrl = uploadResponse.data.image_url;
      } else if (uploadedImageFile) {
        // This path is now less likely but kept as a fallback
        const fileFormData = new FormData();
        fileFormData.append("file", uploadedImageFile);
        // We need a temporary upload endpoint or handle this differently
        // For now, let's assume we need a recipe ID first, which is a flaw.
        // The new base64 endpoint is better.
        toast.error("File upload logic needs rework, please use AI generation for now.");
        return;
      }

      const payload = {
        ...formData,
        calories: parseInt(formData.calories) || 0,
        protein: parseInt(formData.protein) || 0,
        carbs: parseInt(formData.carbs) || 0,
        fat: parseInt(formData.fat) || 0,
        servings: parseInt(formData.servings) || 1,
        image_url: finalImageUrl
      };

      if (editingRecipe) {
        await axios.put(`${API}/recipes/${editingRecipe.id}`, payload);
        toast.success("Rezept aktualisiert");
      } else {
        await axios.post(`${API}/recipes`, payload);
        toast.success("Rezept erstellt");
      }

      fetchRecipes(filters);
      resetForm();
    } catch (error) {
      toast.error(editingRecipe ? "Fehler beim Aktualisieren" : "Fehler beim Erstellen");
    }
  };

  const handleEdit = (recipe) => {
    setEditingRecipe(recipe);
    setFormData({
      name: recipe.name,
      calories: recipe.calories,
      protein: recipe.protein,
      carbs: recipe.carbs,
      fat: recipe.fat,
      servings: recipe.servings || 1,
      ingredient_ids: recipe.ingredients.map(i => i.ingredient_id),
      ingredient_amounts: recipe.ingredients.map(i => i.amount || ""),
      instructions: recipe.instructions || "",
      image_url: recipe.image_url || null
    });
    setShowForm(true);
    // Clear any generated/uploaded images when editing
    setGeneratedImageBase64(null);
    setUploadedImageFile(null);
  };

  const handleDelete = async (recipe) => {
    try {
      // Backend löschen
      await axios.delete(`${API}/recipes/${recipe.id}`);
      
      // Neu laden vom Server
      await fetchRecipes(filters);
      
      toast.success("Rezept gelöscht");
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error("Delete error:", error);
      }
      toast.error("Fehler beim Löschen");
    }
  };

  const handleCooked = async (recipe) => {
    try {
      await axios.post(`${API}/recipes/${recipe.id}/cooked`);
      toast.success(`${recipe.name} als gekocht markiert!`);
    } catch (error) {
      toast.error("Fehler beim Markieren");
    }
  };

  const handleRating = async (recipeId, rating) => {
    try {
      await axios.put(`${API}/recipes/${recipeId}`, { rating });
      toast.success("Bewertung gespeichert");
      fetchRecipes(filters);
    } catch (error) {
      toast.error("Fehler beim Bewerten");
    }
  };

  const resetForm = () => {
    setFormData({ 
      name: "", calories: "", protein: "", carbs: "", fat: "", 
      servings: 1,
      ingredient_ids: [], ingredient_amounts: [], instructions: "",
      image_url: null
    });
    setEditingRecipe(null);
    setShowForm(false);
    setGeneratedImageBase64(null);
    setUploadedImageFile(null);
  };

  const addIngredient = async () => {
    console.log("🔧 addIngredient called, newIngredient:", newIngredient);
    console.log("🔧 API value:", API);
    
    if (!newIngredient.trim()) {
      console.log("❌ Empty ingredient name, returning");
      return;
    }
    
    try {
      console.log("📤 Making POST request to:", `${API}/ingredients`);
      const response = await axios.post(`${API}/ingredients`, { name: newIngredient });
      const newIng = response.data;
      console.log("✅ Ingredient added:", newIng);
      setIngredients([...ingredients, newIng]);
      
      // Automatically select the new ingredient
      setFormData({
        ...formData,
        ingredient_ids: [...formData.ingredient_ids, newIng.id],
        ingredient_amounts: [...formData.ingredient_amounts, ""]
      });
      
      // Add to recently used (move to top)
      setRecentlyUsedIngredients(prev => {
        const filtered = prev.filter(id => id !== newIng.id);
        return [newIng.id, ...filtered].slice(0, 20);
      });
      
      setNewIngredient("");
      setFilteredIngredients([]);
      toast.success(`${newIng.name} hinzugefügt und ausgewählt`);
    } catch (error) {
      toast.error("Fehler beim Hinzufügen der Zutat");
    }
  };

  const handleIngredientSearch = (value) => {
    setNewIngredient(value);
    if (value.trim()) {
      const filtered = ingredients.filter(ing => 
        ing.name.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredIngredients(filtered);
    } else {
      setFilteredIngredients([]);
    }
  };

  const selectIngredient = (ing) => {
    // Check if already added
    if (formData.ingredient_ids.includes(ing.id)) {
      toast.error(`${ing.name} wurde bereits hinzugefügt`);
      return;
    }
    
    setFormData({
      ...formData,
      ingredient_ids: [...formData.ingredient_ids, ing.id],
      ingredient_amounts: [...formData.ingredient_amounts, ""]
    });
    
    // Add to recently used (move to top)
    setRecentlyUsedIngredients(prev => {
      const filtered = prev.filter(id => id !== ing.id);
      return [ing.id, ...filtered].slice(0, 20); // Keep only last 20
    });
    
    setNewIngredient("");
    setFilteredIngredients([]);
    toast.success(`${ing.name} hinzugefügt`);
  };

  const toggleIngredient = (ingId) => {
    const currentIds = formData.ingredient_ids;
    const currentAmounts = formData.ingredient_amounts;
    
    if (currentIds.includes(ingId)) {
      // Deselecting - remove from list
      const idx = currentIds.indexOf(ingId);
      setFormData({
        ...formData,
        ingredient_ids: currentIds.filter((_, i) => i !== idx),
        ingredient_amounts: currentAmounts.filter((_, i) => i !== idx)
      });
    } else {
      // Selecting - add to list and move to top of recently used
      setFormData({
        ...formData,
        ingredient_ids: [...currentIds, ingId],
        ingredient_amounts: [...currentAmounts, ""]
      });
      
      // Add to recently used (move to top)
      setRecentlyUsedIngredients(prev => {
        const filtered = prev.filter(id => id !== ingId);
        return [ingId, ...filtered].slice(0, 20);
      });
    }
  };

  const updateIngredientAmount = (idx, amount) => {
    const newAmounts = [...formData.ingredient_amounts];
    newAmounts[idx] = amount;
    setFormData({ ...formData, ingredient_amounts: newAmounts });
  };

  const toggleIngredientSelection = (ingId) => {
    setSelectedIngredients(prev => 
      prev.includes(ingId) ? prev.filter(id => id !== ingId) : [...prev, ingId]
    );
  };

  // Live search: automatically filter recipes when ingredients change
  useEffect(() => {
    const filterRecipesByIngredients = async () => {
      if (selectedIngredients.length === 0) {
        setMatchedRecipes([]);
        setShowIngredientMatch(false);
        return;
      }

      try {
        const response = await axios.get(`${API}/recipes/match`, {
          params: {
            ingredient_ids: selectedIngredients.join(","),
            max_missing: 2
          }
        });
        if (Array.isArray(response.data)) {
          setMatchedRecipes(response.data);
          setShowIngredientMatch(true);
        } else {
          console.error("API /recipes/match did not return an array:", response.data);
          setMatchedRecipes([]);
        }
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.error("Error filtering recipes:", error);
        }
        setMatchedRecipes([]);
      }
    };

    filterRecipesByIngredients();
  }, [selectedIngredients]);

  return (
    <div className="app-container" data-testid="cookbook-app">
      <header className="cookbook-header">
        <div className="header-content">
          <h1 className="cookbook-title" data-testid="app-title">
            <ChefHat className="title-icon" />
            Kochbuch
          </h1>
          <Link to="/discover" className="discover-link" data-testid="discover-link">
            <Shuffle size={20} /> Entdecken
          </Link>
        </div>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <button 
            className="btn-primary" 
            onClick={() => setShowForm(!showForm)}
            data-testid="new-recipe-btn"
          >
            <Plus size={20} /> Neues Rezept
          </button>

          <div className="search-section">
            <label className="section-label">Suche</label>
            <div className="search-input-wrapper">
              <Search size={18} className="search-icon" />
              <input
                type="text"
                placeholder="Rezepte durchsuchen..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
                data-testid="search-input"
              />
            </div>
          </div>

          <div className="filter-section">
            <label className="section-label"><Filter size={16} /> Filter</label>
            
            <div className="filter-group">
              <label className="filter-label">Min. Bewertung</label>
              <select 
                value={filters.minRating} 
                onChange={(e) => setFilters({...filters, minRating: parseInt(e.target.value)})}
                className="filter-select"
                data-testid="rating-filter"
              >
                <option value="0">Alle</option>
                <option value="1">1+ Sterne</option>
                <option value="2">2+ Sterne</option>
                <option value="3">3+ Sterne</option>
                <option value="4">4+ Sterne</option>
                <option value="5">5 Sterne</option>
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">Max. Kalorien (pro Portion)</label>
              <input
                type="number"
                placeholder="z.B. 500"
                value={filters.maxCalories}
                onChange={(e) => setFilters({...filters, maxCalories: e.target.value})}
                className="filter-input"
                data-testid="max-calories-input"
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">Min. Protein (g pro Portion)</label>
              <input
                type="number"
                placeholder="z.B. 20"
                value={filters.minProtein}
                onChange={(e) => setFilters({...filters, minProtein: e.target.value})}
                className="filter-input"
                data-testid="min-protein-input"
              />
            </div>
          </div>

          <div className="ingredient-matcher">
            <label className="section-label">Rezepte nach Zutaten filtern</label>
            <div className="ingredient-list">
              {sortedSidebarIngredients.map(ing => (
                  <div key={ing.id} className="ingredient-checkbox-wrapper">
                    {deletingIngredientId === ing.id ? (
                      <div className="ingredient-delete-confirm">
                        <span className="ingredient-delete-question">"{ing.name}" löschen?</span>
                        <div className="ingredient-delete-buttons">
                          <button
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                await axios.delete(`${API}/ingredients/${ing.id}`);
                                setIngredients(ingredients.filter(i => i.id !== ing.id));
                                setSelectedIngredients(selectedIngredients.filter(id => id !== ing.id));
                                toast.success("Zutat gelöscht");
                                setDeletingIngredientId(null);
                              } catch (error) {
                                toast.error("Fehler beim Löschen");
                                setDeletingIngredientId(null);
                              }
                            }}
                            className="btn-ingredient-confirm-yes"
                            title="Ja, löschen"
                          >
                            Ja
                          </button>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              setDeletingIngredientId(null);
                            }}
                            className="btn-ingredient-confirm-no"
                            title="Abbrechen"
                          >
                            Nein
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <label className="ingredient-checkbox">
                          <input
                            type="checkbox"
                            checked={selectedIngredients.includes(ing.id)}
                            onChange={() => toggleIngredientSelection(ing.id)}
                          />
                          <span>{ing.name}</span>
                        </label>
                        {editIngredientsMode && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              setDeletingIngredientId(ing.id);
                            }}
                            className="btn-delete-ingredient"
                            title="Zutat löschen"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                ))}
            </div>
            <button
              onClick={() => setEditIngredientsMode(!editIngredientsMode)}
              className="btn-edit-ingredients"
            >
              {editIngredientsMode ? "Fertig" : "Bearbeiten"}
            </button>
            {selectedIngredients.length > 0 && (
              <div className="filter-info">
                {selectedIngredients.length} Zutat(en) ausgewählt
              </div>
            )}
          </div>
        </aside>

        <main className="content-area">
          {showForm && (
            <RecipeForm 
              formData={formData}
              setFormData={setFormData}
              editingRecipe={editingRecipe}
              ingredients={ingredients}
              sortedFormIngredients={sortedFormIngredients}
              newIngredient={newIngredient}
              setNewIngredient={setNewIngredient}
              addIngredient={addIngredient}
              toggleIngredient={toggleIngredient}
              updateIngredientAmount={updateIngredientAmount}
              handleSubmit={handleSubmit}
              resetForm={resetForm}
              generateInstructions={generateInstructions}
              generateImage={generateImage}
              generatingInstructions={generatingInstructions}
              generatingImage={generatingImage}
              generatedImageBase64={generatedImageBase64}
              uploadedImageFile={uploadedImageFile}
              setUploadedImageFile={setUploadedImageFile}
              filteredIngredients={filteredIngredients}
              handleIngredientSearch={handleIngredientSearch}
              selectIngredient={selectIngredient}
              setGeneratedImageBase64={setGeneratedImageBase64}
              recentlyUsedIngredients={recentlyUsedIngredients}
            />
          )}

          {showIngredientMatch && matchedRecipes.length > 0 && (
            <div className="matched-recipes-section" data-testid="matched-recipes">
              <div className="section-header">
                <h2>Passende Rezepte ({matchedRecipes.length})</h2>
                <button onClick={() => setShowIngredientMatch(false)} className="btn-close">
                  <X size={20} />
                </button>
              </div>
              <div className="recipes-grid">
                {matchedRecipes.map(recipe => (
                  <RecipeCard 
                    key={recipe.id} 
                    recipe={recipe} 
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onCooked={handleCooked}
                    onRate={handleRating}
                    showMissingIngredients={true}
                    navigate={navigate}
                  />
                ))}
              </div>
            </div>
          )}

          {!showIngredientMatch && (
            <div className="recipes-section">
              <h2 className="section-header">Rezepte ({filteredRecipes.length})</h2>
              <div className="recipes-grid" data-testid="recipes-grid">
                {filteredRecipes.map(recipe => (
                  <RecipeCard 
                    key={recipe.id} 
                    recipe={recipe} 
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onCooked={handleCooked}
                    onRate={handleRating}
                    navigate={navigate}
                  />
                ))}
              </div>
              {filteredRecipes.length === 0 && (
                <div className="empty-state" data-testid="empty-state">
                  <p>Keine Rezepte gefunden</p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// ============ RECIPE FORM COMPONENT ============
function RecipeForm({
  formData, setFormData, editingRecipe, ingredients, sortedFormIngredients, newIngredient, setNewIngredient,
  addIngredient, toggleIngredient, updateIngredientAmount, handleSubmit, resetForm,
  generateInstructions, generateImage, generatingInstructions, generatingImage, generatedImageBase64,
  uploadedImageFile, setUploadedImageFile, filteredIngredients, handleIngredientSearch, selectIngredient,
  setGeneratedImageBase64, recentlyUsedIngredients
}) {
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error("Bitte nur Bilddateien hochladen");
        return;
      }
      setUploadedImageFile(file);
      // Clear generated image when uploading own image
      setGeneratedImageBase64(null);
      toast.success("Bild ausgewählt");
    }
  };

  // Display priority: uploaded file > generated image > existing recipe image
  const displayImage = uploadedImageFile 
    ? URL.createObjectURL(uploadedImageFile) 
    : generatedImageBase64 
    ? `data:image/png;base64,${generatedImageBase64}` 
    : formData.image_url
    ? `${BACKEND_URL}${formData.image_url}`
    : null;

  return (
    <div className="recipe-form-card" data-testid="recipe-form">
      <div className="form-header">
        <h2>{editingRecipe ? "Rezept bearbeiten" : "Neues Rezept"}</h2>
        <button onClick={resetForm} className="btn-close" data-testid="close-form-btn">
          <X size={20} />
        </button>
      </div>
      
      <form onSubmit={handleSubmit}>
        {displayImage && (
          <div className="generated-image-preview">
            <img src={displayImage} alt="Rezeptbild" />
            {editingRecipe && !uploadedImageFile && !generatedImageBase64 && (
              <div className="image-hint">Aktuelles Bild (kann ersetzt werden)</div>
            )}
          </div>
        )}

        <div className="form-grid">
          <div className="form-group full-width">
            <label>Rezeptname *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              required
              data-testid="recipe-name-input"
            />
          </div>

          <div className="form-group">
            <label>Kalorien (Gesamt)</label>
            <input
              type="number"
              value={formData.calories}
              onChange={(e) => setFormData({...formData, calories: e.target.value})}
              min="0"
              data-testid="calories-input"
            />
          </div>

          <div className="form-group">
            <label>Protein (g Gesamt)</label>
            <input
              type="number"
              value={formData.protein}
              onChange={(e) => setFormData({...formData, protein: e.target.value})}
              min="0"
              data-testid="protein-input"
            />
          </div>

          <div className="form-group">
            <label>Kohlenhydrate (g Gesamt)</label>
            <input
              type="number"
              value={formData.carbs}
              onChange={(e) => setFormData({...formData, carbs: e.target.value})}
              min="0"
              data-testid="carbs-input"
            />
          </div>

          <div className="form-group">
            <label>Fett (g Gesamt)</label>
            <input
              type="number"
              value={formData.fat}
              onChange={(e) => setFormData({...formData, fat: e.target.value})}
              min="0"
              data-testid="fat-input"
            />
          </div>

          <div className="form-group">
            <label>Portionen</label>
            <input
              type="number"
              value={formData.servings}
              onChange={(e) => setFormData({...formData, servings: e.target.value})}
              min="1"
              data-testid="servings-input"
            />
          </div>

          <div className="form-group full-width">
            <label>Zutaten</label>
            <div className="ingredient-search-wrapper">
              <div className="ingredient-add">
                <input
                  type="text"
                  placeholder="Zutat suchen..."
                  value={newIngredient}
                  onChange={(e) => handleIngredientSearch(e.target.value)}
                  data-testid="new-ingredient-input"
                />
                <button 
                  type="button" 
                  onClick={addIngredient} 
                  className="btn-add" 
                  data-testid="add-ingredient-btn"
                  title="Neue Zutat erstellen"
                >
                  <Plus size={18} />
                </button>
              </div>
              
              {filteredIngredients.length > 0 && (
                <div className="ingredient-suggestions">
                  {filteredIngredients.map(ing => (
                    <div 
                      key={ing.id} 
                      className="ingredient-suggestion"
                      onClick={() => selectIngredient(ing)}
                    >
                      {ing.name}
                    </div>
                  ))}
                </div>
              )}
              
              {newIngredient && filteredIngredients.length === 0 && (
                <div className="no-results">
                  Keine Zutat gefunden. Mit + erstellen.
                </div>
              )}
            </div>
            <div className="ingredient-tags">
              {sortedFormIngredients.map((ing, idx) => {
                const isSelected = formData.ingredient_ids.includes(ing.id);
                const selectedIdx = formData.ingredient_ids.indexOf(ing.id);
                return (
                  <div key={ing.id} className="ingredient-tag-with-amount">
                    <label className="ingredient-tag">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleIngredient(ing.id)}
                      />
                      <span>{ing.name}</span>
                    </label>
                    {isSelected && (
                      <input
                        type="text"
                        placeholder="Menge (z.B. 200g)"
                        value={formData.ingredient_amounts[selectedIdx] || ""}
                        onChange={(e) => updateIngredientAmount(selectedIdx, e.target.value)}
                        className="amount-input"
                        data-testid={`amount-input-${selectedIdx}`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="form-group full-width">
            <div className="label-with-action">
              <label>Kochanleitung</label>
              <button 
                type="button" 
                onClick={generateInstructions} 
                className="btn-ai"
                disabled={generatingInstructions}
                data-testid="generate-instructions-btn"
              >
                <Sparkles size={16} /> {generatingInstructions ? "Erstelle..." : "KI generieren"}
              </button>
            </div>
            <textarea
              value={formData.instructions}
              onChange={(e) => setFormData({...formData, instructions: e.target.value})}
              rows="6"
              placeholder="Beschreiben Sie die Zubereitungsschritte..."
              data-testid="instructions-input"
            />
          </div>

          <div className="form-group full-width">
            <label>Rezeptbild</label>
            <div className="image-upload-section">
              <button 
                type="button" 
                onClick={generateImage} 
                className="btn-secondary"
                disabled={generatingImage}
                data-testid="generate-image-btn"
              >
                <Camera size={16} /> {generatingImage ? "Generiere Bild..." : "Mit KI generieren"}
              </button>
              
              <span className="upload-divider">oder</span>
              
              <label className="btn-secondary upload-btn">
                <Upload size={16} /> Eigenes Bild hochladen
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                  data-testid="upload-image-input"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" data-testid="submit-recipe-btn">
            {editingRecipe ? "Aktualisieren" : "Erstellen"}
          </button>
          <button type="button" onClick={resetForm} className="btn-secondary" data-testid="cancel-btn">
            Abbrechen
          </button>
        </div>
      </form>
    </div>
  );
}

// ============ RECIPE CARD COMPONENT ============
function RecipeCard({ recipe, onEdit, onDelete, onCooked, onRate, showMissingIngredients, navigate }) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  const hasImage = recipe.image_url;
  const imageUrl = hasImage ? `${BACKEND_URL}${recipe.image_url}` : null;
  
  const servings = recipe.servings && recipe.servings > 0 ? recipe.servings : 1;

  return (
    <div 
      className="recipe-card" 
      data-testid={`recipe-card-${recipe.id}`}
      onClick={() => !showDeleteConfirm && navigate(`/recipe/${recipe.id}`)}
      style={{ cursor: showDeleteConfirm ? 'default' : 'pointer' }}
    >
      <div className="recipe-card-image">
        {hasImage ? (
          <img src={imageUrl} alt={recipe.name} />
        ) : (
          <div className="recipe-placeholder-image">
            <ChefHat size={48} />
            <span>Kein Bild</span>
          </div>
        )}
      </div>
      
      <div className="recipe-card-content">
        <div className="recipe-card-header">
          <h3 className="recipe-name" data-testid="recipe-name">{recipe.name}</h3>
          <div className="recipe-actions">
            <button 
              onClick={(e) => { 
                e.stopPropagation(); 
                e.preventDefault();
                onEdit(recipe); 
              }} 
              className="btn-icon" 
              data-testid="edit-recipe-btn"
            >
              <Edit2 size={16} />
            </button>
            <button 
              onClick={(e) => { 
                e.stopPropagation(); 
                e.preventDefault();
                setShowDeleteConfirm(true);
              }} 
              className="btn-icon" 
              data-testid="delete-recipe-btn"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        {showDeleteConfirm ? (
          <>
            <div className="recipe-divider"></div>
            <div className="delete-confirm-overlay-v2" onClick={(e) => e.stopPropagation()}>
              <p className="delete-confirm-question-v2">Löschen?</p>
              <div className="delete-confirm-buttons-v2">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    onDelete(recipe);
                    setShowDeleteConfirm(false);
                  }}
                  className="btn-delete-confirm-yes-v2"
                >
                  Ja, löschen
                </button>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    setShowDeleteConfirm(false);
                  }}
                  className="btn-delete-confirm-no-v2"
                >
                  Abbrechen
                </button>
              </div>
            </div>
            <div className="recipe-divider"></div>
          </>
        ) : (
          <>
            <div className="recipe-divider"></div>

        <div className="recipe-nutrients" data-testid="recipe-nutrients">
          <div className="nutrient-item">
            <span className="nutrient-label">Kalorien</span>
            <span className="nutrient-value">{Math.round(recipe.calories / servings)}</span>
          </div>
          <div className="nutrient-item">
            <span className="nutrient-label">Protein</span>
            <span className="nutrient-value">{Math.round(recipe.protein / servings)}g</span>
          </div>
          <div className="nutrient-item">
            <span className="nutrient-label">Kohlenhydrate</span>
            <span className="nutrient-value">{Math.round(recipe.carbs / servings)}g</span>
          </div>
          <div className="nutrient-item">
            <span className="nutrient-label">Fett</span>
            <span className="nutrient-value">{Math.round(recipe.fat / servings)}g</span>
          </div>
        </div>

        {showMissingIngredients && recipe.missing_ingredients && recipe.missing_ingredients.length > 0 && (
          <div className="missing-ingredients">
            <span className="missing-label">Fehlend ({recipe.missing_count}):</span>
            <span className="missing-list">{recipe.missing_ingredients.join(", ")}</span>
          </div>
        )}

        <div className="recipe-divider"></div>

        <div className="recipe-footer" onClick={(e) => e.stopPropagation()}>
          <div className="rating-stars" data-testid="rating-stars">
            {[1, 2, 3, 4, 5].map(star => (
              <Star
                key={star}
                size={20}
                className={`star ${star <= recipe.rating ? 'star-filled' : ''}`}
                onClick={() => onRate(recipe.id, star)}
                data-testid={`star-${star}`}
              />
            ))}
          </div>
          <button 
            onClick={() => onCooked(recipe)} 
            className="btn-cooked"
            data-testid="cooked-btn"
          >
            <ChefHat size={16} /> Gekocht
          </button>
        </div>
        </>
        )}
      </div>
    </div>
  );
}

// ============ RECIPE DETAIL PAGE ============
function RecipeDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [recipe, setRecipe] = useState(null);
  const [checkedIngredients, setCheckedIngredients] = useState({});
  const [loading, setLoading] = useState(true);
  const [servings, setServings] = useState(1);

  const fetchRecipe = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/recipes/${id}`);
      setRecipe(response.data);
      setServings(response.data.servings || 1);
      setLoading(false);
    } catch (error) {
      toast.error("Rezept nicht gefunden");
      navigate("/");
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchRecipe();
  }, [fetchRecipe, location.key]);

  const toggleIngredient = (ingId) => {
    setCheckedIngredients(prev => ({
      ...prev,
      [ingId]: !prev[ingId]
    }));
  };

  const scaleIngredient = (amount, baseServings, targetServings) => {
    if (!amount) return "";

    // Regex to find a number (integer or decimal) at the beginning of the string.
    const match = String(amount).match(/^(\d[\d,.]*)(\s*.*)/);

    if (!match) {
      // If no number is found (e.g., "a pinch of salt"), return the original string.
      return amount;
    }

    const numericStr = match[1].replace(',', '.'); // Normalize comma to dot for parseFloat
    const unitStr = match[2].trim(); // The rest of the string is the unit

    const originalNum = parseFloat(numericStr);
    if (isNaN(originalNum)) {
      return amount; // Safeguard if the numeric part is not a valid number
    }

    const scaledNum = (originalNum / baseServings) * targetServings;

    let scaledNumStr;
    // Use one decimal place for non-integers, zero for integers.
    if (scaledNum % 1 !== 0) {
      scaledNumStr = scaledNum.toFixed(1).replace('.', ',');
    } else {
      scaledNumStr = String(scaledNum);
    }

    // Combine the scaled number with its unit.
    if (unitStr) {
      return `${scaledNumStr} ${unitStr}`;
    }
    return scaledNumStr;
  };

  if (loading) {
    return <div className="loading">Lädt...</div>;
  }

  if (!recipe) {
    return null;
  }

  const baseServings = recipe.servings || 1;
  const servingMultiplier = servings / baseServings;
  const imageUrl = recipe.image_url ? `${BACKEND_URL}${recipe.image_url}` : null;

  return (
    <div className="recipe-detail-page">
      <header className="detail-header">
        <button onClick={() => navigate("/")} className="back-button" data-testid="back-btn">
          <ArrowLeft size={20} /> Zurück
        </button>
        <h1 className="detail-title">{recipe.name}</h1>
      </header>

      {imageUrl && (
        <div className="detail-hero-image" data-testid="recipe-image">
          <img src={imageUrl} alt={recipe.name} />
        </div>
      )}

      <div className="detail-content">
        <div className="detail-section">
          <div className="servings-control">
            <h2>Zutaten für</h2>
            <div className="servings-buttons">
              <button onClick={() => setServings(Math.max(1, servings - 1))}><Minus size={16} /></button>
              <span>{servings} Portion(en)</span>
              <button onClick={() => setServings(servings + 1)}><Plus size={16} /></button>
            </div>
          </div>
          <div className="ingredients-checklist" data-testid="ingredients-list">
            {recipe.ingredients.map((ing) => (
              <label key={ing.ingredient_id} className="ingredient-check-item">
                <input
                  type="checkbox"
                  checked={checkedIngredients[ing.ingredient_id] || false}
                  onChange={() => toggleIngredient(ing.ingredient_id)}
                  data-testid={`ingredient-check-${ing.ingredient_id}`}
                />
                <span className={checkedIngredients[ing.ingredient_id] ? 'checked' : ''}>
                  {scaleIngredient(ing.amount, baseServings, servings) && `${scaleIngredient(ing.amount, baseServings, servings)} `}{ing.ingredient_name}
                </span>
              </label>
            ))}
          </div>

          <div className="nutrients-detail">
            <h3>Nährwerte (für {servings} Portionen)</h3>
            <div className="nutrients-grid">
              <div><strong>Kalorien:</strong> {Math.round(recipe.calories * servingMultiplier)}</div>
              <div><strong>Protein:</strong> {Math.round(recipe.protein * servingMultiplier)}g</div>
              <div><strong>Kohlenhydrate:</strong> {Math.round(recipe.carbs * servingMultiplier)}g</div>
              <div><strong>Fett:</strong> {Math.round(recipe.fat * servingMultiplier)}g</div>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h2>Zubereitung</h2>
          <div className="instructions-text" data-testid="instructions-text">
            {recipe.instructions || "Keine Anleitung vorhanden"}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ DISCOVER PAGE ============
function DiscoverPage() {
  const navigate = useNavigate();
  const [randomRecipes, setRandomRecipes] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRandomRecipes = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/recipes/random?count=6`);
      setRandomRecipes(response.data);
    } catch (error) {
      toast.error("Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRandomRecipes();
  }, [fetchRandomRecipes]);

  const handleRating = async (recipeId, rating) => {
    try {
      await axios.put(`${API}/recipes/${recipeId}`, { rating });
      toast.success("Bewertung gespeichert");
      fetchRandomRecipes();
    } catch (error) {
      toast.error("Fehler beim Bewerten");
    }
  };

  const handleCooked = async (recipe) => {
    try {
      await axios.post(`${API}/recipes/${recipe.id}/cooked`);
      toast.success(`${recipe.name} als gekocht markiert!`);
    } catch (error) {
      toast.error("Fehler beim Markieren");
    }
  };

  return (
    <div className="discover-page">
      <header className="discover-header">
        <button onClick={() => navigate("/")} className="back-button">
          <ArrowLeft size={20} /> Zurück
        </button>
        <h1 className="discover-title">
          <Shuffle size={28} /> Zufällige Rezepte
        </h1>
        <button onClick={fetchRandomRecipes} className="refresh-button" data-testid="refresh-btn">
          <Shuffle size={20} /> Neue laden
        </button>
      </header>

      <div className="discover-content">
        {loading ? (
          <div className="loading">Lädt...</div>
        ) : (
          <div className="recipes-grid" data-testid="discover-grid">
            {randomRecipes.map(recipe => (
              <RecipeCard 
                key={recipe.id} 
                recipe={recipe}
                onEdit={() => {}}
                onDelete={() => {}}
                onCooked={handleCooked}
                onRate={handleRating}
                navigate={navigate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
