import wasmtime
import json
import numpy
import random
from pathlib import Path
import sys
from colorama import Fore, Back, Style, init
import pyfiglet
from sidewinder_classes import registry, gamestate

init(autoreset=True)

banner_text = pyfiglet.figlet_format("Sidewinder engine", font="slant")
engine_dir = Path(__file__).parent
planet_maps_dir = engine_dir / "planet_maps"
item_attr_save_name = engine_dir / "json_files/item_attr.json"
ship_type_save_name = engine_dir / "json_files/ship_types.json"
game_db = gamestate(engine_dir / "gamestate.db")
def startup_checks():
    
    print(Fore.CYAN + banner_text) 
    
    # check if planet maps directory exists
    if planet_maps_dir.is_dir():
        print(Fore.GREEN + "\nPlanet gen map directory found: Continuing startup")
    else:
        sys.exit(Fore.RED + "\nPlanet gen map directory not found: Stopping")
    
    # item attribute file check
    if item_attr_save_name.is_file():
        print(Fore.GREEN + "\nItem attributes JSON present: Continuing startup")
    else:
        sys.exit(Fore.RED + "\nItem attributes JSON not found: Stopping")
    
    if ship_type_save_name.is_file():
        print(Fore.GREEN + "\nShip types JSON present: Continuing startup")
    else:
        sys.exit(Fore.RED + "\nShip types JSON not found: Stopping")

    # set up tables
    try:
        print(Fore.CYAN + "Setting up database...")
        game_db.setup_tables()
        print(Fore.GREEN + "Database setup success!")
    except Exception as e:
        sys.exit(Fore.RED + f"ERROR: Failed to set up database! Details {e}")

if __name__ == "__main__":
    startup_checks()