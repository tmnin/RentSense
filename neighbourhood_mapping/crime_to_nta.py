import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

crime = pd.read_csv("data/nypd_12m.csv")
crime["CMPLNT_FR_DT"] = pd.to_datetime(crime["CMPLNT_FR_DT"], errors="coerce")
crime["Latitude"] = pd.to_numeric(crime["Latitude"], errors="coerce")
crime["Longitude"] = pd.to_numeric(crime["Longitude"], errors="coerce")
crime = crime.dropna(subset=["Latitude", "Longitude", "CMPLNT_FR_DT"])

crime_gdf = gpd.GeoDataFrame(crime, geometry=gpd.points_from_xy(crime["Longitude"], crime["Latitude"]), crs=4326)

joined = gpd.sjoin(crime_gdf, nta[[nta_id, "geometry"]], predicate="intersects")
counts = joined.groupby(nta_id).size().reset_index(name="crime_count")

nta = nta.merge(counts, on=nta_id, how="left").fillna({"crime_count": 0})

nta_proj = nta.to_crs(3857)
nta["crime_per_km2"] = nta["crime_count"] / (nta_proj.geometry.area / 1_000_000)
nta["crime_pct"] = nta["crime_per_km2"].rank(pct=True)

ax = nta.plot(column="crime_pct", figsize=(9, 9), legend=True)
plt.axis("off")
plt.tight_layout()
plt.savefig("data/crime_map.png", dpi=200)

nta[[nta_id, "crime_pct", "crime_per_km2", "crime_count"]].to_csv(
    "data/nta_crime.csv",
    index=False
)
