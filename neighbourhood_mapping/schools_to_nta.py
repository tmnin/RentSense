import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
nta_id = next(
    c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"]
    if c in nta.columns
)

nta_proj = nta.to_crs(3857)
nta_area_km2 = nta_proj.geometry.area / 1_000_000

base = nta[[nta_id, "geometry"]].copy()

schools = gpd.read_file("data/SchoolPoint/SchoolPoints_APS_2024_08_28.shp").to_crs(4326)

schools = schools[schools.geometry.notnull()].copy()

join = gpd.sjoin(
    schools,
    nta[[nta_id, "geometry"]],
    predicate="intersects"
)

counts = join.groupby(nta_id).size().reset_index(name="schools_count")

base = base.merge(counts, on=nta_id, how="left").fillna({"schools_count": 0})

base["schools_per_km2"] = base["schools_count"].to_numpy() / nta_area_km2.to_numpy()
base["schools_pct"] = base["schools_per_km2"].rank(pct=True)

base[[nta_id, "schools_count", "schools_pct"]].to_csv("results/nta_schools.csv", index=False)

out = nta.merge(base[[nta_id, "schools_count", "schools_pct"]], on=nta_id, how="left").fillna(
    {"schools_count": 0, "schools_pct": 0}
)

ax = out.plot(column="schools_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("results/schools_map.png", dpi=200)

print(base[["schools_count", "schools_per_km2", "schools_pct"]].describe())
