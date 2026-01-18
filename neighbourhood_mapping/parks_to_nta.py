import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson")
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

parks = gpd.read_file("data/parks.geojson")

nta = nta.to_crs(3857)
parks = parks.to_crs(3857)

nta_area = nta.geometry.area
parks = parks[~parks.geometry.is_empty & parks.geometry.notna()]

parks_intersections = gpd.overlay(nta[[nta_id, "geometry"]], parks[["geometry"]], how="intersection")
parks_intersections["int_area"] = parks_intersections.geometry.area

parks_by_nta = parks_intersections.groupby(nta_id)["int_area"].sum().reset_index(name="park_area_m2")

out = nta[[nta_id, "geometry"]].merge(parks_by_nta, on=nta_id, how="left").fillna({"park_area_m2": 0})
out["nta_area_m2"] = nta_area.to_numpy()
out["park_coverage"] = out["park_area_m2"] / out["nta_area_m2"]
out["parks_pct"] = out["park_coverage"].rank(pct=True)

out[[nta_id, "parks_pct", "park_coverage", "park_area_m2"]].to_csv("data/nta_parks.csv", index=False)

out_wgs = out.to_crs(4326)
ax = out_wgs.plot(column="parks_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("data/parks_map.png", dpi=200)
