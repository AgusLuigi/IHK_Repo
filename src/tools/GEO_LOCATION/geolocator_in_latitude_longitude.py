def geometry_extract_coordinates_lat_log(df):
    """
    Extracts Latitude and Longitude from the geometry column of a GeoDataFrame.
    Based on the Centroid, to support both points and polygons.
    """
    import geopandas as gpd
    if 'geometry' in df.columns and df.geometry is not None:
        # Ensure it's a GeoDataFrame
        if not isinstance(df, gpd.GeoDataFrame):
            df = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
        
        # Extraktion via Centroid
        df['latitude'] = df.geometry.centroid.y
        df['longitude'] = df.geometry.centroid.x
        
        print(f"✅ Koordinaten erfolgreich extrahiert ({len(df)} Zeilen).")
    else:
        print("⚠️ Keine Geometrie-Spalte gefunden. Extraktion übersprungen.")
    
    return df

# --- Anwendung in deinem Code ---
# df = geometry_extract_coordinates_lat_log(df)