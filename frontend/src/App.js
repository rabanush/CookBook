import { useState, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Plus, Search, Star, ChefHat, X, Edit2, Trash2, Filter } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [recipes, setRecipes] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [filteredRecipes, setFilteredRecipes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [showIngredientMatch, setShowIngredientMatch] = useState(false);
  const [matchedRecipes, setMatchedRecipes] = useState([]);
  const [filters, setFilters] = useState({
    minRating: 0,
    maxCalories: "",
    minCalories: ""
  });
  const [newIngredient, setNewIngredient] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    calories: "",
    protein: "",
    carbs: "",
    fat: "",
    ingredient_ids: []
  });

  useEffect(() => {
    fetchRecipes();
    fetchIngredients();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [recipes, searchTerm, filters]);

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error("Fehler beim Laden der Rezepte");
    }
  };

  const fetchIngredients = async () => {
    try {
      const response = await axios.get(`${API}/ingredients`);
      setIngredients(response.data);
    } catch (error) {
      toast.error("Fehler beim Laden der Zutaten");
    }
  };

  const applyFilters = () => {
    let filtered = [...recipes];

    if (searchTerm) {
      filtered = filtered.filter(r => 
        r.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (filters.minRating > 0) {
      filtered = filtered.filter(r => r.rating >= filters.minRating);
    }

    if (filters.minCalories) {
      filtered = filtered.filter(r => r.calories >= parseInt(filters.minCalories));
    }

    if (filters.maxCalories) {
      filtered = filtered.filter(r => r.calories <= parseInt(filters.maxCalories));
    }

    setFilteredRecipes(filtered);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error("Name ist erforderlich");
      return;
    }

    if (formData.calories < 0 || formData.protein < 0 || formData.carbs < 0 || formData.fat < 0) {
      toast.error("Nährwerte müssen positiv sein");
      return;
    }

    try {
      const payload = {
        ...formData,
        calories: parseInt(formData.calories) || 0,
        protein: parseInt(formData.protein) || 0,
        carbs: parseInt(formData.carbs) || 0,
        fat: parseInt(formData.fat) || 0
      };

      if (editingRecipe) {
        await axios.put(`${API}/recipes/${editingRecipe.id}`, payload);
        toast.success("Rezept aktualisiert");
      } else {
        await axios.post(`${API}/recipes`, payload);
        toast.success("Rezept erstellt");
      }

      fetchRecipes();
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
      ingredient_ids: recipe.ingredients.map(i => i.ingredient_id)
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Rezept wirklich löschen?")) return;
    
    try {
      await axios.delete(`${API}/recipes/${id}`);
      toast.success("Rezept gelöscht");
      fetchRecipes();
    } catch (error) {
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
      fetchRecipes();
    } catch (error) {
      toast.error("Fehler beim Bewerten");
    }
  };

  const resetForm = () => {
    setFormData({ name: "", calories: "", protein: "", carbs: "", fat: "", ingredient_ids: [] });
    setEditingRecipe(null);
    setShowForm(false);
  };

  const addIngredient = async () => {
    if (!newIngredient.trim()) return;
    
    try {
      const response = await axios.post(`${API}/ingredients`, { name: newIngredient });
      setIngredients([...ingredients, response.data]);
      setNewIngredient("");
      toast.success("Zutat hinzugefügt");
    } catch (error) {
      toast.error("Fehler beim Hinzufügen der Zutat");
    }
  };

  const toggleIngredient = (ingId) => {
    setFormData(prev => ({
      ...prev,
      ingredient_ids: prev.ingredient_ids.includes(ingId)
        ? prev.ingredient_ids.filter(id => id !== ingId)
        : [...prev.ingredient_ids, ingId]
    }));
  };

  const toggleIngredientSelection = (ingId) => {
    setSelectedIngredients(prev => 
      prev.includes(ingId) ? prev.filter(id => id !== ingId) : [...prev, ingId]
    );
  };

  const findMatchingRecipes = async () => {
    if (selectedIngredients.length === 0) {
      toast.error("Bitte wählen Sie mindestens eine Zutat aus");
      return;
    }

    try {
      const response = await axios.get(`${API}/recipes/match`, {
        params: {
          ingredient_ids: selectedIngredients.join(","),
          max_missing: 2
        }
      });
      setMatchedRecipes(response.data);
      setShowIngredientMatch(true);
    } catch (error) {
      toast.error("Fehler beim Suchen von Rezepten");
    }
  };

  return (
    <div className="app-container" data-testid="cookbook-app">
      {/* Header */}
      <header className="cookbook-header">
        <div className="header-content">
          <h1 className="cookbook-title" data-testid="app-title">
            <ChefHat className="title-icon" />
            Familien-Kochbuch
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <div className="main-content">
        {/* Sidebar */}
        <aside className="sidebar">
          <button 
            className="btn-primary" 
            onClick={() => setShowForm(!showForm)}
            data-testid="new-recipe-btn"
          >
            <Plus size={20} /> Neues Rezept
          </button>

          {/* Search */}
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

          {/* Filters */}
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
              <label className="filter-label">Kalorien</label>
              <div className="filter-range">
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.minCalories}
                  onChange={(e) => setFilters({...filters, minCalories: e.target.value})}
                  className="filter-input"
                  data-testid="min-calories-input"
                />
                <span>-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.maxCalories}
                  onChange={(e) => setFilters({...filters, maxCalories: e.target.value})}
                  className="filter-input"
                  data-testid="max-calories-input"
                />
              </div>
            </div>
          </div>

          {/* Ingredient Matcher */}
          <div className="ingredient-matcher">
            <label className="section-label">Rezepte nach Zutaten finden</label>
            <div className="ingredient-list">
              {ingredients.map(ing => (
                <label key={ing.id} className="ingredient-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedIngredients.includes(ing.id)}
                    onChange={() => toggleIngredientSelection(ing.id)}
                  />
                  <span>{ing.name}</span>
                </label>
              ))}
            </div>
            <button 
              onClick={findMatchingRecipes} 
              className="btn-secondary"
              data-testid="find-recipes-btn"
            >
              Passende Rezepte finden
            </button>
          </div>
        </aside>

        {/* Content Area */}
        <main className="content-area">
          {/* Recipe Form */}
          {showForm && (
            <div className="recipe-form-card" data-testid="recipe-form">
              <div className="form-header">
                <h2>{editingRecipe ? "Rezept bearbeiten" : "Neues Rezept"}</h2>
                <button onClick={resetForm} className="btn-close" data-testid="close-form-btn">
                  <X size={20} />
                </button>
              </div>
              
              <form onSubmit={handleSubmit}>
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
                    <label>Kalorien</label>
                    <input
                      type="number"
                      value={formData.calories}
                      onChange={(e) => setFormData({...formData, calories: e.target.value})}
                      min="0"
                      data-testid="calories-input"
                    />
                  </div>

                  <div className="form-group">
                    <label>Protein (g)</label>
                    <input
                      type="number"
                      value={formData.protein}
                      onChange={(e) => setFormData({...formData, protein: e.target.value})}
                      min="0"
                      data-testid="protein-input"
                    />
                  </div>

                  <div className="form-group">
                    <label>Kohlenhydrate (g)</label>
                    <input
                      type="number"
                      value={formData.carbs}
                      onChange={(e) => setFormData({...formData, carbs: e.target.value})}
                      min="0"
                      data-testid="carbs-input"
                    />
                  </div>

                  <div className="form-group">
                    <label>Fett (g)</label>
                    <input
                      type="number"
                      value={formData.fat}
                      onChange={(e) => setFormData({...formData, fat: e.target.value})}
                      min="0"
                      data-testid="fat-input"
                    />
                  </div>

                  <div className="form-group full-width">
                    <label>Zutaten</label>
                    <div className="ingredient-add">
                      <input
                        type="text"
                        placeholder="Neue Zutat..."
                        value={newIngredient}
                        onChange={(e) => setNewIngredient(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addIngredient())}
                        data-testid="new-ingredient-input"
                      />
                      <button type="button" onClick={addIngredient} className="btn-add" data-testid="add-ingredient-btn">
                        <Plus size={18} />
                      </button>
                    </div>
                    <div className="ingredient-tags">
                      {ingredients.map(ing => (
                        <label key={ing.id} className="ingredient-tag">
                          <input
                            type="checkbox"
                            checked={formData.ingredient_ids.includes(ing.id)}
                            onChange={() => toggleIngredient(ing.id)}
                          />
                          <span>{ing.name}</span>
                        </label>
                      ))}
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
          )}

          {/* Matched Recipes Display */}
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
                  />
                ))}
              </div>
            </div>
          )}

          {/* All Recipes */}
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

