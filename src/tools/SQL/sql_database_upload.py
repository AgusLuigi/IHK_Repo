# --- INITIALISIERUNG ---
import ipywidgets as widgets
output = widgets.Output()
engine = None

def get_all_dataframes():
    import __main__
    import pandas as pd
    """Holt alle verfügbaren DataFrames aus dem lokalen Speicher."""
    return {name: getattr(__main__, name) for name in dir(__main__) 
            if isinstance(getattr(__main__, name), pd.DataFrame) and not name.startswith('_')}

def get_detailed_permissions(engine, schema):
    from sqlalchemy import text
    """Prüft rein lesend (systemseitig) die Rechte für das gewählte Schema."""
    try:
        with engine.connect() as conn:
            user_name = conn.execute(text("SELECT current_user")).scalar()

            can_create = conn.execute(text(f"SELECT has_schema_privilege('{user_name}', '{schema}', 'CREATE')")).scalar()
            is_super = conn.execute(text("SELECT usesuper FROM pg_user WHERE usename = current_user")).scalar()
            
            level = "Admin/Owner (Full Access)" if (can_create or is_super) else "User (Insert/Append Only)"
            return {"user": user_name, "can_create": can_create or is_super, "level": level}
    except:
        return {"user": "Unknown", "can_create": False, "level": "Permission Check Error"}

def sql_upload_pipeline():
    import ipywidgets as widgets
    import __main__
    import pandas as pd
    from sqlalchemy import create_engine, text, inspect
    from IPython.display import display, clear_output
    from geoalchemy2 import Geometry

    available_dfs = get_all_dataframes()
    login_container = widgets.VBox()
    
    with output:
        clear_output()

    if not available_dfs:
        with output: print("⚠️ Keine DataFrames im Speicher gefunden.")
        display(output)
        return

    # --- TEIL 1: DATABASE CONNECTION (LOGIN) ---
    layout_single = widgets.Layout(width='95%', height='32px')
    link_input = widgets.Textarea(description="SQL Link:", placeholder="postgresql://user:password@host:5432/dbname?sslmode=require", layout=widgets.Layout(width='95%', height='50px'))

    user_i = widgets.Textarea(description="User:", placeholder="z.B. postgres", layout=layout_single)
    pass_i = widgets.Password(description="Password:", placeholder="Passwort", layout=layout_single)
    host_i = widgets.Textarea(description="Host:", placeholder="z.B. db.neon.tech", layout=layout_single)
    db_i   = widgets.Textarea(description="DB Name:", placeholder="z.B. neondb", layout=layout_single)
    btn_connect = widgets.Button(description="Connect", button_style="info", layout=widgets.Layout(width='95%', height='45px'))

    # Fix Keyboard-Interruption Notebooks
    js_fix = widgets.HTML("<script>document.querySelectorAll('textarea, input').forEach(el => { el.addEventListener('keydown', e => e.stopPropagation(), true); });</script>")

    login_container.children = [
        js_fix, 
        widgets.HTML("<h3>1. Database Connection</h3>"),
        link_input, 
        widgets.HTML("<b>Or enter individual credentials:</b>"),
        user_i, pass_i, host_i, db_i, 
        btn_connect
    ]
    display(login_container)
    display(output) 

    def on_connect_clicked(b):
        global engine
        url = link_input.value.strip()
        if not url:
            u, p, h, d = user_i.value.strip(), pass_i.value.strip(), host_i.value.strip(), db_i.value.strip()
            url = f"postgresql://{u}:{p}@{h}/{d}?sslmode=require"
        
        if "sslmode" not in url and "postgresql" in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        
        try:
            with output: print("🔄 Connecting...")
            engine = create_engine(url)
            with engine.connect() as conn: conn.execute(text("SELECT 1"))
            
            login_container.close() # Login-UI
            with output:
                clear_output()
                print("✅ Connection successful!")
            
            show_data_selection(engine)
            
        except Exception as e:
            with output: print(f"❌ Connection Error: {e}")

    btn_connect.on_click(on_connect_clicked)

