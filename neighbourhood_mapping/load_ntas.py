import geopandas as gpd
import matplotlib.pyplot as plt

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson")
nta = nta.to_crs(epsg=4326)

ax = nta.plot(figsize=(8, 8))
plt.axis("off")
plt.tight_layout()
plt.savefig("nta_map.png", dpi=200)
print("saved nta_map.png")
