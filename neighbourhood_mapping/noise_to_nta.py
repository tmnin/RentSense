import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

noise = pd.read_csv("data/311_noise_12m.csv", low_memory=False)
noise["Latitude"] = pd.to_numeric(noise["Latitude"], errors="coerce")
noise["Longitude"] = pd.to_numeric(noise["Longitude"], errors="coerce")
noise = noise.dropna(subset=["Latitude", "Longitude"])

noise_gdf = gpd.GeoDataFrame(noise, geometry=gpd.points_from_xy(noise["Longitude"], noise["Latitude"]), crs=4326)

joined = gpd.sjoin(noise_gdf, nta[[nta_id, "geometry"]], predicate="intersects")
counts = joined.groupby(nta_id).size().reset_index(name="noise_count")

nta = nta.merge(counts, on=nta_id, how="left").fillna({"noise_count": 0})

nta_proj = nta.to_crs(3857)
nta["noise_per_km2"] = nta["noise_count"] / (nta_proj.geometry.area / 1_000_000)
nta["noise_pct"] = nta["noise_per_km2"].rank(pct=True)

ax = nta.plot(column="noise_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("data/noise_map.png", dpi=200)

nta[[nta_id, "noise_pct", "noise_per_km2", "noise_count"]].to_csv(
    "data/nta_noise.csv",
    index=False
)
