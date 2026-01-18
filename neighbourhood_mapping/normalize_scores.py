import pandas as pd
from functools import reduce

crime = pd.read_csv("results/nta_crime.csv")
noise = pd.read_csv("results/nta_noise.csv")
parks = pd.read_csv("results/nta_parks.csv")
amenities = pd.read_csv("results/nta_amenities.csv")
commute = pd.read_csv("results/nta_commute.csv")
jobs = pd.read_csv("results/nta_jobs.csv")
politics = pd.read_csv("results/nta_politics.csv")
schools = pd.read_csv("results/nta_schools.csv")

nta_id = "nta2020"

dfs = [crime, noise, parks, amenities, commute, jobs, politics, schools]
df = reduce(lambda l, r: l.merge(r, on=nta_id, how="outer"), dfs)

df["safety_score"] = 1 - df["crime_pct"]
df["quiet_score"] = 1 - df["noise_pct"]
df["parks_score"] = df["parks_pct"]
df["amenities_score"] = df["amenities_pct"]

if "commute_score" not in df.columns and "commute_pct" in df.columns:
    df["commute_score"] = df["commute_pct"]

df["jobs_score"] = df["job_score"]
df["politics_score"] = df["political_score"]

if "schools_score" not in df.columns and "schools_pct" in df.columns:
    df["schools_score"] = df["schools_pct"]

score_cols = [
    "safety_score",
    "quiet_score",
    "parks_score",
    "amenities_score",
    "commute_score",
    "jobs_score",
    "politics_score",
    "schools_score",
]

df[score_cols] = df[score_cols].apply(pd.to_numeric, errors="coerce").clip(0, 1)

df["overall_score"] = df[score_cols].mean(axis=1)

out = df[[nta_id] + score_cols + ["overall_score"]].sort_values("overall_score", ascending=False)

#adding names of NTAs
import geopandas as gpd

nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson")
name_col = next(c for c in ["ntaname", "NTAName", "nta_name", "NTA_NAME"] if c in nta.columns)
nta_names = nta[[nta_id, name_col]].drop_duplicates()

out = out.merge(nta_names, on=nta_id, how="left")

out = out[[nta_id, name_col] + score_cols + ["overall_score"]]


out.to_csv("results/nta_scores_all.csv", index=False)

print(out.describe())
print("Saved results/nta_scores_all.csv")
