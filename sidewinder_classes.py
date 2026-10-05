import json
import sys
from colorama import Fore, init
import sqlite3
from pathlib import Path

init(autoreset=True)

# This sets up the static jsons and adds commands to make it load.
class registry:
    def __init__(self):
        self._items = {}
        self._ship_types = {}
    
    def load(self, file_path, target_dict_name):
        try:
            with open(file_path, "r") as file:
                parsed_data = json.load(file)

                if target_dict_name == "item":
                    self._items = parsed_data
                elif target_dict_name == "ship_type":
                    self._ship_types = parsed_data

            print(Fore.GREEN + f"Parsed {file_path.name} successfully!")
        except json.JSONDecodeError:
            sys.exit(Fore.RED + f"ERROR: failed to parse JSON {file_path.name}, possibly corrupted or formatted badly")

    def get_item(self, item_id):
        item = self._items.get(item_id)

        if item is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent item '{item_id}'.")
            return {"name": None, "type": None, "speed": None, "mass": None, "crafting_lv": None}

        return item
    
    def get_ship_type(self, ship_type_id):
        ship_type = self._ship_types.get(ship_type_id)

        if ship_type is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent ship type '{ship_type_id}'.")
            return {"name": None, "type": None, "speed": None, "acceleration": None, "health": None}

        return ship_type

