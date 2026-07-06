import os
import sys
import platform
import subprocess
import urllib.request

class BaseInstaller:
    """Basis-Klasse mit gemeinsamen Funktionen für alle Betriebssysteme."""
    def __init__(self, target_env_name="MaiOmni", python_version="3.10.20"):
        self.target_env_name = target_env_name
        self.python_version = python_version
        self.system = platform.system()

    def log(self, message):
        print(f"[Installer] {message}")

    def run_command(self, command):
        """Führt einen Terminal-Befehl aus."""
        try:
            result = subprocess.run(command, shell=True, check=True, text=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            self.log(f"Fehler beim Ausführen von: {command}\nDetails: {e}")
            return False

    def check_miniconda(self):
        """Prüft, ob Conda/Miniconda bereits installiert ist."""
        try:
            subprocess.run("conda --version", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def check_env_exists(self):
        """Prüft via CLI, ob die Conda-Umgebung bereits existiert."""
        try:
            output = subprocess.check_output("conda env list", shell=True, text=True)
            # Filtert die Zeilen und isoliert die reinen Umgebungsnamen
            envs = [line.split()[0] for line in output.splitlines() if line and not line.startswith("#")]
            return self.target_env_name in envs
        except subprocess.CalledProcessError:
            return False

    def create_conda_env(self):
        """Erstellt die gewünschte Python-Umgebung via Conda mit Überschreib-Abfrage."""
        if not self.check_miniconda():
            self.log("Conda wurde nicht gefunden! Installiere erst Miniconda (siehe Anleitung).")
            return False
        
        # LOGIK: Überprüfung des vorhandenen Python-Zustands / der Umgebung
        if self.check_env_exists():
            print("\n" + "=" * 60)
            user_choice = input(f"[ACHTUNG] Die Umgebung '{self.target_env_name}' existiert bereits.\nSoll sie überschrieben werden? (y/n): ").strip().lower()
            print("=" * 60 + "\n")
            
            if user_choice in ['y', 'yes']:
                self.log(f"Lösche alte Umgebung '{self.target_env_name}'...")
                remove_cmd = f"conda env remove -n {self.target_env_name} -y"
                if not self.run_command(remove_cmd):
                    self.log("[FEHLER] Alte Umgebung konnte nicht sauber entfernt werden.")
                    return False
            else:
                self.log(f"Überspringe Erstellung. Bestehende Umgebung '{self.target_env_name}' bleibt unverändert.")
                return True

        self.log(f"Erstelle Conda-Umgebung '{self.target_env_name}' mit Python {self.python_version}...")
        command = f"conda create -n {self.target_env_name} python={self.python_version} -y"
        return self.run_command(command)

    def install_dependencies(self):
        """Installiert die Basis-Bibliotheken in die neue Umgebung."""
        self.log(f"Installiere/Überprüfe Basis-Pakete in '{self.target_env_name}'...")
        # Hier nutzen wir 'conda run -n', damit wir nicht mühsam die Shell wechseln müssen
        command = f"conda run -n {self.target_env_name} pip install jupyter ipykernel"
        return self.run_command(command)

    def run(self):
        """Haupt-Workflow der Installation."""
        raise NotImplementedError("Die 'run'-Methode muss von der Subklasse implementiert werden!")


class WindowsInstaller(BaseInstaller):
    """Spezifische Installations-Logik für Windows."""
    def install_miniconda_sys(self):
        if self.check_miniconda():
            self.log("Conda ist bereits auf Windows installiert.")
            return True
        
        self.log("Lade Miniconda für Windows herunter...")
        url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
        installer_path = os.path.join(os.environ.get("TEMP", "."), "miniconda_installer.exe")
        
        try:
            urllib.request.urlretrieve(url, installer_path)
            self.log("Starte Miniconda-Installation (Silent)... Bitte kurz warten.")
            
            # Pfad vorab berechnen, um den Backslash aus dem f-String zu verbannen
            target_dir = os.path.expanduser("~\\miniconda3")
            
            # Installiert Miniconda silent im Standardpfad für den aktuellen User
            install_cmd = f'"{installer_path}" /InstallationType=JustMe /RegisterPython=0 /S /D={target_dir}'
            
            if self.run_command(install_cmd):
                self.log("Miniconda erfolgreich installiert. Bitte starte das Terminal neu, falls 'conda' nicht direkt erkannt wird.")
                return True
        except Exception as e:
            self.log(f"Fehler bei der Windows-Miniconda-Installation: {e}")
        return False

    def run(self):
        self.log("--- Starte Windows Installation ---")
        if not self.check_miniconda():
            if not self.install_miniconda_sys():
                return
        
        if self.create_conda_env():
            self.install_dependencies()
            self.log("Windows-Setup abgeschlossen!")


class MacOSInstaller(BaseInstaller):
    """Spezifische Installations-Logik für macOS (M-Chips/Intel)."""
    def install_miniconda_sys(self):
        if self.check_miniconda():
            self.log("Conda ist bereits auf macOS installiert.")
            return True
        
        self.log("Lade Miniconda für macOS herunter...")
        # Erkennt automatisch, ob M-Chip (arm64) oder alter Intel (x86_64)
        arch = "arm64" if platform.processor() == "arm" else "x86_64"
        url = f"https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-{arch}.sh"
        installer_path = "/tmp/miniconda_installer.sh"
        
        try:
            urllib.request.urlretrieve(url, installer_path)
            self.log("Starte Miniconda-Installation...")
            self.run_command(f"chmod +x {installer_path}")
            # Installiert es silent im Home-Verzeichnis
            install_cmd = f"sh {installer_path} -b -p $HOME/miniconda3"
            if self.run_command(install_cmd):
                self.log("Miniconda erfolgreich installiert!")
                return True
        except Exception as e:
            self.log(f"Fehler bei der macOS-Miniconda-Installation: {e}")
        return False

    def run(self):
        self.log("--- Starte macOS Installation ---")
        if not self.check_miniconda():
            if not self.install_miniconda_sys():
                # Falls die Silent-Methode fehlschlägt, Pfad-Ausgabe als Fallback
                self.log("Bitte stelle sicher, dass Conda in deinem $PATH liegt.")
                return
        
        if self.create_conda_env():
            self.install_dependencies()
            self.log("macOS-Setup abgeschlossen!")


def main():
    # Factory: Erkennt das Betriebssystem und wählt die richtige Klasse
    current_os = platform.system()
    
    if current_os == "Windows":
        installer = WindowsInstaller()
    elif current_os == "Darwin":  # Darwin ist der Systemname für macOS
        installer = MacOSInstaller()
    else:
        print(f"[Installer] Betriebssystem '{current_os}' wird derzeit nicht unterstützt.")
        sys.exit(1)
        
    installer.run()

if __name__ == "__main__":
    main()