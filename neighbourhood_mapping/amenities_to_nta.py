import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

nta_proj = nta.to_crs(3857)
nta_area_km2 = nta_proj.geometry.area / 1_000_000
base = nta[[nta_id, "geometry"]].copy()

restaurants = pd.read_csv("data/restaurants.csv", low_memory=False)
restaurants["Latitude"] = pd.to_numeric(restaurants["Latitude"], errors="coerce")
restaurants["Longitude"] = pd.to_numeric(restaurants["Longitude"], errors="coerce")
restaurants = restaurants.dropna(subset=["Latitude", "Longitude"])
restaurants_gdf = gpd.GeoDataFrame(
    restaurants,
    geometry=gpd.points_from_xy(restaurants["Longitude"], restaurants["Latitude"]),
    crs=4326
)
r_join = gpd.sjoin(restaurants_gdf, nta[[nta_id, "geometry"]], predicate="intersects")
r_counts = r_join.groupby(nta_id).size().reset_index(name="restaurants_count")
base = base.merge(r_counts, on=nta_id, how="left").fillna({"restaurants_count": 0})

groceries = pd.read_csv("data/groceries.csv", low_memory=False)
geo_col = next(c for c in ["Georeference", "georeference", "GEOREFERENCE"] if c in groceries.columns)
coords = groceries[geo_col].astype(str).str.extract(r"POINT\s*\(\s*([-\d\.]+)\s+([-\d\.]+)\s*\)")
groceries["Longitude"] = pd.to_numeric(coords[0], errors="coerce")
groceries["Latitude"] = pd.to_numeric(coords[1], errors="coerce")
groceries = groceries.dropna(subset=["Latitude", "Longitude"])
groceries_gdf = gpd.GeoDataFrame(
    groceries,
    geometry=gpd.points_from_xy(groceries["Longitude"], groceries["Latitude"]),
    crs=4326
)
g_join = gpd.sjoin(groceries_gdf, nta[[nta_id, "geometry"]], predicate="intersects")
g_counts = g_join.groupby(nta_id).size().reset_index(name="groceries_count")
base = base.merge(g_counts, on=nta_id, how="left").fillna({"groceries_count": 0})

base["restaurants_per_km2"] = base["restaurants_count"].to_numpy() / nta_area_km2.to_numpy()
base["groceries_per_km2"] = base["groceries_count"].to_numpy() / nta_area_km2.to_numpy()

base["restaurants_pct"] = base["restaurants_per_km2"].rank(pct=True)
base["groceries_pct"] = base["groceries_per_km2"].rank(pct=True)

base["amenities_pct"] = (base["restaurants_pct"] + base["groceries_pct"]) / 2

out = nta.merge(base[[nta_id, "restaurants_count", "groceries_count", "amenities_pct"]], on=nta_id, how="left").fillna(
    {"restaurants_count": 0, "groceries_count": 0, "amenities_pct": 0}
)

out[[nta_id, "amenities_pct", "restaurants_count", "groceries_count"]].to_csv("data/nta_amenities.csv", index=False)

ax = out.plot(column="amenities_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("data/amenities_map.png", dpi=200)