def show_data_selection(engine):
    import ipywidgets as widgets
    from sqlalchemy import text, inspect
    from IPython.display import display, clear_output
    available_dfs = get_all_dataframes()
    inspector = inspect(engine)
    all_schemas = inspector.get_schema_names()

    # --- MAPPING & DYNAMIC SQL PUSH ---
    status_output = widgets.Output()
    
    df_select = widgets.Dropdown(options=available_dfs.keys(), description="Source DF:")
    schema_select = widgets.Dropdown(options=all_schemas, value='public' if 'public' in all_schemas else all_schemas[0], description="Schema:")
    target_table_name = widgets.Textarea(description="Table Name:", placeholder="e.g., upload_results")
    
    # "No Connection / Upload Only" permanenter Standard-Fallback
    pk_col = widgets.Dropdown(description="Primary Key:", options=["No Connection / Upload Only"]) 
    rel_table = widgets.Dropdown(description="Link to DB:", options=[("No Mapping", None)])
    rel_col = widgets.Dropdown(description="DB Column:", options=["No connected"])

    def update_ui_by_permissions(change=None):
        """Aktualisiert Berechtigungs-Visualisierung und PK-Optionen."""
        perms = get_detailed_permissions(engine, schema_select.value)
        
        with status_output:
            clear_output()
            color = "#4CAF50" if perms["can_create"] else "#FF9800"
            display(widgets.HTML(f"""
                <div style='border: 2px solid {color}; padding: 8px; border-radius: 5px; background-color: #fcfcfc;'>
                    <b>Schema:</b> {schema_select.value} | <b>User:</b> {perms['user']} | <b>Status:</b> {perms['level']}
                </div>
            """))

        # PK Dropdown Logik
        if df_select.value:
            cols = list(available_dfs[df_select.value].columns)
            pk_col.options = ["No Connection / Upload Only"] + cols
        else:
            pk_col.options = ["No Connection / Upload Only"]
        
        # Table Mapping load
        try:
            tables = inspector.get_table_names(schema=schema_select.value)
            rel_table.options = [("No Mapping", None)] + [(t, t) for t in tables]
        except:
            rel_table.options = [("No Mapping", None)]

    def update_db_cols(change):
        """Lädt Spalten der gewählten Referenz-Tabelle."""
        if rel_table.value:
            try:
                cols = [c['name'] for c in inspector.get_columns(rel_table.value, schema=schema_select.value)]
                rel_col.options = cols
            except: rel_col.options = ["No connected"]
        else:
            rel_col.options = ["No connected"]

    # Bind observers
    schema_select.observe(update_ui_by_permissions, names='value')
    df_select.observe(update_ui_by_permissions, names='value')
    rel_table.observe(update_db_cols, names='value')

    update_ui_by_permissions()

    btn_val = widgets.Button(description="Hit Rate & ID Logic", button_style='info')
    btn_up = widgets.Button(description="Start Upload", button_style='success', disabled=True)

    ui_mapping = widgets.VBox([
        status_output,
        widgets.HTML("<hr><h3>2. Mapping & Dynamic SQL Push</h3>"),
        df_select, schema_select, target_table_name, pk_col,
        widgets.HTML("<b>Reference Validation (Foreign Key Check):</b>"),
        rel_table, rel_col,
        widgets.HBox([btn_val, btn_up])
    ])
    display(ui_mapping)

    def validate(b):
        """ID-Enrichment und percentage-Check."""
        import __main__
        with output:
            clear_output()
            df_name = df_select.value
            df = available_dfs[df_name].copy()
            
            # 1. Extern Enrichment
            enrich_func = getattr(__main__, 'enrich_spatial_ids', None)
            if enrich_func and callable(enrich_func):
                try:
                    print("🔄 Executing 'enrich_spatial_ids'...")
                    df = enrich_func(df)
                    setattr(__main__, df_name, df)
                    print("✅ IDs enriched.")
                except Exception as e: print(f"⚠️ Enrichment Error: {e}")

            # 2. percentage check DB test
            if rel_table.value and rel_col.value:
                sch = schema_select.value
                try:
                    query = text(f'SELECT DISTINCT "{rel_col.value}" FROM "{sch}"."{rel_table.value}"')
                    with engine.connect() as conn:
                        db_ids = pd.read_sql(query, conn)[rel_col.value].astype(str).unique()
                    
                    # Fallback Check no PK
                    check_col = pk_col.value if pk_col.value in df.columns else df.columns[0]
                    source_series = df[check_col].dropna().astype(str).unique()
                    
                    matches = sum(pd.Series(source_series).isin(db_ids))
                    quota = (matches / len(source_series)) * 100 if len(source_series) > 0 else 0
                    print(f"📊 Validation ({check_col}): {quota:.2f}% Hit Rate ({matches}/{len(source_series)} IDs)")
                    btn_up.disabled = False
                except Exception as e: print(f"❌ Validation Error: {e}")
            else:
                print("ℹ️ No reference table. Upload unlocked.")
                btn_up.disabled = False
    def get_dynamic_sql_types(df):
        """
        Stochastischer Smart-Scanner (3-Stufen-Check):
        1. Respektiert Pandas-Dtypes (Vorgabe beim Sortieren)
        2. Prüft Schlüsselwörter im Spaltennamen
        3. Validiert den tatsächlichen Inhalt (Stichprobe), um Fallstricke zu vermeiden.
        """
        from sqlalchemy import BigInteger, Text, Float, Boolean, DateTime, Numeric, JSON
        from sqlalchemy.dialects.postgresql import UUID, INET, CIDR, MACADDR
        import pandas as pd
        
        try:
            from geoalchemy2 import Geometry
        except ImportError:
            Geometry = None
        
        dtype_map = {}
        
        for col in df.columns:
            col_lower = col.lower()
            pd_dtype = df[col].dtype
            
            # Inhalts-Check: Erste 20 Zeilen ohne NaNs prüfen
            sample_values = df[col].dropna().head(20)
            sample_str = " ".join(sample_values.astype(str)).lower()
            
            # --- 1. GEOMETRY (GIS) ---
            if any(key in col_lower for key in ['geometry', 'geom', 'point', 'polygon']) or str(pd_dtype) == 'geometry':
                # Verifikation: Sieht der Inhalt nach WKT (POINT, POLYGON) oder HEX aus?
                if any(k in sample_str for k in ['point', 'polygon', 'linestring']) or len(sample_str) > 20:
                    dtype_map[col] = Geometry(geometry_type='GEOMETRY', srid=4326) if Geometry else Text()
                else:
                    dtype_map[col] = Text()

            # --- 2. KOORDINATEN (LAT/LOG) ---
            # Erzwingt FLOAT, wenn der Inhalt numerisch konvertierbar ist
            elif any(key in col_lower for key in ['lat', 'lon', 'log', 'lng', 'coord', 'x', 'y']):
                try:
                    pd.to_numeric(df[col], errors='raise')
                    dtype_map[col] = Float() # SQL Double Precision
                except:
                    dtype_map[col] = Text() # Fallback bei Textfehlern in Koord-Spalten

            # --- 3. NETZWERK & IDENTIFIKATION (UUID, IP, MAC) ---
            elif 'uuid' in col_lower:
                # Check: Sieht es nach einer langen ID aus?
                if len(sample_str) > 30: dtype_map[col] = UUID(as_uuid=True)
                else: dtype_map[col] = Text()
            elif any(key in col_lower for key in ['ip_address', 'ipv4', 'ipv6', 'inet']):
                dtype_map[col] = INET()
            elif 'cidr' in col_lower:
                dtype_map[col] = CIDR()
            elif 'mac' in col_lower and 'address' in col_lower:
                dtype_map[col] = MACADDR()

            # --- 4. STRUKTURIERTE DATEN (JSON) ---
            elif any(key in col_lower for key in ['json', 'metadata', 'tags', 'attributes', 'settings']):
                # Verifikation: Enthält der Inhalt geschweifte oder eckige Klammern?
                if any(k in sample_str for k in ['{', '[']):
                    dtype_map[col] = JSON()
                else:
                    dtype_map[col] = Text()

            # --- 5. IDs & PRIMARY KEYS ---
            elif any(key in col_lower for key in ['id', 'pk', 'key']):
                # Wenn du es in Pandas als string definiert hast (z.B. neighborhood_id '0805'), bleibt es Text.
                if pd.api.types.is_integer_dtype(pd_dtype):
                    dtype_map[col] = BigInteger()
                else:
                    dtype_map[col] = Text()

            # --- 6. ERWEITERTE NUMERIK (FINANZEN) ---
            elif any(key in col_lower for key in ['price', 'cost', 'amount', 'fee', 'revenue', 'money']):
                try:
                    pd.to_numeric(df[col], errors='raise')
                    dtype_map[col] = Numeric(precision=18, scale=2)
                except:
                    dtype_map[col] = Text()

            # --- 7. ZEITSTEMPEL & DATUM ---
            elif any(key in col_lower for key in ['date', 'time', 'created', 'updated', 'at']) or pd.api.types.is_datetime64_any_dtype(pd_dtype):
                dtype_map[col] = DateTime()
            
            # --- 8. WAHRHEITSWERTE (BOOLEAN) ---
            elif any(key in col_lower for key in ['is_', 'has_', 'active', 'check']) or pd.api.types.is_bool_dtype(pd_dtype):
                # Stochastik-Check: Nur wenn max 2 unique Werte (+ NaN) existieren
                if df[col].dropna().nunique() <= 2:
                    dtype_map[col] = Boolean()
                else:
                    # Schützt Spalten wie 'accessibility' (yes, limited, no)
                    dtype_map[col] = Text()

            # --- 9. GLOBALER FALLBACK (Inhaltsbasierte Erkennung) ---
            else:
                if pd.api.types.is_float_dtype(pd_dtype):
                    dtype_map[col] = Float()
                elif pd.api.types.is_integer_dtype(pd_dtype):
                    dtype_map[col] = BigInteger()
                elif pd.api.types.is_bool_dtype(pd_dtype):
                    dtype_map[col] = Boolean()
                else:
                    # Standard für 'opening_hours', 'address', 'operator' etc.
                    dtype_map[col] = Text()
        return dtype_map
        
    def upload(b):
        """Führt den Upload durch mit vollautomatischer Typ-Erkennung (Smart-Mapping)."""
        import __main__
        with output:
            try:
                import warnings
                from sqlalchemy.exc import SAWarning
                # Wichtig: get_dynamic_sql_types muss im gleichen Scope oder global definiert sein
                warnings.filterwarnings('ignore', category=SAWarning)

                perms = get_detailed_permissions(engine, schema_select.value)
                df = getattr(__main__, df_select.value).copy()
                tbl = target_table_name.value.strip() or "upload_table"
                sch = schema_select.value
                pk = pk_col.value

                is_upload_only = (pk == "No Connection / Upload Only")

                # --- INTELLIGENTE TYP-ERKENNUNG (Verbindung zum Scanner) ---
                print("🧠 Analyzing columns for optimal SQL types (UUID, JSON, Geometry, etc.)...")
                dynamic_dtypes = get_dynamic_sql_types(df)

                # Spezielle Vorbereitung für Geometrie (WKT-Konvertierung für den Transfer)
                if 'geometry' in df.columns:
                    print("🌐 Spatial data detected: Preparing WKT for transfer...")
                    df['geometry'] = df['geometry'].apply(lambda x: x.wkt if hasattr(x, 'wkt') else x)

                if is_upload_only:
                    # USER MODUS (Append)
                    print(f"🛡️ Safety Mode: Appending data to {sch}.{tbl}...")
                    df.to_sql(name=tbl, con=engine, schema=sch, if_exists='append', 
                              index=False, method='multi', dtype=dynamic_dtypes)
                else:
                    # ADMIN MODUS (Recreate)
                    print(f"🛠️ Admin Mode: Preparing table {sch}.{tbl}...")
                    with engine.connect() as conn:
                        # Drop nur wenn Admin-Rechte vorhanden
                        if perms["can_create"]:
                            conn.execute(text(f'DROP TABLE IF EXISTS "{sch}"."{tbl}";'))
                            conn.commit()
                        
                        # Upload mit dem dynamisch generierten dtype-Dictionary
                        df.to_sql(name=tbl, con=engine, schema=sch, if_exists='append', 
                                  index=False, method='multi', dtype=dynamic_dtypes)
                        
                        if pk and pk != "No Connection / Upload Only":
                            print(f"🔑 Setting Primary Key: {pk}...")
                            conn.execute(text(f'ALTER TABLE "{sch}"."{tbl}" ADD PRIMARY KEY ("{pk}");'))
                            conn.commit()
                
                print(f"🚀 SUCCESS: {len(df)} rows transferred with smart formatting.")
            except Exception as e: 
                print(f"❌ Upload error: {e}")
                print("💡 Hint: If you lack Admin rights, select 'No Connection / Upload Only'.")

    btn_val.on_click(validate)
    btn_up.on_click(upload)

# --- START ---
sql_upload_pipeline()