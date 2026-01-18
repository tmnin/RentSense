import os
import glob
import requests
import pandas as pd
import geopandas as gpd

NYC_COUNTIES = {"005", "047", "061", "081", "085"}

def rent_year():
    return 2022

def get_acs_tract_rent(year, api_key):
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": "NAME,B25064_001E",
        "for": "tract:*",
        "in": "state:36 county:*",
        "key": api_key,
    }
    r = requests.get(url, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Census API HTTP {r.status_code}\n{r.text[:1000]}")
    try:
        rows = r.json()
    except Exception:
        raise RuntimeError(f"Census API did not return JSON.\nFirst 1000 chars:\n{r.text[:1000]}")
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[df["county"].isin(NYC_COUNTIES)].copy()
    df["B25064_001E"] = pd.to_numeric(df["B25064_001E"], errors="coerce")
    df.loc[df["B25064_001E"] <= 0, "B25064_001E"] = pd.NA
    df = df.dropna(subset=["B25064_001E"])
    df["TRACT_GEOID11"] = (
        df["state"].astype(str).str.zfill(2)
        + df["county"].astype(str).str.zfill(3)
        + df["tract"].astype(str).str.zfill(6)
    )
    return df[["TRACT_GEOID11", "B25064_001E"]].dropna()

def load_tracts():
    shp_paths = sorted(glob.glob("data/tracts_2010/*.shp"))
    if not shp_paths:
        raise FileNotFoundError("No .shp files found in data/tracts_2010/")
    gs = [gpd.read_file(p) for p in shp_paths]
    tr = pd.concat(gs, ignore_index=True)
    tr = gpd.GeoDataFrame(tr, geometry="geometry", crs=gs[0].crs)
    geoid_col = None
    for c in ["GEOID10", "geoid10", "GEOID", "geoid"]:
        if c in tr.columns:
            geoid_col = c
            break
    if geoid_col is None:
        geoid_col = next(c for c in tr.columns if "geoid" in c.lower())
    tr["TRACT_GEOID11"] = tr[geoid_col].astype(str).str.replace(r"\D", "", regex=True).str.zfill(11).str[-11:]
    return tr[["TRACT_GEOID11", "geometry"]].drop_duplicates()

def main():
    api_key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError('CENSUS_API_KEY is not set. Run: export CENSUS_API_KEY="YOUR_KEY"')

    year = rent_year()

    nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(3857)
    nta_id = next(c for c in ["nta2020", "ntacode", "NTACode", "NTA2020", "nta_code", "NTA_CODE"] if c in nta.columns)
    nta_base = nta[[nta_id, "geometry"]].copy()

    tract_rent = get_acs_tract_rent(year, api_key)

    tracts = load_tracts().to_crs(3857)
    tr = tracts.merge(tract_rent, on="TRACT_GEOID11", how="inner")
    if tr.empty:
        raise ValueError("0 rows after merging tracts with ACS rent")

    cent = tr.copy()
    cent["geometry"] = cent.geometry.centroid

    joined = gpd.sjoin(cent, nta_base, how="inner", predicate="within")
    if joined.empty:
        joined = gpd.sjoin(cent, nta_base, how="inner", predicate="intersects")
    if joined.empty:
        raise ValueError("0 rows after spatial join of tract centroids to NTA")

    agg = joined.groupby(nta_id, as_index=False).agg(median_gross_rent_usd=("B25064_001E", "median"))
    out = nta_base.merge(agg, on=nta_id, how="left")

    os.makedirs("results", exist_ok=True)
    out[[nta_id, "median_gross_rent_usd"]].to_csv("results/nta_rent.csv", index=False)
    print("Saved results/nta_rent.csv")

if __name__ == "__main__":
    main()
