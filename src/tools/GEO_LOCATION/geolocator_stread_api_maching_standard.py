def enrich_with_neighborhoods(input_csv, output_csv):
    """
    Lädt Daten, bestimmt den Berliner Bezirk (neighborhood) via Geopy 
    und bereinigt die Postleitzahlen.
    """
    import pandas as pd
    from geopy.geocoders import Nominatim
    from time import sleep
    # 1. Daten laden
    try:
        df = pd.read_csv(input_csv)
        print(f"✅ Datei '{input_csv}' geladen.")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Datei: {e}")
        return

    # 2. Geocoder initialisieren
    geolocator = Nominatim(user_agent="berlin_bezirk_locator_v2")

    def get_bezirk(lat, lon):
        try:
            # Reverse Geocoding
            location = geolocator.reverse((lat, lon), exactly_one=True, language='de')
            sleep(1)  # Rate Limit einhalten (wichtig!)
            
            if location and "address" in location.raw:
                addr = location.raw["address"]
                # Suche nach Bezirk in verschiedenen Feldern
                return (addr.get("city_district") or 
                        addr.get("borough") or 
                        addr.get("suburb") or # 'suburb' oft präziser in Berlin
                        addr.get("county"))
            return None
        except:
            return None

    # 3. Logik anwenden
    print("🔄 Starte Geokodierung (das kann dauern, 1 Sekunde pro Zeile)...")
    df["neighborhood"] = df.apply(lambda row: get_bezirk(row["latitude"], row["longitude"]) if pd.notnull(row["latitude"]) and pd.notnull(row["longitude"]) else None, axis=1)

    # 4. Postleitzahlen bereinigen (numeric format)
    if "postcode" in df.columns:
        df["postcode"] = pd.to_numeric(df["postcode"], errors="coerce").astype("Int64")

    # 5. Speichern
    df.to_csv(output_csv, index=False)
    print(f"🚀 SUCCESS: Datei gespeichert als '{output_csv}'")
    
    return df

# --- ANWENDUNG ---
# df = enrich_with_neighborhoods("ubahn_with_stadtteil.csv", "ubahn_with_neighborhoods.csv")