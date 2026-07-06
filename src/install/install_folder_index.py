import os
import json
import sys
import logging

def get_project_root() -> str:
    """
    Ermittelt das Stammverzeichnis, indem gezielt nach dem Ordner 'Offline_KI'
    gesucht wird. Verhindert das Ausbrechen aus dem Projektverzeichnis.
    Sichert auch den Betrieb in interaktiven Umgebungen (Notebooks) ab.
    """
    if "__file__" in globals() or "____file____" in locals():
        current_path = os.path.abspath(os.path.dirname(__file__))
    else:
        current_path = os.path.abspath(os.getcwd())
    
    path_parts = current_path.split(os.sep)

    Project_folder = "IHK_REPO"
    
    # CHIRURGISCHER FIX: Case-insensitive Suche in den Pfadteilen
    path_parts_lower = [part.lower() for part in path_parts]
    target_lower = Project_folder.lower()

    if target_lower in path_parts_lower:
        ki_index = path_parts_lower.index(target_lower)
        if os.name == 'nt':  # Windows
            root_path = path_parts[0] + os.sep + os.path.join(*path_parts[1:ki_index + 1])
        else:  # Unix/Linux/macOS
            root_path = os.sep + os.path.join(*path_parts[:ki_index + 1])
        return os.path.abspath(root_path)

    while current_path != os.path.dirname(current_path):
        if os.path.basename(current_path).lower() == target_lower:
            return current_path
        current_path = os.path.dirname(current_path)
        
    return os.path.abspath(os.getcwd())

# ==============================================================================
# 1. FIXE GLOBALE CORE-STRUKTUR (Geschützte Basis-Begriffe)
# ==============================================================================
PROJECT_ROOT = get_project_root()

# Diese Core-Begriffe sind fest definiert und vor Überschreibung absolut geschützt
FOLDER_STRUCTURE = {
    "root": PROJECT_ROOT,
    "config": os.path.join(PROJECT_ROOT, "config"),
    "data": os.path.join(PROJECT_ROOT, "data"),
    "knowledge": os.path.join(PROJECT_ROOT, "knowledge"),
    "logs": os.path.join(PROJECT_ROOT, "logs"),
    "notebook": os.path.join(PROJECT_ROOT, "notebook"),
    #"privacy": os.path.join(PROJECT_ROOT, "privacy"),
    "src": os.path.join(PROJECT_ROOT, "src"),
    "temp": os.path.join(PROJECT_ROOT, "temp"),
    #"docker": os.path.join(PROJECT_ROOT, "docker")
}

# ==============================================================================
# 2. STOCHASTISCHER DETEKTOR MIT DUPLIKAT-SCHUTZ
# ==============================================================================
def stochastischer_system_scan(root_path: str, structure_dict: dict):
    """
    Durchsucht das gesamte Projektverzeichnis stochastisch und tiefenunabhängig.
    Schützt bereits vorhandene Begriffe oder identische Pfade vor dem Überschreiben.
    """
    # Systemordner, die ignoriert werden sollen, um den Index sauber zu halten
    ignore_set = {".git", ".ipynb_checkpoints", "__pycache__", "venv", ".DS_Store"}
    
    for root, dirs, files in os.walk(root_path):
        # Ignorierte Ordner direkt aus dem Scan ausschließen
        dirs[:] = [d for d in dirs if d not in ignore_set]
        
        for dir_name in dirs:
            full_path = os.path.abspath(os.path.join(root, dir_name))
            
            # IDENTITY-CHECK: Existiert dieser Begriff bereits global im RAM?
            if dir_name in structure_dict:
                # Fall A: Pfad ist absolut identisch -> Überspringen (Schutz aktiv)
                if structure_dict[dir_name] == full_path:
                    continue
                else:
                    # Fall B: Der Name existiert, zeigt aber woanders hin (Kollisionsschutz)
                    parent_name = os.path.basename(root)
                    kuerzel = f"{parent_name}_{dir_name}"
                    
                    # Nur hinzufügen, wenn dieses modifizierte Kürzel nicht auch schon belegt ist
                    if kuerzel not in structure_dict:
                        structure_dict[kuerzel] = full_path
            else:
                # Begriff ist komplett neu -> Stochastisch im Index aufnehmen
                structure_dict[dir_name] = full_path

# Starte den System-Scan (Ergänzt nur noch neue, unentdeckte Ordner)
stochastischer_system_scan(PROJECT_ROOT, FOLDER_STRUCTURE)

# Kritische Infrastruktur-Verzeichnisse für Konfigurationen vorab erzwingen
os.makedirs(FOLDER_STRUCTURE["logs"], exist_ok=True)
os.makedirs(FOLDER_STRUCTURE["config"], exist_ok=True)

# ==============================================================================
# 3. CENTRAL LOGGING SETUP (Notebook-Sicher gegen Zeilen-Duplikate)
# ==============================================================================
logger = logging.getLogger("ProjectInitializer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

# CHIRURGISCHER LOGIK-FIX: Alte Handler restlos entfernen vor der Neuzuweisung
if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(os.path.join(FOLDER_STRUCTURE["logs"], "app.log"), encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Verhindert doppelte Protokollierung über den Root-Logger des Systems
logger.propagate = False

# ==============================================================================
# 4. INITIALISIERUNGS-FUNKTION
# ==============================================================================
def initialize_project():
    """
    Validiert die stochastisch ermittelten Ordner, legt fehlende Basis-Ordner an
    und speichert die gesamte duplikatfreie Struktur als JSON-Konfiguration.
    """
    logger.info("--- Stochastische Projekt-Initialisierung gestartet ---")
    logger.info(f"Bestätigtes Hauptverzeichnis (Root): {PROJECT_ROOT}")
    
    # Ordner auf der Festplatte prüfen, erstellen und protokollieren
    for folder_name, folder_path in FOLDER_STRUCTURE.items():
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"[ERSTELLT] Neuer stochastischer Begriff '{folder_name}' --> Pfad: {folder_path}")
        else:
            logger.info(f"[OK - GESCHÜTZT] Begriff '{folder_name}' bereits aktiv --> Pfad: {folder_path}")

    # Pfade als JSON im Config-Ordner sichern für zukünftige Skripte
    config_file_path = os.path.join(FOLDER_STRUCTURE["config"], "project_paths.json")
    
    try:
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(FOLDER_STRUCTURE, f, indent=4, ensure_ascii=False)
        logger.info(f"Globale Pfad-Begriffe erfolgreich gesichert in: {config_file_path}")
        logger.info("--- Projekt-Initialisierung erfolgreich beendet ---\n")
    except Exception as e:
        logger.error(f"Konfiguration konnte nicht geschrieben werden: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    initialize_project()