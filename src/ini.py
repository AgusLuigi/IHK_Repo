# src/ini.py
import sys
import os
import glob
import importlib
import pandas as pd  # Notwendig für load_data und den Export

# 1. UNIVERSAL PATH DETECTION (Surgically precise)
src_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.abspath(os.path.join(src_path, '..'))

# Unlock path to src for Python
if src_path not in sys.path:
    sys.path.append(src_path)

# 2. AUTOMATIC MODULE IMPORT
imported_modules = []
for f in glob.glob(os.path.join(src_path, "*.py")):
    module_name = os.path.basename(f)[:-3]
    if module_name.startswith('__') or module_name == 'ini':
        continue
    
    try:
        mod = importlib.import_module(module_name)
        # Transfers all functions/classes into the global scope of the notebook
        globals().update({k: v for k, v in vars(mod).items() if not k.startswith('_')})
        imported_modules.append(module_name)
    except Exception as e:
        print(f"⚠️ Error loading {module_name}: {e}")

# 3. UNIVERSAL HELPER: LOAD DATA
def load_data(relative_path_from_root):
    """
    Loads CSV files based on the main folder.
    Example: load_data("data/berlin_population.csv")
    """
    full_path = os.path.join(root_path, relative_path_from_root)
    if os.path.exists(full_path):
        return pd.read_csv(full_path, sep=';') # Standard-Separator für Berlin-Daten
    else:
        print(f"❌ File not found at: {full_path}")
        return None

# 4. UNIVERSAL HELPER: SAVE DATA (Logic integration)
def save_in_data_folder_csv(df, file_name, sub_folder=""):
    """
    Creates the target directory inside /data if it doesn't exist 
    and saves the DataFrame with encoding protection for Berlin umlauts.
    """
    target_dir = os.path.join(root_path, "data", sub_folder)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"✅ Directory '{target_dir}' has been created.")
    
    output_path = os.path.join(target_dir, file_name)
    
    # Speichern mit utf-8-sig für korrekte Umlaute in Excel/Notebooks
    df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"✅ File successfully saved at: {output_path}")
    return output_path

print("✅ Universal workspace ready!")
print(f"📍 Main folder: {root_path}")
print(f"📦 Modules loaded: {', '.join(imported_modules)}")