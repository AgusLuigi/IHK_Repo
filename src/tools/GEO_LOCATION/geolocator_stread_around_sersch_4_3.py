def compose_general_address(row, full_df):
    """
    Universal address repair (Berlin markets).

    Mindestqualität:
    - Straße UND Postleitzahl müssen sinnvoll belegt sein.
    - Hausnummer ist optional, wird nur gesucht, wenn Quellenlage das hergibt.

    Kaskade:
    0) Load sorce
    1) VALIDATION         -> needs_repair (only Street/Postcode relevant)
    2) INTERNAL MATCH (GEOPRECISION_OFFLINE_COMPARE, e.g., [4])
    2.1) Look in sorce.   -> no found go negst
    3) INTERNAL MATCH (GEOPRECISION_OFFLINE_COMPARE, e.g., [4])
    3.1) CACHE (precision 5) -> no found go negst
    4) API (Nominatim, controlled by API_GLOBAL_ADRESS)
    5) NEIGHBOR HNR (only if API_GLOBAL_ADRESS >= 4 and within dist_limit radius)
    """
    import re
    import time
    import sqlite3
    from pathlib import Path
    import warnings
    from time import monotonic
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderServiceError

    warnings.filterwarnings('ignore', 'Geometry is in a geographic CRS')

    # ---------- GLOBAL SETTINGS ----------
     
    # 1. Configuration & Helper Functions

    # Coordinate Precision Table (WGS84) for reference:
    # Decimals | Accuracy (approx.) | Use Case
    # ---------|--------------------|--------------------------------------------------
    # 0        | 111 km             | Global/Country level identification
    # 1        | 11.1 km            | Major city level identification
    # 2        | 1.11 km            | District/Neighborhood level identification
    # 3        | 111 m              | Large building blocks / Village level
    # 4        | 11.1 m             | Single plot / Market place (Ideal for matching)
    # 5        | 1.11 m             | Individual tree / Street sign level
    # 6        | 0.11 m (11 cm)     | Centimeter precision (Construction/Surveying)
    # 7        | 1.1 cm             | High-precision GPS systems

    GEOPRECISION_OFFLINE_COMPARE = [4]  # mehrere zalen Möglich Geo-Genauigkeit in der datenbank suche für internen Match (~11m)

    # API-Level-Regler:
    # 7: Zentimeter, 
    # 6: sehr fein, 
    # 5: Objekt, 
    # 4: Hausnummer, 
    # 3: Straße, 
    # 2: Bezirk, 
    # 1: Stadt, 
    # 0: Land
    API_GLOBAL_ADRESS = 4  # API/Neighbor-Stufe für api genauigkeit suche 

    API_SLEEP = 5                 # Pause zwischen API-Versuchen
    API_BLOCK_WAIT_TIME = 61      # Startwartezeit bei 429 (wird exponentiell gesteigert)
    CITY_FALLBACK = "Berlin"
    USER_AGENT = "data_repair_study_v15"

    # Stufen-Schalter (falls du später einzelne Layer deaktivieren willst)
    USE_CACHE = True
    USE_INTERNAL_MATCH = True
    USE_API = True
    USE_NEIGHBOR_HNR = True  # Nur relevant ab API_GLOBAL_ADRESS >= 4

    # globaler Throttle-State (geteilt über alle Zeilen)
    if not hasattr(compose_general_address, "_last_api_call_ts"):
        compose_general_address._last_api_call_ts = 0.0
    GLOBAL_MIN_DELAY = 1.2  # Mindestabstand zwischen Nominatim-Requests in Sekunden

    address_mapping_config = {
        "street": ["addr:street", "street"],
        "housenumber": ["addr:housenumber", "housenumber"],
        "postcode": ["addr:postcode", "post_code"],
        "city": ["addr:city", "city"]
    }

    def get_api_settings(level):
        """Mapt globales Level auf Nominatim-zoom und Distanzlimit (in Grad)."""
        zoom_map = {7: 18, 6: 18, 5: 17, 4: 16, 3: 14, 2: 10, 1: 8, 0: 3}
        dist_map = {
            7: 0.00005,  # ~5m
            6: 0.0001,   # ~11m
            5: 0.0005,   # ~55m
            4: 0.0018,   # ~200m
            3: 0.005,    # ~550m
            2: 0.02,     # ~2.2km
            1: 0.1,      # ~11km
            0: 1.0       # global
        }
        return zoom_map.get(level, 16), dist_map.get(level, 0.0009)

    api_zoom, dist_limit = get_api_settings(API_GLOBAL_ADRESS)

    # ---------- BASIC VALUE HANDLING ----------
    def clean(v):
        v = str(v).strip()
        return "" if v.lower() in ["nan", "none", "n/a", "null", ""] else v

    def get_val(key_list):
        for col in key_list:
            if col in row.index:
                val = clean(row.get(col, ''))
                if val:
                    return val
        return ""

    street = get_val(address_mapping_config["street"])
    hnr = get_val(address_mapping_config["housenumber"])
    postcode = get_val(address_mapping_config["postcode"])
    city_val = get_val(address_mapping_config["city"])
    target_city = city_val if city_val else CITY_FALLBACK

    def is_invalid_street(val):
        v = clean(val)
        if not v:
            return True
        v_lower = v.lower()
        if v_lower in ['nan', 'n/a', 'none', 'null', target_city.lower()]:
            return True
        if v_lower.isdigit():
            return True
        return False

    def is_invalid_postcode(val):
        v = clean(val)
        if not v:
            return True
        if not v.isdigit():
            return True
        return len(v) < 4  # einfache Heuristik

    # ---------- MINDESTQUALITÄT (nur Straße/PLZ) ----------
    # Zoom Level Sorce HNR wird NICHT für needs_repair berücksichtigt.
    needs_repair = is_invalid_street(street) or is_invalid_postcode(postcode)

    # ---------- CACHE LAYER (SQLite) ----------
    cache_dir = Path("data/geometry_adres")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_db = cache_dir / "geometry_address_cache.sqlite"

    def init_cache():
        conn = sqlite3.connect(cache_db)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS address_cache (
                cache_key TEXT PRIMARY KEY,
                street TEXT,
                housenumber TEXT,
                postcode TEXT,
                city TEXT,
                full_address TEXT,
                lat REAL,
                lon REAL,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn

    def get_cache_key(lat, lon, precision=5):
        return f"{round(lat, precision)}_{round(lon, precision)}"

    def load_cache(conn, lat, lon, precision=5):
        key = get_cache_key(lat, lon, precision)
        cur = conn.cursor()
        cur.execute("""
            SELECT street, housenumber, postcode, city, full_address
            FROM address_cache WHERE cache_key = ?
        """, (key,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "street": r[0] or "",
            "housenumber": r[1] or "",
            "postcode": r[2] or "",
            "city": r[3] or "",
            "full_address": r[4] or ""
        }

    def save_cache(conn, lat, lon, street_val, hnr_val, pc_val, city_val, full, source="nominatim", precision=5):
        key = get_cache_key(lat, lon, precision)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO address_cache
            (cache_key, street, housenumber, postcode, city, full_address, lat, lon, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (key, street_val, hnr_val, pc_val, city_val, full, lat, lon, source))
        conn.commit()

    cache_conn = init_cache()
    cached_result = None
    api_used_in_this_call = False

    try:
        if needs_repair:
            curr_centroid = row.geometry.centroid
            curr_lat, curr_lon = curr_centroid.y, curr_centroid.x
            found_final = False

            # ---------- 1) INTERNAL MATCH (Quelle zuerst ausreizen) ----------
            if USE_INTERNAL_MATCH:
                for precision in GEOPRECISION_OFFLINE_COMPARE:
                    target_lat, target_lon = round(curr_lat, precision), round(curr_lon, precision)
                    mask = (
                        (full_df.index != row.name) &
                        (full_df.geometry.centroid.y.round(precision) == target_lat) &
                        (full_df.geometry.centroid.x.round(precision) == target_lon)
                    )
                    potential_matches = full_df[mask]
                    for _, match in potential_matches.iterrows():
                        m_street = clean(match.get('addr:street', match.get('street', '')))
                        if not is_invalid_street(m_street):
                            street = m_street
                            hnr = clean(match.get('addr:housenumber', match.get('housenumber', '')))
                            postcode = clean(match.get('addr:postcode', match.get('post_code', '')))
                            print(f"[TRACE] INTERNAL match for row {row.name} at precision {precision}")
                            found_final = True
                            break
                    if found_final:
                        break

            # ---------- 2) CACHE (nur wenn Quelle keinen Treffer hatte) ----------
            if USE_CACHE and not found_final:
                cached_result = load_cache(cache_conn, curr_lat, curr_lon, precision=5)
                if cached_result:
                    print(f"[TRACE] CACHE hit for row {row.name}")
                    if is_invalid_street(street):
                        street = cached_result["street"]
                    if is_invalid_postcode(postcode):
                        postcode = cached_result["postcode"]
                    # HNR optional ergänzen
                    if not clean(hnr) and cached_result["housenumber"]:
                        hnr = cached_result["housenumber"]
                    if cached_result["city"]:
                        target_city = cached_result["city"]

                    if not is_invalid_street(street) and not is_invalid_postcode(postcode):
                        found_final = True

            # ---------- 3) API (nur wenn Quelle + Cache NICHT reichen) ----------
            if USE_API and not found_final:
                print(f"[TRACE] API required for row {row.name} (Level: {API_GLOBAL_ADRESS}, zoom={api_zoom})")
                geolocator = Nominatim(user_agent=USER_AGENT)
                current_wait = API_BLOCK_WAIT_TIME

                for attempt in range(3):
                    try:
                        # GLOBALER THROTTLE vor dem Request
                        now = monotonic()
                        delta = now - compose_general_address._last_api_call_ts
                        if delta < GLOBAL_MIN_DELAY:
                            sleep_for = GLOBAL_MIN_DELAY - delta
                            print(f"[TRACE] Global API throttle: sleeping {sleep_for:.2f}s before Nominatim call.")
                            time.sleep(sleep_for)

                        location = geolocator.reverse(
                            (curr_lat, curr_lon),
                            exactly_one=True,
                            language='de',
                            timeout=15,
                            zoom=api_zoom
                        )
                        compose_general_address._last_api_call_ts = monotonic()

                        # Fester Sleep NACH der Anfrage
                        print(f"[TRACE] Post-call cooldown: sleeping {API_SLEEP}s after Nominatim call.")
                        time.sleep(API_SLEEP)

                        if location and "address" in location.raw:
                            api_used_in_this_call = True
                            osm = location.raw.get('address', {})
                            street = osm.get('road') or osm.get('pedestrian') or osm.get('footway') or street
                            hnr = osm.get('house_number', '') or hnr
                            postcode = osm.get('postcode', postcode)
                            target_city = osm.get('city') or osm.get('town') or target_city

                            # ---------- 4) NEIGHBOR HNR (nur wenn Level erlaubt) ----------
                            if USE_NEIGHBOR_HNR and API_GLOBAL_ADRESS >= 4 and not clean(hnr):
                                hnr_col = next((c for c in ["addr:housenumber", "housenumber"] if c in full_df.columns), None)
                                if hnr_col:
                                    valid_hnr_df = full_df[
                                        full_df[hnr_col].apply(lambda x: bool(clean(x)))
                                    ]
                                    if not valid_hnr_df.empty:
                                        distances = valid_hnr_df.geometry.distance(curr_centroid)
                                        min_dist = distances.min()
                                        if min_dist <= dist_limit:
                                            hnr = str(valid_hnr_df.loc[distances.idxmin(), hnr_col])
                                            print(
                                                f"[TRACE] Neighbor HNR within {round(min_dist*111000, 1)}m "
                                                f"(limit ~{round(dist_limit*111000)}m) for row {row.name}."
                                            )
                                        else:
                                            print(
                                                f"[WARN] No neighbor HNR within safety radius "
                                                f"({round(dist_limit*111000)}m) for row {row.name}."
                                            )

                            # jetzt erst Cache befüllen, weil Quelle + Cache vorher nichts hatten
                            save_cache(
                                cache_conn,
                                curr_lat, curr_lon,
                                clean(street), clean(hnr), clean(postcode), clean(target_city),
                                f"{clean(street)} {clean(hnr)} {clean(postcode)} {clean(target_city)}".strip()
                            )
                            found_final = True
                            break

                    except GeocoderServiceError as e:
                        if "429" in str(e):
                            print(f"[WARN] Rate Limit (429). Waiting {current_wait}s...")
                            time.sleep(current_wait)
                            current_wait *= 2
                        else:
                            print(f"[ERROR] Service error: {e}")
                            break
                    except Exception as e:
                        print(f"[ERROR] Unexpected error in row {row.name}: {e}")
                        break

        # ---------- FINAL FORMATTING ----------
        postcode_clean = re.sub(r'\D', '', str(postcode))[:5]
        street_final = clean(street)
        hnr_final = clean(hnr)
        addr_line = f"{street_final} {hnr_final}".strip()
        address_base = " ".join([p for p in [addr_line, postcode_clean] if p]).strip()

        if address_base:
            if target_city.lower() in address_base.lower():
                return address_base
            return f"{address_base} {target_city}"
        return target_city

    finally:
        cache_conn.close()