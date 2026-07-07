# src/ini.py
import sys
import os
import glob
import importlib
import pandas as pd

# 1. UNIVERSAL PATH DETECTION VIA PROJECT CONFIG
try:
    # Ermittle die relative Position des config-Ordners ausgehend von der Datei
    current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()

    config_path = os.path.abspath(os.path.join(current_dir, "..", "config", "project_paths.json"))
    if not os.path.exists(config_path):
        # Fallback: Sucht im aktuellen Verzeichnis, falls direkt aus src/ aufgerufen
        config_path = os.path.abspath(os.path.join(current_dir, "config", "project_paths.json"))

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    root_path = config_data["root"]
    src_path = config_data["src"]
except Exception as e:
    # Extrem sicherer Fallback, falls die JSON-Datei blockiert oder nicht lesbar ist
    src_path = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    if "src" not in src_path.split(os.sep)[-1]:
        src_path = os.path.join(src_path, "src")
    root_path = os.path.abspath(os.path.join(src_path, ".."))

# Unlock path to src for Python
if src_path not in sys.path:
    sys.path.append(src_path)

# 2. AUTOMATIC MODULE IMPORT (Recursive Subfolder Scan)
imported_modules = []
ignore_folders = {os.path.basename(src_path), "__pycache__", "venv", ".git"}

for root, dirs, files in os.walk(src_path):
    # Verhindert das Durchsuchen von Systemordnern
    dirs[:] = [d for d in dirs if d not in ignore_folders]
    
    # CHIRURGISCHER FIX: Füge jeden Unterordner (z.B. analysis_data_load) zu sys.path hinzu
    if root not in sys.path:
        sys.path.append(root)
        
    for file in files:
        if file.endswith(".py") and not file.startswith("__") and file != "ini.py":
            module_name = file[:-3]
            
            try:
                mod = importlib.import_module(module_name)
                # Transfers all functions/classes into the global scope of the notebook
                globals().update({k: v for k, v in vars(mod).items() if not k.startswith('_')})
                imported_modules.append(module_name)
            except Exception as e:
                print(f"⚠️ Error loading {module_name} from {os.path.basename(root)}: {e}")

# 3. UNIVERSAL HELPER: LOAD DATA
def load_data(relative_path_from_root=None):
    """
    Loads CSV files based on the main folder with automatic separator detection
    to prevent single-column compression errors.
    Example: load_data("data/berlin_population.csv")
    """
    if relative_path_from_root is None:
        print("⚠️ Fehler: Du musst einen relativen Pfad angeben! Beispiel: load_data('data/berlin_population.csv')")
        return None

    full_path = os.path.join(root_path, relative_path_from_root)
    if not os.path.exists(full_path):
        print(f"❌ File not found at: {full_path}")
        return None

    detected_sep = ';'  # Standard-Fallback für Berlin-Daten
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
            # Zähle Vorkommen der typischen Trennzeichen in der Header-Zeile
            comma_count = first_line.count(',')
            semicolon_count = first_line.count(';')
            
            if comma_count > semicolon_count:
                detected_sep = ','
                print(f"⚠️ HINWEIS: Automatische Erkennung hat Komma-Separator (sep=',') für '{relative_path_from_root}' detektiert und angepasst.")
    except Exception as e:
        print(f"⚠️ Warnung bei Separator-Analyse: {e}. Verwende Standard ';'.")

    # Laden mit dem dynamisch verifizierten Separator
    return pd.read_csv(full_path, sep=detected_sep)

# 4. UNIVERSAL HELPER: SAVE DATA (Logic integration)
def save_in_data_folder_csv(df, file_name, sub_folder=""):
    """
    Creates the target directory inside /data if it doesn't exist 
    and saves the DataFrame with encoding protection for Berlin umlauts.
    """
    target_dir = os.path.join(root_path, "data", sub_folder)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        print(f"✅ Directory '{target_dir}' has been created.")
    
    output_path = os.path.join(target_dir, file_name)
    
    # Speichern mit utf-8-sig für korrekte Umlaute in Excel/Notebooks
    df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"✅ File successfully saved at: {output_path}")
    return output_path

print("✅ Universal workspace ready!")
print('save_in_data_folder_csv(df, file_name, sub_folder="")')
print('load_data(relative_path_from_root="")')
print(f"📍 Main folder: {root_path}")
print(f"📦 Modules loaded: {', '.join(imported_modules)}")