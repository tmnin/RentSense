import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def get_politics_data():
    nta = gpd.read_file("data/Neighborhood_Tabulation_Areas_2020.geojson").to_crs(4326)
    nta_id = next(c for c in ["ntacode", "NTACode", "NTA2020", "nta2020", "nta_code", "NTA_CODE"] if c in nta.columns)

    boro_enrollment = {
        'MN': 0.15,
        'BK': 0.20,
        'BX': 0.18,
        'QN': 0.35,
        'SI': 0.65 
    }

    progressive_strongholds = [
        'Astoria', 'Long Island City', 'Sunnyside', 'Park Slope', 
        'Williamsburg', 'Greenpoint', 'Bushwick', 'Bed-Stuy', 
        'Harlem', 'East Village', 'Lower East Side'
    ]
    
    conservative_pockets = [
        'Borough Park', 'Midwood', 'Sheepshead Bay', 'Gerritsen Beach',
        'Bayside', 'Whitestone', 'Howard Beach', 'Middle Village',
        'Tottenville', 'Great Kills', 'New Dorp'
    ]

    def calculate_enrollment_score(row):
        boro_code = row[nta_id][:2]
        base_score = boro_enrollment.get(boro_code, 0.4)
        
        nta_name = str(row.get('ntaname', row.get('NTAName', '')))
        
        if any(hood.lower() in nta_name.lower() for hood in progressive_strongholds):
            base_score -= 0.15
        elif any(hood.lower() in nta_name.lower() for hood in conservative_pockets):
            base_score += 0.25
            
        return max(0, min(1, base_score))

    nta['political_score'] = nta.apply(calculate_enrollment_score, axis=1)
    
    nta[[nta_id, 'political_score']].to_csv("results/nta_politics.csv", index=False)
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    nta.plot(column="political_score", cmap="RdBu_r", legend=True, ax=ax)
    ax.set_axis_off()
    plt.savefig("results/politics_map.png", dpi=300, bbox_inches='tight')

if __name__ == "__main__":
    get_politics_data()