# SQL Abfrage und Speicherung als permanente SQLite-Datei mit benutzerdefinierter Filterung

# =============================================================================
# HILFSFUNKTION: Fenster auf Bildschirm zentrieren
# =============================================================================
def _center(win, w, h):
    """Zentriert ein Tk-Fenster exakt auf dem Bildschirm."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x  = (sw - w) // 2
    y  = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# =============================================================================
# HILFSFUNKTION: Fenster sauber zerstoeren (Jupyter-sicher)
# =============================================================================
def _destroy_root(root):
    try: root.quit()
    except Exception: pass
    try: root.update()
    except Exception: pass
    try: root.destroy()
    except Exception: pass


# =============================================================================
# FARBSCHEMA: Dark / Light Mode
# =============================================================================
def _get_system_colors(root=None):
    """
    Erkennt den Dark/Light Mode unter Windows und macOS nativ.
    Nutzt Helligkeits-Fallback für andere Systeme.
    """
    import platform
    import subprocess
    is_dark = False
    system = platform.system()

    try:
        if system == "Windows":
            import winreg
            # Abfrage der Windows-Registry für den App-Modus
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            is_dark = (value == 0)
            
        elif system == "Darwin":  # macOS
            # Abfrage der macOS 'AppleInterfaceStyle' Einstellung
            try:
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                is_dark = "Dark" in result.stdout
            except Exception:
                is_dark = False

        else:
            # Fallback für Linux/Andere via tkinter Helligkeitsanalyse
            if root:
                rgb = root.winfo_rgb("SystemButtonFace")
                # 16-bit zu 8-bit Konvertierung
                r, g, b = rgb[0] // 256, rgb[1] // 256, rgb[2] // 256
                # Standard-Luminanz-Formel für menschliche Wahrnehmung
                brightness = (0.299 * r + 0.587 * g + 0.114 * b)
                is_dark = brightness < 128
    except Exception:
        is_dark = False
        
        return {
            "BG":        "#121212",  # Deep Charcoal (Hintergrund bleibt ruhig)
            "CARD":      "#888888",  # Raised Gray (Fläche hebt sich dezent ab)
            "ACCENT":    "#333333",  # Platinum Silver (Statt Blau: Klarer Akzent)
            "TEXT":      "#333333",  # Off-White (Maximale Lesbarkeit, blendet nicht)
            "MUTED":     "#888888",  # Medium Gray (Für weniger wichtige Infos)
            "BORDER":    "#333333",  # Dark Slate (Feine Abgrenzung)
            "BTN_FG":    "#121212",  # Black (Kontrast auf hellem Button)
            "BTN_HOVER": "#888888",  # Pure White (Hervorhebung bei Interaktion)
            "SQL_BG":    "#0a0a0a",  # Pitch Black (Kontrast für Code/SQL)
        }
    else:
        # Optimierter Light Mode: Klar und strukturiert
        return {
            "BG":        "#fcfcfc",  # Soft White (Verhindert hartes Blenden)
            "CARD":      "#ffffff",  # Pure White (Karten heben sich ab)
            "ACCENT":    "#2d2d2d",  # Graphite (Starker, neutraler Akzent)
            "TEXT":      "#121212",  # Deep Black (Bester Lesekontrast)
            "MUTED":     "#666666",  # Dim Gray
            "BORDER":    "#e0e0e0",  # Light Silver
            "BTN_FG":    "#f8f8f8",  # White (Text auf dunklem Button)
            "BTN_HOVER": "#000000",  # Absolute Black
            "SQL_BG":    "#f5f5f5",  # Light Fog (Dezenter Block für Code)
        }


# =============================================================================
# EINZEL-FENSTER-WIZARD (alle 3 Schritte in einem Fenster)
# =============================================================================
def _run_wizard(tk):
    from tkinter import scrolledtext, filedialog

    W, H  = 780, 580
    STEPS = ["1  Verbindung", "2  SQL-Filter", "3  Speicherort"]

    result  = {"db_url": None, "filter_sql": None, "sqlite_path": None}
    aborted = {"v": False}
    step    = {"i": 0}

    # ------------------------------------------------------------------
    # ROOT
    # ------------------------------------------------------------------
    root = tk.Tk()
    root.title("DB Replikation – Einrichtung")
    root.resizable(False, False)
    _center(root, W, H)
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()

    theme     = _get_system_colors(root)
    BG        = theme["BG"]
    CARD      = theme["CARD"]
    ACCENT    = theme["ACCENT"]
    TEXT      = theme["TEXT"]
    MUTED     = theme["MUTED"]
    BORDER    = theme["BORDER"]
    BTN_FG    = theme["BTN_FG"]
    BTN_HOVER = theme["BTN_HOVER"]
    SQL_BG    = theme["SQL_BG"]

    root.configure(bg=BG)

    # ------------------------------------------------------------------
    # GLOBALE TK-DEFAULTS:
    # Jedes Widget erbt automatisch die Theme-Farben – auch Widgets ohne
    # explizites bg=/fg=, z.B. interne Scrollbar-Container, Dialoge usw.
    # Kein Grau-Weiss-Fleck mehr durch vergessene Farbzuweisung.
    # ------------------------------------------------------------------
    root.option_add("*Background",               BG)
    root.option_add("*Foreground",               TEXT)
    root.option_add("*activeBackground",         BTN_HOVER)
    root.option_add("*activeforeground",         BTN_FG)
    root.option_add("*disabledForeground",       MUTED)
    root.option_add("*highlightBackground",      BORDER)
    root.option_add("*selectBackground",         ACCENT)
    root.option_add("*selectForeground",         BTN_FG)
    # Entry
    root.option_add("*Entry.Background",         CARD)
    root.option_add("*Entry.Foreground",         TEXT)
    root.option_add("*Entry.insertBackground",   TEXT)
    root.option_add("*Entry.disabledBackground", CARD)
    root.option_add("*Entry.disabledForeground", MUTED)
    root.option_add("*Entry.readonlyBackground", CARD)
    # Text / ScrolledText
    root.option_add("*Text.Background",          SQL_BG)
    root.option_add("*Text.Foreground",          TEXT)
    root.option_add("*Text.insertBackground",    TEXT)
    # Button
    root.option_add("*Button.Background",        BORDER)
    root.option_add("*Button.Foreground",        TEXT)
    root.option_add("*Button.activeBackground",  BTN_HOVER)
    root.option_add("*Button.activeforeground",  BTN_FG)
    root.option_add("*Button.disabledForeground",MUTED)
    # Label
    root.option_add("*Label.Background",         BG)
    root.option_add("*Label.Foreground",         TEXT)
    # Frame
    root.option_add("*Frame.Background",         BG)
    # Scrollbar
    root.option_add("*Scrollbar.Background",     BORDER)
    root.option_add("*Scrollbar.troughColor",    CARD)
    root.option_add("*Scrollbar.activeBackground", MUTED)

    # ------------------------------------------------------------------
    # ABBRUCH-FUNKTION
    # ------------------------------------------------------------------
    def _abort():
        """Bricht den Wizard ab: Mainloop stoppen, Destroy erfolgt nach mainloop()."""
        aborted["v"] = True
        try:
            root.withdraw()
            root.quit()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", _abort)

    # ------------------------------------------------------------------
    # HEADER: Schrittanzeige
    # ------------------------------------------------------------------
    header = tk.Frame(root, bg=ACCENT, height=54)
    header.pack(fill="x")
    header.pack_propagate(False)

    step_labels = []
    for i, name in enumerate(STEPS):
        frm = tk.Frame(header, bg=ACCENT)
        frm.pack(side="left", padx=24, pady=10)
        dot = tk.Label(frm, text=str(i + 1), bg=ACCENT, fg="#f8f8f8",
                       font=("Segoe UI", 10, "bold"), width=2, relief="flat")
        dot.pack(side="left")
        lbl = tk.Label(frm, text=name, bg=ACCENT, fg="#aac8e8",
                       font=("Segoe UI", 10))
        lbl.pack(side="left", padx=(4, 0))
        step_labels.append((dot, lbl, frm))
        if i < len(STEPS) - 1:
            tk.Label(header, text="›", bg=ACCENT, fg="#aac8e8",
                     font=("Segoe UI", 12)).pack(side="left")

    def _update_header():
        for i, (dot, lbl, frm) in enumerate(step_labels):
            if i == step["i"]:
                dot.configure(bg="#ffffff", fg=ACCENT)
                lbl.configure(fg="#f8f8f8", font=("Segoe UI", 10, "bold"))
            elif i < step["i"]:
                dot.configure(bg=ACCENT, fg="#7fb8e0")
                lbl.configure(fg="#7fb8e0", font=("Segoe UI", 10))
            else:
                dot.configure(bg=ACCENT, fg="#aac8e8")
                lbl.configure(fg="#aac8e8", font=("Segoe UI", 10))

    # ------------------------------------------------------------------
    # BODY
    # ------------------------------------------------------------------
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=28, pady=(20, 0))

    var_url  = tk.StringVar(value="postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require")
    var_path = tk.StringVar(value="")

    panels = {}

    # ------------------------------------------------------------------
    # PANEL 0 – Verbindungs-URL
    # ------------------------------------------------------------------
    def _make_step0():
        f = tk.Frame(body, bg=BG)

        tk.Label(f, text="Datenbank-Verbindungs-URL",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(f, text="Vollstaendigen Connection-String eingeben.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))

        tk.Label(f, text="db_url", bg=BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ent = tk.Entry(f, textvariable=var_url, font=("Courier New", 10),
                       bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                       highlightthickness=1, highlightbackground=BORDER,
                       highlightcolor=ACCENT)
        ent.pack(fill="x", ipady=7, pady=(3, 16))

        tk.Label(f, text="Beispiele", bg=BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        examples = tk.Frame(f, bg=CARD, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER)
        examples.pack(fill="x", pady=(3, 0))

        ex_data = [
            ("PostgreSQL", "postgresql://USER:PW@HOST:5432/DB?sslmode=require"),
            ("MySQL",      "mysql+pymysql://USER:PW@HOST:3306/DB"),
            ("MSSQL",      "mssql+pyodbc://USER:PW@HOST/DB?driver=ODBC+Driver+17+for+SQL+Server"),
        ]
        for label, val in ex_data:
            row = tk.Frame(examples, bg=CARD)
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text=f"{label}:", bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
            lnk = tk.Label(row, text=val, bg=CARD, fg=ACCENT,
                           font=("Courier New", 9), cursor="hand2", anchor="w")
            lnk.pack(side="left")
            lnk.bind("<Button-1>", lambda e, v=val: var_url.set(v))

        return f

    # ------------------------------------------------------------------
    # PANEL 1 – SQL-Filter
    # ------------------------------------------------------------------
    def _make_step1():
        f = tk.Frame(body, bg=BG)

        tk.Label(f, text="SQL-Filter-Abfrage  (optional)",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(f,
                 text="Leer lassen → alle Tabellen komplett laden.  "
                      "SQL eingeben → gefiltert nach user_id / trip_id.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10),
                 wraplength=720, justify="left").pack(anchor="w", pady=(2, 10))

        txt_frame = tk.Frame(f, bg=CARD, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER)
        txt_frame.pack(fill="both", expand=True)

        sql_txt = scrolledtext.ScrolledText(
            txt_frame, wrap="none",
            font=("Courier New", 10),
            undo=True,
            bg=SQL_BG,          # Theme-Farbe statt hartcodiert "#121212"/"#ffffff"
            fg=TEXT,            # Theme-Farbe statt hartcodiert "#d4d4d4"/"#1a1a1a"
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground=BTN_FG,
            relief="flat", borderwidth=0
        )
        sql_txt.pack(fill="both", expand=True, padx=2, pady=2)

        default = (
            "WITH sessions_2023 AS (\n"
            "    SELECT user_id, trip_id, session_start\n"
            "    FROM sessions\n"
            "    WHERE session_start > '2023-01-04'\n"
            "),\n"
            "filtered_users AS (\n"
            "    SELECT user_id\n"
            "    FROM sessions_2023\n"
            "    GROUP BY user_id\n"
            "    HAVING COUNT(session_id) > 7\n"
            ")\n"
            "SELECT DISTINCT s.user_id, s.trip_id\n"
            "FROM sessions_2023 s\n"
            "JOIN filtered_users fu ON s.user_id = fu.user_id;"
        )
        sql_txt.insert("1.0", default)

        tk.Label(f, text="Ctrl+Enter = Weiter zum naechsten Schritt",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="e", pady=(4, 0))

        f._sql_txt = sql_txt
        return f

    # ------------------------------------------------------------------
    # PANEL 2 – Speicherort
    # ------------------------------------------------------------------
    def _make_step2():
        f = tk.Frame(body, bg=BG)

        tk.Label(f, text="Speicherort der SQLite-Datei",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(f, text="Wo soll die replizierte Datenbank gespeichert werden?",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))

        tk.Label(f, text="Dateipfad", bg=BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        row = tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=(3, 4))

        ent_path = tk.Entry(row, textvariable=var_path,
                            font=("Courier New", 10),
                            bg=CARD, fg=TEXT,
                            disabledbackground=CARD, disabledforeground=MUTED,
                            readonlybackground=CARD,
                            relief="flat",
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=ACCENT, state="readonly")
        ent_path.pack(side="left", fill="x", expand=True, ipady=7)

        def _pick():
            p = filedialog.asksaveasfilename(
                parent=root,
                title="Speicherort waehlen",
                defaultextension=".sqlite",
                filetypes=[("SQLite-Datenbanken", "*.sqlite"), ("Alle Dateien", "*.*")],
                initialfile="replizierte_daten"
            )
            if p:
                var_path.set(p)
                _update_finish_btn()

        tk.Button(row, text="Ordner wählen …", command=_pick,
                  font=("Segoe UI", 10), relief="flat",
                  bg=BORDER, fg=TEXT,              # TEXT statt hartcodiert "#333333"
                  activebackground=BTN_HOVER,      # BTN_HOVER statt "#cccccc"
                  activeforeground=BTN_FG,
                  cursor="hand2", padx=10).pack(side="left", padx=(8, 0), ipady=6)

        hint_frame = tk.Frame(f, bg=CARD, relief="flat",
                              highlightthickness=1, highlightbackground=BORDER)
        hint_frame.pack(fill="x", pady=(12, 0))

        hints = [
            ("Windows", r"C:\Users\Name\Dokumente\export.sqlite"),
            ("macOS",   "/Users/name/Dokumente/export.sqlite"),
            ("Linux",   "/home/name/db/export.sqlite"),
        ]
        for os_name, path_ex in hints:
            hr = tk.Frame(hint_frame, bg=CARD)
            hr.pack(fill="x", padx=10, pady=3)
            tk.Label(hr, text=f"{os_name}:", bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
            tk.Label(hr, text=path_ex, bg=CARD, fg=TEXT,
                     font=("Courier New", 9), anchor="w").pack(side="left")

        return f

    panels[0] = _make_step0()
    panels[1] = _make_step1()
    panels[2] = _make_step2()

    # ------------------------------------------------------------------
    # FOOTER: Navigations-Buttons
    # ------------------------------------------------------------------
    footer = tk.Frame(root, bg=BG, height=60)
    footer.pack(fill="x", padx=28, pady=14)
    footer.pack_propagate(False)

    btn_back = tk.Button(
        footer, text="← Zurück", width=12,
        font=("Segoe UI", 10), relief="flat",
        bg=BORDER, fg=TEXT,              # TEXT statt hartcodiert "#333333"
        activebackground=BTN_HOVER,
        activeforeground=BTN_FG,
        cursor="hand2"
    )
    btn_back.pack(side="left")

    btn_next = tk.Button(
        footer, text="Weiter →", width=14,
        font=("Segoe UI", 10, "bold"), relief="flat",
        bg=BORDER, fg=TEXT, cursor="hand2",
        activebackground=BTN_HOVER,
        activeforeground=BTN_FG
    )
    btn_next.pack(side="right")

    btn_cancel = tk.Button(
        footer, text="Abbrechen", width=12,
        font=("Segoe UI", 10), relief="flat",
        bg=BG, fg=MUTED, cursor="hand2",
        activebackground=BORDER,
        activeforeground=TEXT,
        command=_abort
    )
    btn_cancel.pack(side="right", padx=(0, 10))

    # ------------------------------------------------------------------
    # FINISH-FUNKTION
    # ------------------------------------------------------------------
    def _finish():
        """Validiert, sichert Daten und schliesst den Wizard."""
        try:
            sql_raw = panels[1]._sql_txt.get("1.0", "end-1c").strip()
            db_url  = var_url.get().strip()
            path    = var_path.get().strip()

            if not path:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Hinweis",
                    "Bitte waehlen Sie einen Speicherort aus, bevor Sie starten."
                )
                return

            result["db_url"]      = db_url
            result["filter_sql"]  = sql_raw
            result["sqlite_path"] = path

            root.withdraw()
            root.quit()

        except Exception as e:
            print(f"[Fehler beim Beenden] {e}")
            try:
                root.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # FINISH-BUTTON: freischalten sobald Pfad vorhanden
    # ------------------------------------------------------------------
    def _update_finish_btn():
        if var_path.get():
            btn_next.configure(state="normal")
        else:
            btn_next.configure(state="disabled")

    # ------------------------------------------------------------------
    # SCHRITT-NAVIGATION
    # ------------------------------------------------------------------
    def _show_step(i):
        for p in panels.values():
            p.pack_forget()
        panels[i].pack(fill="both", expand=True)
        step["i"] = i
        _update_header()

        btn_back.configure(
            state="normal" if i > 0 else "disabled",
            command=_back,
            bg=BORDER if i > 0 else BG
        )

        if i < 2:
            btn_next.configure(
                text="Weiter →",
                command=_next,
                bg=ACCENT,
                fg=TEXT,
                activebackground=BTN_HOVER,
                activeforeground="#888888",
                state="normal"
            )
        else:
            btn_next.configure(
                text="▶  Starten",
                command=_finish,
                bg="#3B6D11",       # Signal-Gruen – bewusste Ausnahme
                fg="#f8f8f8",
                activebackground="#27500A",
                activeforeground="#888888"
            )
            _update_finish_btn()

    def _next():
        if step["i"] < 2:
            _show_step(step["i"] + 1)

    def _back():
        if step["i"] > 0:
            _show_step(step["i"] - 1)

    btn_back.configure(command=_back)
    panels[1]._sql_txt.bind("<Control-Return>", lambda e: _next())

    # ------------------------------------------------------------------
    # START
    # ------------------------------------------------------------------
    _show_step(0)
    root.mainloop()
    _destroy_root(root)   # zentrales Cleanup fuer alle Schliess-Pfade

    if aborted["v"] or not result["sqlite_path"]:
        return None
    return result


# =============================================================================
# HAUPTFUNKTION
# =============================================================================
def sql_download_offline():
    """
    Startet den Wizard und repliziert die Datenbank in eine lokale SQLite-Datei.
    """
    import tkinter as tk
    import pandas as pd
    from sqlalchemy import create_engine, inspect, text

    cfg = _run_wizard(tk)

    if cfg is None:
        print("[Abbruch] Wizard abgebrochen.")
        return

    db_url           = cfg["db_url"]
    filter_sql_query = cfg["filter_sql"]
    sqlite_file_path = cfg["sqlite_path"]
    use_filter       = bool(filter_sql_query)

    print(f"\n[Modus] {'Gefilterter Download' if use_filter else 'Kompletter Download (kein Filter)'}")

    # ------------------------------------------------------------------
    # SCHRITT 1: Verbindung herstellen
    # ------------------------------------------------------------------
    print(f"\n[1/4] Verbindung herstellen...")
    print(f"      URL : {db_url[:60]}{'...' if len(db_url) > 60 else ''}")

    try:
        engine_ext    = create_engine(db_url)
        engine_sqlite = create_engine(f"sqlite:///{sqlite_file_path}")
        inspector     = inspect(engine_ext)

        #all_tables = inspector.get_table_names()
        available_schemas = inspector.get_schema_names()
        target_schema = "nyc_schools" if "nyc_schools" in available_schemas else "public"
        
        all_tables = inspector.get_table_names(schema=target_schema)
        if not all_tables:
            print("[Fehler] Keine Tabellen gefunden.")
            return

        print(f"      {len(all_tables)} Tabelle(n): {all_tables}")

    except Exception as e:
        print(f"[Fehler] Verbindung fehlgeschlagen: {e}")
        e_str = str(e).lower()
        if "authentication" in e_str or "password" in e_str:
            print("         Tipp: Benutzername / Passwort pruefen.")
        elif "connection refused" in e_str:
            print("         Tipp: Host und Port pruefen.")
        return

    # ------------------------------------------------------------------
    # SCHRITT 2: Filter-IDs extrahieren
    # ------------------------------------------------------------------
    filter_map = {}

    if use_filter:
        print(f"\n[2/4] Filter-IDs extrahieren...")
        try:
            with engine_ext.connect() as conn:
                relevant_ids_df = pd.read_sql(
                    sql=text(filter_sql_query),
                    con=conn
                )
        except Exception as e:
            print(f"[Fehler] Filter-Abfrage fehlgeschlagen: {e}")
            return

        if relevant_ids_df.empty:
            print("[Fehler] Filter lieferte keine Datensaetze. Abbruch.")
            return

        user_id_list = ""
        trip_id_list = ""

        if "user_id" in relevant_ids_df.columns:
            uid_values   = relevant_ids_df["user_id"].dropna().unique().tolist()
            user_id_list = ", ".join(f"'{v}'" for v in uid_values)
            print(f"      user_id : {len(uid_values):,} eindeutige Werte")

        if "trip_id" in relevant_ids_df.columns:
            tid_values   = relevant_ids_df["trip_id"].dropna().unique().tolist()
            trip_id_list = ", ".join(f"'{v}'" for v in tid_values)
            print(f"      trip_id : {len(tid_values):,} eindeutige Werte")

        if not user_id_list and not trip_id_list:
            print("[Warnung] Weder 'user_id' noch 'trip_id' gefunden – lade alles ungefiltert.")
        else:
            if user_id_list:
                filter_map["sessions"] = f"user_id IN ({user_id_list})"
                filter_map["users"]    = f"user_id IN ({user_id_list})"
            if trip_id_list:
                filter_map["flights"]  = f"trip_id IN ({trip_id_list})"
                filter_map["hotels"]   = f"trip_id IN ({trip_id_list})"
    else:
        print(f"\n[2/4] Kein Filter – uebersprungen.")

    # ------------------------------------------------------------------
    # SCHRITT 3: Tabellen replizieren
    # ------------------------------------------------------------------
    print(f"\n[3/4] Tabellen laden und speichern...")

    replicated_count = 0
    total_rows       = 0
    current_table    = ""

    try:
        with engine_ext.connect() as conn:
            for table_name in all_tables:
                current_table = table_name
                where_clause  = ""
                label         = "(komplett)"

                if table_name in filter_map:
                    where_clause = f" WHERE {filter_map[table_name]}"
                    label        = "(gefiltert)"

                print(f"      [{replicated_count + 1}/{len(all_tables)}] '{table_name}' {label}...")

                safe_table_name = f'"{table_name}"'
                query = text(f"SELECT * FROM {target_schema}.{safe_table_name}{where_clause}")
                df = pd.read_sql(sql=query, con=conn)

                df.to_sql(
                    name=table_name,
                    con=engine_sqlite,
                    if_exists="replace",
                    index=False
                )

                replicated_count += 1
                total_rows       += len(df)
                print(f"             {len(df):,} Zeilen gespeichert.")

    except Exception as e:
        print(f"\n[Fehler] Kritischer Abbruch bei Tabelle '{current_table}':")
        print(f"         {e}")
        return

    finally:
        try:
            engine_ext.dispose()
            engine_sqlite.dispose()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # SCHRITT 4: Abschluss
    # ------------------------------------------------------------------
    print(f"\n[4/4] Fertig.")
    print(f"      Tabellen : {replicated_count}")
    print(f"      Zeilen   : {total_rows:,}")
    print(f"      Datei    : {sqlite_file_path}")

# Online-Verbindung nutzen.            !!!! Aktuell die Quelle amnuell verbinden sihe weitere schritte !!!!
# --------------------------------------------
#überprüfe quellen an andere schupladen setze die passende schuplade in

# Ändere diese Zeile in deinem Download-Skript:
# Vorher: all_tables = inspector.get_table_names()
# Nachher (Chirurgisch):
#all_tables = inspector.get_table_names(schema="nyc_schools")
# --------------------------------------------
#from sqlalchemy import create_engine, inspect

#online_url = "postgresql://neondb_owner:a9Am7Yy5r9_T7h4OF2GN@ep-falling-glitter-a5m0j5gk-pooler.us-east-2.aws.neon.tech:5432/neondb?sslmode=require" # Dein voller Link
#engine_online = create_engine(online_url)
#inspector = inspect(engine_online)

# Zeigt dir alle Schemas (Schubladen) an
#print(inspector.get_schema_names())


# !!!Project hinzu fügen ein Drup down beim SQL befehlszeile welche Quelle gezogen werden soll!!! 