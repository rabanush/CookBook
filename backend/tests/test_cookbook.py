"""Cookbook backend API tests"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://nutrition-log-197.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    return {"ingredients": [], "recipes": []}


# Ingredients
def test_create_ingredient(session, created_ids):
    r = session.post(f"{API}/ingredients", json={"name": "TEST_Mehl"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "TEST_Mehl"
    assert "id" in data
    created_ids["ingredients"].append(data["id"])


def test_create_ingredient_duplicate_returns_existing(session, created_ids):
    r = session.post(f"{API}/ingredients", json={"name": "TEST_Mehl"})
    assert r.status_code == 200
    assert r.json()["id"] == created_ids["ingredients"][0]


def test_create_ingredient_empty(session):
    r = session.post(f"{API}/ingredients", json={"name": "   "})
    assert r.status_code == 400


def test_list_ingredients(session):
    r = session.get(f"{API}/ingredients")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_more_ingredients(session, created_ids):
    for n in ["TEST_Eier", "TEST_Milch"]:
        r = session.post(f"{API}/ingredients", json={"name": n})
        assert r.status_code == 200
        created_ids["ingredients"].append(r.json()["id"])


# Recipes
def test_create_recipe(session, created_ids):
    payload = {
        "name": "TEST_Pfannkuchen",
        "calories": 300, "protein": 10, "carbs": 40, "fat": 8,
        "ingredient_ids": created_ids["ingredients"]
    }
    r = session.post(f"{API}/recipes", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "TEST_Pfannkuchen"
    assert data["calories"] == 300
    assert len(data["ingredients"]) == 3
    assert data["rating"] == 0
    created_ids["recipes"].append(data["id"])


def test_create_recipe_negative_calories(session):
    r = session.post(f"{API}/recipes", json={
        "name": "TEST_Bad", "calories": -1, "protein": 0, "carbs": 0, "fat": 0
    })
    assert r.status_code == 422


def test_create_recipe_empty_name(session):
    r = session.post(f"{API}/recipes", json={
        "name": "  ", "calories": 100, "protein": 0, "carbs": 0, "fat": 0
    })
    assert r.status_code == 400


def test_get_recipe(session, created_ids):
    rid = created_ids["recipes"][0]
    r = session.get(f"{API}/recipes/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_get_recipe_404(session):
    r = session.get(f"{API}/recipes/non-existent-id")
    assert r.status_code == 404


def test_list_recipes_with_search(session):
    r = session.get(f"{API}/recipes", params={"search": "TEST_Pfann"})
    assert r.status_code == 200
    names = [x["name"] for x in r.json()]
    assert any("TEST_Pfann" in n for n in names)


def test_list_recipes_with_filters(session):
    r = session.get(f"{API}/recipes", params={"min_calories": 200, "max_calories": 400})
    assert r.status_code == 200
    for rec in r.json():
        assert 200 <= rec["calories"] <= 400


def test_update_recipe_rating(session, created_ids):
    rid = created_ids["recipes"][0]
    r = session.put(f"{API}/recipes/{rid}", json={"rating": 5})
    assert r.status_code == 200
    assert r.json()["rating"] == 5
    # Verify persistence
    g = session.get(f"{API}/recipes/{rid}")
    assert g.json()["rating"] == 5


def test_update_recipe_invalid_rating(session, created_ids):
    rid = created_ids["recipes"][0]
    r = session.put(f"{API}/recipes/{rid}", json={"rating": 6})
    assert r.status_code == 422


def test_min_rating_filter(session):
    r = session.get(f"{API}/recipes", params={"min_rating": 5})
    assert r.status_code == 200
    for rec in r.json():
        assert rec["rating"] >= 5


def test_match_recipes(session, created_ids):
    ing_ids = ",".join(created_ids["ingredients"][:2])  # Missing 1
    r = session.get(f"{API}/recipes/match", params={"ingredient_ids": ing_ids, "max_missing": 2})
    assert r.status_code == 200
    data = r.json()
    found = [x for x in data if x["id"] == created_ids["recipes"][0]]
    assert len(found) == 1
    assert found[0]["missing_count"] == 1
    assert len(found[0]["missing_ingredients"]) == 1


def test_match_recipes_exact(session, created_ids):
    ing_ids = ",".join(created_ids["ingredients"])
    r = session.get(f"{API}/recipes/match", params={"ingredient_ids": ing_ids, "max_missing": 0})
    assert r.status_code == 200
    found = [x for x in r.json() if x["id"] == created_ids["recipes"][0]]
    assert len(found) == 1
    assert found[0]["missing_count"] == 0
    assert found[0]["match_percentage"] == 100


def test_mark_cooked(session, created_ids):
    rid = created_ids["recipes"][0]
    r = session.post(f"{API}/recipes/{rid}/cooked")
    assert r.status_code == 200
    assert "timestamp" in r.json()


def test_mark_cooked_not_found(session):
    r = session.post(f"{API}/recipes/non-existent/cooked")
    assert r.status_code == 404


def test_sync_returns_cooked(session, created_ids):
    r = session.get(f"{API}/sync", params={"since": 0})
    assert r.status_code == 200
    data = r.json()
    assert any(e["recipe_id"] == created_ids["recipes"][0] for e in data)


def test_sync_since_filter(session):
    import time
    future = int(time.time()) + 10000
    r = session.get(f"{API}/sync", params={"since": future})
    assert r.status_code == 200
    assert r.json() == []


def test_zz_delete_recipe(session, created_ids):
    rid = created_ids["recipes"][0]
    r = session.delete(f"{API}/recipes/{rid}")
    assert r.status_code == 200
    g = session.get(f"{API}/recipes/{rid}")
    assert g.status_code == 404


def test_zz_delete_ingredients(session, created_ids):
    for iid in created_ids["ingredients"]:
        r = session.delete(f"{API}/ingredients/{iid}")
        assert r.status_code == 200