# This is used to modify or change values of things that rapidly change. Such as planets, ships, etc...
class gamestate:
    
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.planet_ram = {}
        self.ship_ram = {}
    
    def setup_tables(self):

        # table to hold current active ship data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_ships (
                ship_id TEXT PRIMARY KEY,
                type TEXT,
                pos_x REAL,
                pos_y REAL,
                health INTEGER
            )
            '''
            )
        # table that holds planet data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS planets (
                planet_id TEXT PRIMARY KEY,
                solarsystem_id TEXT,
                galaxy_id TEXT,
                type TEXT,
                distance REAL,
                orbit REAL,
                time INTEGER,
                waterlv INTEGER,
                map_path TEXT
            )
            '''
            )

        # table that holds ship invetory data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ship_inv (
                ship_id TEXT,
                item_id TEXT,
                quantity INTEGER,
                max_storage INTEGER,
                max_population INTEGER,
                quarters INTEGER,
                PRIMARY KEY (ship_id, item_id)
            )
            '''
            )
        
        # table to hold planet invetory data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS planet_inv (
                planet_id TEXT,
                item_id TEXT,
                quantity INTEGER,
                max_storage INTEGER,
                max_population INTEGER,
                quarters INTEGER,
                PRIMARY KEY (planet_id, item_id)
            )
            '''
            )
        
        # table to define planet throughput
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS total_throughput (
                planet_id TEXT,
                item_id TEXT,
                net_change INTEGER, 
                tick_cycle INTEGER,
                PRIMARY KEY (planet_id, item_id)
            )
            '''
            )
        
        # table to define solar systems
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS solar_systems (
                solarsystem_id TEXT PRIMARY KEY,
                galaxy_id TEXT,
                name TEXT,
                distance REAL,
                orbit REAL,
                star_type TEXT
            )
            '''
            )

        # table to define macro galaxies
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS galaxies (
                galaxy_id TEXT PRIMARY KEY,
                name TEXT,
                pos_x REAL,
                pos_y REAL,
                radius REAL
            )
            '''
            )
        
        # table for ship equipment
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ship_equipment (
                ship_id TEXT,
                slot_type TEXT,
                item_id TEXT,
                PRIMARY KEY (ship_id, slot_type)
            )
            '''
            )
        

        self.conn.commit()
    
    '''CRUD FUNCTIONS: boy I hate writing these'''

    def make_galaxy(self, galaxy_id, name, pos_x, pos_y, radius):
        self.cursor.execute('''
            INSERT INTO galaxies (galaxy_id, name, pos_x, pos_y, radius)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (galaxy_id, name, pos_x, pos_y, radius)
        )
        self.conn.commit()

    def make_solarsystem(self, solarsystem_id, galaxy_id, name, distance, orbit, star_type):
        self.cursor.execute('''
            INSERT INTO solar_systems (solarsystem_id, galaxy_id, name, distance, orbit, star_type)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (solarsystem_id, galaxy_id, name, distance, orbit, star_type)
        )
        self.conn.commit()
    
    def make_ship_equipment(self, ship_id, slot_type, item_id):
        self.cursor.execute('''
            INSERT INTO ship_equipment (ship_id, slot_type, item_id)
            VALUES (?, ?, ?)
            ''',
            (ship_id, slot_type, item_id)
        )

    def make_planet(self, planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path):
        self.cursor.execute('''
            INSERT INTO planets (planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', 
            (planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path)
        )
        self.conn.commit()
    
    def make_planet_invetory(self, planet_id, item_id, quantity, max_storage, max_population, quarters):
        self.cursor.execute('''
            INSERT INTO planet_inv (planet_id, item_id, quantity, max_storage, max_population, quarters)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (planet_id, item_id, quantity, max_storage, max_population, quarters)
        )

    def make_ship(self, ship_id, type, pos_x, pos_y, health):
        self.cursor.execute('''
            INSERT INTO active_ships (ship_id, type, pos_x, pos_y, health)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (ship_id, type, pos_x, pos_y, health)
        )
        self.conn.commit()
    
    def make_ship_invetory(self, ship_id, item_id, quantity, max_storage, max_population, quarters):
        self.cursor.execute('''
            INSERT INTO ship_inv (ship_id, item_id, quantity, max_storage, max_population, quarters)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (ship_id, item_id, quantity, max_storage, max_population, quarters)
        )

    def remove_planet(self, planet_id):
        self.cursor.execute('''
            DELETE FROM planets
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        self.conn.commit()

    def remove_ship(self, ship_id):
        self.cursor.execute('''
        DELETE FROM active_ships
        WHERE ship_id = ?
            ''',
            (ship_id,)
        )
        self.conn.commit()
    
    # save commands
    def save_planet(self, planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path):
        self.cursor.execute('''
            UPDATE planets
            SET solarsystem_id = ?, galaxy_id = ?, type = ?, distance = ?, orbit = ?, time = ?, waterlv = ?, map_path = ?
            WHERE planet_id = ?
            ''',
            (solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path, planet_id)
        )
        self.conn.commit()

    def save_ship(self, ship_id, pos_x, pos_y, health):
        self.cursor.execute('''
            UPDATE active_ships
            SET pos_x = ?, pos_y = ?, health = ?
            WHERE ship_id = ?
            ''',
            (pos_x, pos_y, health, ship_id)
        )
        self.conn.commit()

    def load_ship(self, ship_id):
        self.cursor.execute('''
            SELECT pos_x, pos_y, health
            FROM active_ships
            WHERE ship_id = ?
            ''',
            (ship_id,)
        )
        pre_ram_ship = self.cursor.fetchone()
        if pre_ram_ship:
            self.ship_ram[ship_id] = {
                "pos_x": pre_ram_ship[0],
                "pos_y": pre_ram_ship[1],
                "health": pre_ram_ship[2]
            }
            print(Fore.GREEN + f"Saved ship {ship_id} to RAM")
            print(Fore.CYAN + self.ship_ram)
        else:
            print(Fore.RED + f"failed to load ship database {ship_id} to ram: Ship id not found!")

    def load_planet(self, planet_id):
        self.cursor.execute('''
            SELECT solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path
            FROM planets
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        pre_ram_planet = self.cursor.fetchone()

        if pre_ram_planet:
            self.planet_ram[planet_id] = {
                "solarsystem_id": pre_ram_planet[0],
                "galaxy_id": pre_ram_planet[1],
                "type": pre_ram_planet[2],
                "distance": pre_ram_planet[3],
                "orbit": pre_ram_planet[4],
                "time": pre_ram_planet[5],
                "waterlv": pre_ram_planet[6],
                "map_path": pre_ram_planet[7]
            }
            print(Fore.GREEN + f"Saved planet {planet_id} to RAM")
            print(Fore.CYAN + str(self.planet_ram))
        else:
            print(Fore.RED + f"failed to load planet database {planet_id} to ram: Planet id not found!")