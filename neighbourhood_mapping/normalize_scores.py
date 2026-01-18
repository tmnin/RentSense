import pandas as pd
from functools import reduce

crime = pd.read_csv("results/nta_crime.csv")
noise = pd.read_csv("results/nta_noise.csv")
parks = pd.read_csv("results/nta_parks.csv")
amenities = pd.read_csv("results/nta_amenities.csv")

nta_id = crime.columns[0]

dfs = [crime, noise, parks, amenities]
df = reduce(lambda l, r: l.merge(r, on=nta_id, how="outer"), dfs).fillna(0)

df["safety_score"] = 1 - df["crime_pct"]
df["quiet_score"] = 1 - df["noise_pct"]
df["parks_score"] = df["parks_pct"]
df["amenities_score"] = df["amenities_pct"]

out = df[[nta_id, "safety_score", "quiet_score", "parks_score", "amenities_score"]]

out.to_csv("results/nta_scores_base.csv", index=False)

print(out.describe())
