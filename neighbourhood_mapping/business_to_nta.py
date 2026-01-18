import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def get_business_density_data():
    nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(2263)
    nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)
    
    nta_area_km2 = nta.geometry.area / 10763910
    
    df = pd.read_csv("data/Legally_Operating_Businesses.csv", low_memory=False)
    df.columns = df.columns.str.strip().str.upper()

    lat_col = next((c for c in df.columns if "LATITUDE" in c), None)
    lon_col = next((c for c in df.columns if "LONGITUDE" in c), None)

    if lat_col and lon_col:
        df = df.dropna(subset=[lat_col, lon_col])
        biz_gdf = gpd.GeoDataFrame(
            df, 
            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
            crs=4326
        ).to_crs(2263)
        
        joined = gpd.sjoin(biz_gdf, nta[[nta_id, 'geometry']], predicate='within')
        biz_counts = joined.groupby(nta_id).size().reset_index(name='biz_count')
    else:
        biz_counts = pd.DataFrame({nta_id: nta[nta_id], 'biz_count': 0})

    base = nta[[nta_id, 'geometry']].merge(biz_counts, on=nta_id, how='left').fillna(0)
    base['biz_density'] = base['biz_count'] / nta_area_km2
    base['job_score'] = base['biz_density'].rank(pct=True)

    base[[nta_id, 'job_score', 'biz_count']].to_csv("results/nta_jobs.csv", index=False)
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    base.plot(column="job_score", cmap="YlGn", legend=True, ax=ax)
    ax.set_axis_off()
    plt.savefig("results/jobs_map.png", dpi=300, bbox_inches='tight')

if __name__ == "__main__":
    get_business_density_data()