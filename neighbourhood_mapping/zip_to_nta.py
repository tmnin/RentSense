import geopandas as gpd
import pandas as pd

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson")
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

zips = gpd.read_file("data/zip_areas.geojson")
zip_id = "postalCode"

nta = nta.to_crs(3857)
zips = zips.to_crs(3857)

zips[zip_id] = zips[zip_id].astype(str).str.extract(r"(\d{5})", expand=False)
zips = zips.dropna(subset=[zip_id]).copy()
zips[zip_id] = zips[zip_id].astype(str)

zips = zips[[zip_id, "geometry"]].drop_duplicates(subset=[zip_id])
zips["zip_area_m2"] = zips.geometry.area

inter = gpd.overlay(zips[[zip_id, "zip_area_m2", "geometry"]], nta[[nta_id, "geometry"]], how="intersection")
inter["overlap_m2"] = inter.geometry.area
inter["overlap_frac"] = inter["overlap_m2"] / inter["zip_area_m2"]

out = inter[[zip_id, nta_id, "overlap_frac", "overlap_m2"]].sort_values([zip_id, "overlap_frac"], ascending=[True, False])

out.to_csv("results/zip_to_nta.csv", index=False)

print(out.head(20))
print("rows:", len(out))
print("unique zips:", out[zip_id].nunique())
