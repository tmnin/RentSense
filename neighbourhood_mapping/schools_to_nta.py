import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

nta_area_km2 = nta.to_crs(3857).geometry.area / 1_000_000
base = nta[[nta_id, "geometry"]].copy()

schools = gpd.read_file("data/school_points.geojson").to_crs(4326)

lat_like = [c for c in schools.columns if c.lower() in ["latitude", "lat"]]
lon_like = [c for c in schools.columns if c.lower() in ["longitude", "lon", "lng"]]

if len(lat_like) and len(lon_like) and schools.geometry.isna().all():
    schools = gpd.GeoDataFrame(
        schools,
        geometry=gpd.points_from_xy(schools[lon_like[0]], schools[lat_like[0]]),
        crs=4326
    )

k12_join = gpd.sjoin(schools, nta[[nta_id, "geometry"]], predicate="intersects")
k12_counts = k12_join.groupby(nta_id).size().reset_index(name="k12_count")
base = base.merge(k12_counts, on=nta_id, how="left").fillna({"k12_count": 0})

cuny = pd.read_csv("data/cuny.csv", low_memory=False)

cuny_lat = next(c for c in ["Latitude", "latitude", "LATITUDE", "lat"] if c in cuny.columns)
cuny_lon = next(c for c in ["Longitude", "longitude", "LONGITUDE", "lon", "lng"] if c in cuny.columns)

cuny[cuny_lat] = pd.to_numeric(cuny[cuny_lat], errors="coerce")
cuny[cuny_lon] = pd.to_numeric(cuny[cuny_lon], errors="coerce")
cuny = cuny.dropna(subset=[cuny_lat, cuny_lon])

cuny_gdf = gpd.GeoDataFrame(
    cuny,
    geometry=gpd.points_from_xy(cuny[cuny_lon], cuny[cuny_lat]),
    crs=4326
)

cuny_join = gpd.sjoin(cuny_gdf, nta[[nta_id, "geometry"]], predicate="intersects")
cuny_counts = cuny_join.groupby(nta_id).size().reset_index(name="cuny_count")
base = base.merge(cuny_counts, on=nta_id, how="left").fillna({"cuny_count": 0})

base["k12_per_km2"] = base["k12_count"].to_numpy() / nta_area_km2.to_numpy()
base["cuny_per_km2"] = base["cuny_count"].to_numpy() / nta_area_km2.to_numpy()

base["k12_pct"] = base["k12_per_km2"].rank(pct=True)
base["cuny_pct"] = base["cuny_per_km2"].rank(pct=True)

base["education_pct"] = (base["k12_pct"] + base["cuny_pct"]) / 2

out = nta.merge(
    base[[nta_id, "education_pct", "k12_count", "cuny_count"]],
    on=nta_id,
    how="left"
).fillna({"education_pct": 0, "k12_count": 0, "cuny_count": 0})

out[[nta_id, "education_pct", "k12_count", "cuny_count"]].to_csv("data/nta_education.csv", index=False)

ax = out.plot(column="education_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("data/education_map.png", dpi=200)
plt.close()