// Recipe Card Component
function RecipeCard({ recipe, onEdit, onDelete, onCooked, onRate, showMissingIngredients }) {
  return (
    <div className="recipe-card" data-testid={`recipe-card-${recipe.id}`}>
      <div className="recipe-card-header">
        <h3 className="recipe-name" data-testid="recipe-name">{recipe.name}</h3>
        <div className="recipe-actions">
          <button onClick={() => onEdit(recipe)} className="btn-icon" data-testid="edit-recipe-btn">
            <Edit2 size={16} />
          </button>
          <button onClick={() => onDelete(recipe.id)} className="btn-icon" data-testid="delete-recipe-btn">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="recipe-divider"></div>

      <div className="recipe-nutrients" data-testid="recipe-nutrients">
        <div className="nutrient-item">
          <span className="nutrient-label">Kalorien</span>
          <span className="nutrient-value">{recipe.calories}</span>
        </div>
        <div className="nutrient-item">
          <span className="nutrient-label">Protein</span>
          <span className="nutrient-value">{recipe.protein}g</span>
        </div>
        <div className="nutrient-item">
          <span className="nutrient-label">Kohlenhydrate</span>
          <span className="nutrient-value">{recipe.carbs}g</span>
        </div>
        <div className="nutrient-item">
          <span className="nutrient-label">Fett</span>
          <span className="nutrient-value">{recipe.fat}g</span>
        </div>
      </div>

      {recipe.ingredients && recipe.ingredients.length > 0 && (
        <div className="recipe-ingredients" data-testid="recipe-ingredients">
          <div className="ingredients-label">Zutaten:</div>
          <div className="ingredients-tags">
            {recipe.ingredients.map((ing, idx) => (
              <span key={idx} className="ingredient-badge">{ing.ingredient_name}</span>
            ))}
          </div>
        </div>
      )}

      {showMissingIngredients && recipe.missing_ingredients && recipe.missing_ingredients.length > 0 && (
        <div className="missing-ingredients">
          <span className="missing-label">Fehlend ({recipe.missing_count}):</span>
          <span className="missing-list">{recipe.missing_ingredients.join(", ")}</span>
        </div>
      )}

      <div className="recipe-divider"></div>

      <div className="recipe-footer">
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
    </div>
  );
}

export default App;