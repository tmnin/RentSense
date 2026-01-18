import os
import glob
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NYC_COUNTIES = {5, 47, 61, 81, 85}

def pick_col(df, names):
    for c in names:
        if c in df.columns:
            return c
    return None

def get_granular_commute_data():
    nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(3857)
    nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)
    nta_base = nta[[nta_id, "geometry"]].copy()

    shp_paths = sorted(glob.glob("data/tracts_2010/*.shp"))
    if not shp_paths:
        raise FileNotFoundError("No .shp files found in data/tracts_2010/")

    tracts_list = [gpd.read_file(p) for p in shp_paths]
    tracts = pd.concat(tracts_list, ignore_index=True)
    tracts = gpd.GeoDataFrame(tracts, geometry="geometry", crs=tracts_list[0].crs).to_crs(3857)

    geoid_col = pick_col(tracts, ["GEOID10", "geoid10", "GEOID", "geoid"])
    if geoid_col is None:
        geoid_col = next(c for c in tracts.columns if "geoid" in c.lower())
    tracts["TRACT_GEOID11"] = tracts[geoid_col].astype(str).str.replace(r"\D", "", regex=True).str.zfill(11).str[-11:]
    tracts = tracts.dropna(subset=["TRACT_GEOID11"]).copy()

    sld = pd.read_csv(
        "data/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv",
        low_memory=False
    )

    state_col = pick_col(sld, ["STATEFP", "STATEFP10", "STATE_FIPS", "STATE"])
    county_col = pick_col(sld, ["COUNTYFP", "COUNTYFP10", "CTY_FIPS", "COUNTY"])
    if state_col is None or county_col is None:
        raise KeyError("EPA SLD CSV missing STATEFP/COUNTYFP columns (or equivalent)")

    sld[state_col] = pd.to_numeric(sld[state_col], errors="coerce")
    sld[county_col] = pd.to_numeric(sld[county_col], errors="coerce")
    sld = sld[(sld[state_col] == 36) & (sld[county_col].isin(list(NYC_COUNTIES)))].copy()

    tractce_col = pick_col(sld, ["TRACTCE", "TRACTCE10", "TRACT", "TRACT10"])
    if tractce_col is None:
        raise KeyError("EPA SLD CSV does not contain a tract code column (TRACTCE/TRACT).")

    tractce = sld[tractce_col].astype(str).str.replace(r"\D", "", regex=True).str.zfill(6)
    statefp = sld[state_col].astype("Int64").astype(str).str.zfill(2)
    countyfp = sld[county_col].astype("Int64").astype(str).str.zfill(3)
    sld["TRACT_GEOID11"] = (statefp + countyfp + tractce).str.replace(r"\D", "", regex=True).str.zfill(11).str[-11:]

    sld["D4A"] = pd.to_numeric(sld["D4A"], errors="coerce")
    sld["D4C"] = pd.to_numeric(sld["D4C"], errors="coerce")
    sld = sld.dropna(subset=["TRACT_GEOID11", "D4A", "D4C"]).copy()

    tract_vals = sld.groupby("TRACT_GEOID11", as_index=False).agg(D4A=("D4A", "mean"), D4C=("D4C", "mean"))
    if tract_vals.empty:
        raise ValueError("No tract-level rows after aggregating SLD. Check TRACTCE/STATEFP/COUNTYFP parsing.")

    tr = tracts.merge(tract_vals, on="TRACT_GEOID11", how="inner")
    if tr.empty:
        raise ValueError(
            "0 rows after merging tracts with SLD tract aggregates.\n"
            f"Tracts sample:\n{tracts['TRACT_GEOID11'].head(10).to_string(index=False)}\n"
            f"SLD sample:\n{tract_vals['TRACT_GEOID11'].head(10).to_string(index=False)}"
        )

    tr["freq_score"] = tr["D4C"].rank(pct=True)
    tr["dist_score"] = 1.0 - tr["D4A"].rank(pct=True)
    tr["tract_commute"] = (tr["freq_score"] + tr["dist_score"]) / 2.0

    cent = tr[[ "TRACT_GEOID11", "tract_commute", "geometry"]].copy()
    cent["geometry"] = cent.geometry.centroid

    joined = gpd.sjoin(cent, nta_base, how="inner", predicate="within")
    if joined.empty:
        joined = gpd.sjoin(cent, nta_base, how="inner", predicate="intersects")
    if joined.empty:
        raise ValueError("0 rows after spatial join of tract centroids to NTA")

    agg = joined.groupby(nta_id, as_index=False).agg(commute_score=("tract_commute", "mean"))

    out = nta_base.merge(agg, on=nta_id, how="left")
    fill_val = float(out["commute_score"].mean(skipna=True)) if out["commute_score"].notna().any() else 0.5
    out["commute_score"] = out["commute_score"].fillna(fill_val)

    os.makedirs("results", exist_ok=True)
    out[[nta_id, "commute_score"]].to_csv("results/nta_commute.csv", index=False)

    mapped = nta.merge(out[[nta_id, "commute_score"]], on=nta_id, how="left")
    ax = mapped.to_crs(4326).plot(column="commute_score", figsize=(9, 9), legend=True)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("results/commute_map.png", dpi=200)

    print("Success! results/nta_commute.csv and results/commute_map.png")

if __name__ == "__main__":
    get_granular_commute_data()
