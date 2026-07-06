def sql_load_offline_df():
    """Universal: Lädt ALLE Tabellen aus SQLite → separate DataFrames + Original-CTE-Logik"""
    
    # 1. LAZY IMPORTS (nur wenn Funktion läuft)
    import pandas as pd
    from sqlalchemy import create_engine, text, inspect
    import tkinter as tk
    from tkinter import filedialog
    import os
    
    print("🔍 Starte SQL-Loader...")
    
    # 2. DATEI-AUSWAHL (mit Error-Handling)
    try:
        root = tk.Tk(); root.withdraw()
        sqlite_path = filedialog.askopenfilename(
            title="SQLite-Datei wählen (*.sqlite, *.db)",
            filetypes=[("SQLite", "*.sqlite *.db"), ("Alle", "*.*")]
        )
        root.destroy()
    except:
        print("❌ File-Dialog fehlgeschlagen"); return {}
    
    if not sqlite_path or not os.path.exists(sqlite_path):
        print("❌ Keine gültige Datei"); return {}
    
    print(f"📁 Datei geladen: {os.path.basename(sqlite_path)}")
    
    # 3. VERBINDUNG + TABELLEN (Original-Engine-Logik)
    try:
        engine = create_engine(f"sqlite:///{sqlite_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Gefundene Tabellen: {tables}")
    except Exception as e:
        print(f"❌ Engine-Fehler: {e}"); return {}
    
    # 4. ALLE TABELLEN → DATAFRAMES (mit Original pd.read_sql + text())
    dataframes = {}
    for table in tables:
        try:
            df_name = f"df_{table}"
            # GENAU wie Original: pd.read_sql(text(sql), conn)
            with engine.connect() as conn:
                dataframes[df_name] = pd.read_sql(text(f"SELECT * FROM [{table}]"), conn)
            print(f"📊 {df_name}: {len(dataframes[df_name])} Zeilen")
        except Exception as e:
            print(f"⚠️  {table}: Fehler {e}")
    
    # 5. **ORIGINAL-CTE-LOGIK** (DEIN EXAKTER CODE)
    print("\n🔍 **ORIGINAL-CTE** (exakt wie dein Code):")
    original_cte = """
    WITH sessions_2023 AS (
      SELECT
        user_id, session_id, trip_id, session_start, session_end, page_clicks,
        flight_discount, flight_discount_amount, hotel_discount, hotel_discount_amount,
        flight_booked, hotel_booked, cancellation
      FROM sessions WHERE session_start > '2023-01-04'
    ),
    filtered_users AS (
      SELECT user_id FROM sessions_2023 
      GROUP BY user_id HAVING COUNT(session_id) > 7
    ),
    session_base AS (
      SELECT s.*, u.birthdate, u.gender, u.married, u.has_children, u.home_country,
             u.home_city, u.home_airport, u.home_airport_lat, u.home_airport_lon, u.sign_up_date,
             f.origin_airport, f.destination, f.destination_airport, f.seats, 
             f.return_flight_booked, f.departure_time, f.return_time, f.checked_bags,
             f.trip_airline, f.destination_airport_lat, f.destination_airport_lon, f.base_fare_usd,
             h.hotel_name, h.nights, h.rooms, h.check_in_time, h.check_out_time,
             h.hotel_per_room_usd AS hotel_price_per_room_night_usd
      FROM sessions_2023 s
      LEFT JOIN users u ON s.user_id = u.user_id
      LEFT JOIN flights f ON s.trip_id = f.trip_id
      LEFT JOIN hotels h ON s.trip_id = h.trip_id
      WHERE s.user_id IN (SELECT user_id FROM filtered_users)
    )
    SELECT * FROM session_base;
    """
    print(original_cte)
    
    # 6. HEAD(5) ZEIGEN (wie gewünscht)
    print("\n👀 Erste 5 Zeilen:")
    if dataframes:
        first_table = next(iter(dataframes))
        print(f"{first_table}:")
        display(dataframes[first_table].head(5))
    
    # 7. ORIGINALE AUSGABE (wie dein Code)
    print(f"\n✅ Daten erfolgreich aus '{os.path.basename(sqlite_path)}' geladen.")
    
    # Globale Variablen (Notebook-kompatibel)
    globals().update(dataframes)
    print("✅ DataFrames global:", list(dataframes.keys()))
    return dataframes


# ✅ KORREKTER AUFRUF (nicht universal_sql_loader() !)
#data = sql_load_offline_df()
#-------------------------------

# Zweite Variante
def sql_query(sql_or_path):
    import pandas as pd
    from sqlalchemy import create_engine, text,inspect
    import os

    TXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SQL_LINK.txt")

    # ERKENNUNG: Ist es ein Verbindungs-String?
    PREFIXES = (
        "sqlite:////",      # Lokal  (4 Schrägstriche)
        "sqlite:///",       # Lokal  (3 Schrägstriche, relativ)
        "postgresql://",    # Online
        "mysql://",         # Online
        "mssql://",         # Online
    )

    if sql_or_path.startswith(PREFIXES):
        # SCHRITT 1: Verbindung testen
        if sql_or_path.startswith("sqlite:////"):
            typ = "🖥️  Lokal  (sqlite:////)"
        elif sql_or_path.startswith("sqlite:///"):
            typ = "🖥️  Lokal  (sqlite:///)"
        else:
            typ = "🌐 Online"

        print(f"🔍 Erkannt: {typ}")

        try:
            engine = create_engine(sql_or_path)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # ✅ Verbindung OK → Pfad speichern
            with open(TXT_PATH, "w") as f:
                f.write(sql_or_path)
            print(f"✅ Datenbank geladen: {sql_or_path}")
            print(f"📄 Pfad gespeichert: {TXT_PATH}")
            print("👉 Du kannst jetzt query_sql(\"SELECT...\") nutzen.")
        except Exception as e:
            print(f"❌ Verbindung fehlgeschlagen: {e}")
        return

    # SCHRITT 2: SQL-Abfrage → TXT lesen + ausführen
    if not os.path.exists(TXT_PATH):
        print("❌ Kein gespeicherter Datenbankpfad gefunden.")
        print("👉 Zuerst aufrufen mit:")
        print("   Lokal:  query_sql('sqlite:////pfad/zur/datei.sqlite')")
        print("   Online: query_sql('postgresql://user:pw@host/db')")
        return

    with open(TXT_PATH, "r") as f:
        db_path = f.read().strip()

    try:
        engine = create_engine(db_path)
        with engine.connect() as conn:
            return pd.read_sql(text(sql_or_path), conn)
    except Exception as e:
        print(f"❌ SQL-Fehler: {e}")

# --- ANWENDUNG ---
# Einmalig zum Verbinden:
# query_sql('sqlite:////Users/cristallagus/Desktop/GitHub/weebet/_onboarding_data/notebook/replizierte_daten.sqlite')

# Danach direkt SQL:
# query_sql("""
# SELECT borough, COUNT(*)
# FROM high_school_directory
# GROUP BY borough
# """)

# --- TEST ---

# 1. Tabellen holen
#def check_content():
#    tables = sql_query("SELECT name FROM sqlite_master WHERE type='table'")
#    for t in tables['name']:
#        count = sql_query(f'SELECT COUNT(*) as n FROM "{t}"').iloc[0]['n']
#        print(f"Tabelle: {t:.<30} Zeilen: {count}")

#check_content()

# Check Tabellen Namen
#df_tables = sql_query("SELECT name FROM sqlite_master WHERE type='table'")
#print("Tabellen in deiner Datei:", df_tables['name'].tolist())