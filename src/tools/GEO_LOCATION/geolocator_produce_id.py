# --- SURGICAL ID ENRICHMENT (INDEX LOGIC) ---

def geometry_enrich_spatial_ids(df_input):
    print("📍 Surgically adding the 3 IDs (LOR-Standard)...")
    
    if not isinstance(df_input, gpd.GeoDataFrame):
        df_input = gpd.GeoDataFrame(df_input, geometry='geometry', crs="EPSG:4326")

    try:
        # 1. Load LOR boundaries
        lor_boundaries = ox.features_from_place("Berlin, Germany", tags={'admin_level': ['9', '10']})
        
        # 2. Prepare reference data
        # We reset the index to safely access the IDs (prevents 'Level osmid not found')
        lor_flat = lor_boundaries.reset_index()
        
        # Districts (Admin Level 9)
        districts_ref = lor_flat[lor_flat['admin_level'] == '9'].copy()
        districts_ref['dist_id_temp'] = districts_ref['osmid'].astype(str) if 'osmid' in districts_ref.columns else districts_ref.index.astype(str)
        districts_ref = districts_ref[['name', 'dist_id_temp', 'geometry']]

        # Neighborhoods / Ortsteile (Admin Level 10)
        neighborhoods_ref = lor_flat[lor_flat['admin_level'] == '10'].copy()
        neighborhoods_ref['neigh_id_temp'] = neighborhoods_ref['osmid'].astype(str) if 'osmid' in neighborhoods_ref.columns else neighborhoods_ref.index.astype(str)
        neighborhoods_ref = neighborhoods_ref[['name', 'neigh_id_temp', 'geometry']]

        # 3. Spatial joins on temporary object (to avoid corrupting original columns with suffixes)
        df_temp = df_input.copy()
        df_temp = df_temp.to_crs(districts_ref.crs)

        # Join Districts
        df_temp = gpd.sjoin(df_temp, districts_ref, how='left', predicate='within')
        df_temp = df_temp.rename(columns={'name': 'district_new', 'dist_id_temp': 'district_id_new'})
        if 'index_right' in df_temp.columns: df_temp = df_temp.drop(columns=['index_right'])

        # Join Neighborhoods
        df_temp = gpd.sjoin(df_temp, neighborhoods_ref, how='left', predicate='within')
        df_temp = df_temp.rename(columns={'name': 'neighborhood_new', 'neigh_id_temp': 'neighborhood_id_new'})
        if 'index_right' in df_temp.columns: df_temp = df_temp.drop(columns=['index_right'])

        # 4. SURGICAL TRANSFER TO ORIGINAL
        # We only assign the 3 IDs and the names. Everything else remains untouched.
        
        # ID 1: district_id (From official OSM source)
        df_input['district_id'] = df_temp['district_id_new'].fillna('N/A')
        
        # ID 2: neighborhood_id (From official OSM source)
        df_input['neighborhood_id'] = df_temp['neighborhood_id_new'].fillna('N/A')
        
        # ID 3: market_id food_market = FM (Technical ID, if not already present)
        if 'market_id' not in df_input.columns:
            df_input['market_id'] = [f"FM{i+1:03d}" for i in range(len(df_input))]

        # Update names (only if they are empty or coming from the join)
        df_input['district'] = df_temp['district_new'].fillna(df_input.get('district', 'N/A'))
        df_input['neighborhood_name'] = df_temp['neighborhood_new'].fillna(df_input.get('neighborhood_name', 'N/A'))

        print(f"✅ Success: 3 IDs created for {len(df_input)} markets. Original data (emails, times etc.) remained untouched.")
        return df_input

    except Exception as e:
        print(f"❌ Error: {e}")
        return df_input

# Execution
#cl_food_markets_berlin = enrich_spatial_ids(cl_food_markets_berlin)

# ---------------------------------------------------------------------------

# alternative ID with Fix numbers

# --- STEP 2: SURGICAL ID ENRICHMENT (LOCAL GEO-DATA) ---

def geometry_enrich_spatial_ids_fix(df_input):
    import geopandas as gpd
    import pandas as pd
    from pathlib import Path
    
    print("📍 Surgically adding IDs (LOR-Standard via Spatial Join)...")
    
    DISTRICT_MAPPING = {
        'Mitte': '11001001',
        'Friedrichshain-Kreuzberg': '11002002',
        'Pankow': '11003003',
        'Charlottenburg-Wilmersdorf': '11004004',
        'Spandau': '11005005',
        'Steglitz-Zehlendorf': '11006006',
        'Tempelhof-Schöneberg': '11007007',
        'Neukölln': '11008008',
        'Treptow-Köpenick': '11009009',
        'Marzahn-Hellersdorf': '11010010',
        'Lichtenberg': '11011011',
        'Reinickendorf': '11012012'
    }
    
    # 1. Direct path check
    lor_path = Path.cwd().parents[1] / "sources" / "lor_ortsteile.geojson"
    
    if not lor_path.exists():
        print(f"⚠️ Warning: {lor_path} not found. Skipping spatial enrichment.")
        return df_input

    try:
        # Load Berlin Geo-Data
        berlin_gdf = gpd.read_file(lor_path)
        name_col = next((c for c in ['OT_NAME', 'PLRNAME', 'STADTEIL'] if c in berlin_gdf.columns), 'BEZIRK')

        # Ensure input is a GeoDataFrame
        if not isinstance(df_input, gpd.GeoDataFrame):
            # CRS EPSG:4326 is standard for Lat/Lon coordinates
            df_input = gpd.GeoDataFrame(df_input, geometry='geometry', crs="EPSG:4326")

        # 2. Spatial Join
        # This matches your data points with the polygons in lor_ortsteile.geojson
        joined = gpd.sjoin(df_input, berlin_gdf[['BEZIRK', 'spatial_name', 'geometry']], 
                           how='left', predicate='within')

        # 3. Surgical assignment of IDs        
        df_input['district'] = joined['BEZIRK'].fillna(df_input.get('district', 'Unknown'))
        df_input['district_id'] = joined['BEZIRK'].map(DISTRICT_MAPPING).fillna('99999999')
        
        # Neighborhood ID (The specific local area code from GeoJSON)
        df_input['neighborhood'] = joined[name_col].fillna('Outside Berlin')
        df_input['neighborhood_id'] = joined['spatial_name'].astype(str).replace('nan', 'Outside Berlin')
                
        # 4. Generate unique market_id if not present
        if 'market_id' not in df_input.columns:
            df_input['market_id'] = [f"FM{i+1:03d}" for i in range(len(df_input))]

        print(f"✅ IDs enriched successfully for {len(df_input)} records.")
        return df_input

    except Exception as e:
        print(f"❌ Error in enrichment: {e}")
        return df_input

# Execution
# This will now correctly fill both district_id (Bezirk) and neighborhood_id (Kiez)
#cl_food_markets_berlin = enrich_spatial_ids(cl_food_markets_berlin)