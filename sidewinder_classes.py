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
        self.ship_inv_ram = {}
        self.planet_inv_ram = {}
        self.total_throughput_ram = {}
        self.solarsystem_ram = {}
        self.galaxy_ram = {}
        self.ship_equipment_ram = {}
    
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

        # table that holds ship inventory data
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
        
        # table to hold planet inventory data
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
            CREATE TABLE IF NOT EXISTS solarsystem (
                solarsystem_id TEXT PRIMARY KEY,
                galaxy_id TEXT,
                name TEXT,
                distance REAL,
                orbit REAL,
                star_type TEXT
            )
            '''
            )

        # table to define galaxies
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS galaxy (
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
    
    # CRUD FUNCTIONS: boy I hate writing these, but they are necessary for dynamic values that constantly get changed.

    # MAKE FUNCTIONS: easy to make, easy to use. These are used to make rows in the desired SQL table.
    def make_galaxy(self, galaxy_id, name, pos_x, pos_y, radius):
        self.cursor.execute('''
            INSERT INTO galaxy (galaxy_id, name, pos_x, pos_y, radius)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (galaxy_id, name, pos_x, pos_y, radius)
        )
        self.conn.commit()

    def make_solarsystem(self, solarsystem_id, galaxy_id, name, distance, orbit, star_type):
        self.cursor.execute('''
            INSERT INTO solarsystem (solarsystem_id, galaxy_id, name, distance, orbit, star_type)
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
    
    def make_planet_inventory(self, planet_id, item_id, quantity, max_storage, max_population, quarters):
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

    def make_total_throughput(self, planet_id, item_id, net_change, tick_cycle):
        self.cursor.execute('''
            INSERT INTO total_throughput (planet_id, item_id, net_change, tick_cycle)
            VALUES (?, ?, ?, ?)
            ''',
            (planet_id, item_id, net_change, tick_cycle)
        )
    
    def make_ship_inventory(self, ship_id, item_id, quantity, max_storage, max_population, quarters):
        self.cursor.execute('''
            INSERT INTO ship_inv (ship_id, item_id, quantity, max_storage, max_population, quarters)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (ship_id, item_id, quantity, max_storage, max_population, quarters)
        )

    # REMOVE FUNCTIONS: easier to make, and easier to use then the MAKE FUNCTIONS family

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
    
    def remove_galaxy(self, galaxy_id):
        self.cursor.execute('''
            DELETE FROM galaxy
            WHERE galaxy_id = ?
            ''',
            (galaxy_id,)
        )
        self.conn.commit()
    
    def remove_solarsystem(self, solarsystem_id):
        self.cursor.execute('''
            DELETE FROM solarsystem
            WHERE solarsystem_id = ?
            ''',
            (solarsystem_id,)
        )
    
    def remove_ship_equipment(self, ship_id):
        self.cursor.execute('''
            DELETE FROM ship_equipment
            WHERE ship_id = ?
            ''',
            (ship_id,)
        )
        self.conn.commit()
    
    def remove_planet_inventory(self, planet_id):
        self.cursor.execute('''
            DELETE FROM planet_inv
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        self.conn.commit()
    
    def remove_ship_inventory(self, ship_id):
        self.cursor.execute('''
            DELETE FROM ship_inv
            WHERE ship_id = ?
            ''',
            (ship_id,)
        )
        self.conn.commit()
    
    def remove_total_throughput(self, planet_id):
        self.cursor.execute('''
            DELETE FROM total_throughput
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        self.conn.commit()
    
    
    # SAVE FUNCTIONS: Saves data to a specific row in a table, this took 2 and a half hours to finish, please treat it well.

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
    
    def save_galaxy(self, galaxy_id, name, pos_x, pos_y, radius):
        self.cursor.execute('''
            UPDATE galaxy
            SET name = ?, pos_x = ?, pos_y = ?, radius = ?
            WHERE galaxy_id = ?
            ''',
            (name, pos_x, pos_y, radius, galaxy_id)
        )
        self.conn.commit()

    def save_solarsystem(self, solarsystem_id, galaxy_id, name, distance, orbit, star_type):
        self.cursor.execute('''
            UPDATE solarsystem
            SET galaxy_id = ?, name = ?, distance = ?, orbit = ?, star_type = ?
            WHERE solarsystem_id = ?
            ''',
            (galaxy_id, name, distance, orbit, star_type, solarsystem_id)
        )
        self.conn.commit()

    def save_planet_inventory(self, planet_id, item_id, quantity, max_storage, max_population, quarters):
        self.cursor.execute('''
            UPDATE planet_inv
            SET quantity = ?, max_storage = ?, max_population = ?, quarters = ?
            WHERE planet_id = ? AND item_id = ?
            ''',
            (quantity, max_storage, max_population, quarters, planet_id, item_id)
        )
        self.conn.commit()
    
    def save_ship_inventory(self, ship_id, item_id, quantity, max_storage, max_population, quarters):
        self.cursor.execute('''
            UPDATE ship_inv
            SET quantity = ?, max_storage = ?, max_population = ?, quarters = ?
            WHERE ship_id = ? AND item_id = ?
            ''',
            (quantity, max_storage, max_population, quarters, ship_id, item_id)
        )
        self.conn.commit()
    
    def save_ship_equipment(self, ship_id, slot_type, item_id):
        self.cursor.execute('''
            UPDATE ship_equipment
            SET item_id = ?
            WHERE ship_id = ? AND slot_type = ?
            ''',
            (item_id, ship_id, slot_type)
        )
        self.conn.commit()

    def save_total_throughput(self, planet_id, item_id, net_change, tick_cycle):
        self.cursor.execute('''
            UPDATE total_throughput
            SET net_change = ?, tick_cycle = ?
            WHERE planet_id = ? AND item_id = ?
            ''',
            (net_change, tick_cycle, planet_id, item_id)
        )
        self.conn.commit()

    # load functions, the hardest to make, out of the CRUD functions, but the most useful. well... they are all equally useful.
    # TODO: add funtions for these tables: galaxies, solar_systems, ship_equipment, planet_inv, ship_inv, ship_equipment, total_throughput
    def load_ship(self, ship_id):
        self.cursor.execute('''
            SELECT pos_x, pos_y, health
            FROM active_ships
            WHERE ship_id = ?
        ''',
            (ship_id,)
        )
        pre_ram = self.cursor.fetchone()
        if pre_ram:
            self.ship_ram[ship_id] = {
                "pos_x": pre_ram[0],
                "pos_y": pre_ram[1],
                "health": pre_ram[2]
            }
            print(Fore.GREEN + f"Saved ship table {ship_id} to RAM")
            print(Fore.CYAN + self.ship_ram[ship_id])
        else:
            print(Fore.RED + f"Failed to load ship table {ship_id} to RAM: Ship ID not found!")

    def load_planet(self, planet_id):
        self.cursor.execute('''
            SELECT solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path
            FROM planets
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.planet_ram[planet_id] = {
                "solarsystem_id": pre_ram[0],
                "galaxy_id": pre_ram[1],
                "type": pre_ram[2],
                "distance": pre_ram[3],
                "orbit": pre_ram[4],
                "time": pre_ram[5],
                "waterlv": pre_ram[6],
                "map_path": pre_ram[7]
            }
            print(Fore.GREEN + f"Loaded planet table {planet_id} to RAM")
            print(Fore.CYAN + str(self.planet_ram[planet_id]))
        else:
            print(Fore.RED + f"Failed to load planet table {planet_id} to RAM: Planet ID not found!")
        
    def load_ship_inventory(self, ship_id, item_id):
        self.cursor.execute('''
            SELECT quantity, max_storage, max_population, quarters
            FROM ship_inv
            WHERE ship_id = ? AND item_id = ?
            ''',
            (ship_id, item_id)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.ship_inv_ram[(ship_id, item_id)] = {
                "quantity": pre_ram[0],
                "max_storage": pre_ram[1],
                "max_population": pre_ram[2],
                "quarters": pre_ram[3]
            }
            print(Fore.GREEN + f"Loaded ship inventory table {ship_id} with item {item_id} to RAM")
            print(Fore.CYAN + str(self.ship_inv_ram[(ship_id, item_id)]))
        else:
            print(Fore.RED + f"Failed to load ship inventory table {ship_id} with item {item_id} to RAM")
    
    def load_planet_inventory(self, planet_id, item_id):
        self.cursor.execute('''
            SELECT quantity, max_storage, max_population, quarters
            FROM planet_inv
            WHERE planet_id = ? AND item_id = ?
            ''',
            (planet_id, item_id)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.planet_inv_ram[(planet_id, item_id)] = {
                "quantity": pre_ram[0],
                "max_storage": pre_ram[1],
                "max_population": pre_ram[2],
                "quarters": pre_ram[3]
            }
            print(Fore.GREEN + f"Loaded planet inventory table {planet_id} with item {item_id} to RAM")
            print(Fore.CYAN + str(self.planet_inv_ram[(planet_id, item_id)]))
        else:
            print(Fore.RED + f"Failed to load planet invetory table {planet_id} with item {item_id} to RAM")
    
    def load_total_throughput(self, planet_id, item_id):
        self.cursor.execute('''
            SELECT net_change, tick_cycle
            FROM total_throughput
            WHERE planet_id = ? AND item_id = ?
            ''',
            (planet_id, item_id)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.total_throughput_ram[(planet_id, item_id)] = {
                "net_change": pre_ram[0],
                "tick_cycle": pre_ram[1]
            }
            print(Fore.GREEN + f"Loaded throughput table {planet_id} with item {item_id} to RAM")
            print(Fore.CYAN + str(self.total_throughput_ram[(planet_id, item_id)]))
        else:
            print(Fore.RED + f"Failed to load throughput table {planet_id} with item {item_id} to RAM")
    
    def load_solarsystem(self, solarsystem_id):
        self.cursor.execute('''
            SELECT galaxy_id, name, distance, orbit, star_type
            FROM solarsystem
            WHERE solarsystem_id = ?
            ''',
            (solarsystem_id,)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.solarsystem_ram[solarsystem_id] = {
                "galaxy_id": pre_ram[0],
                "name": pre_ram[1],
                "orbit": pre_ram[2],
                "star_type": pre_ram[3]
            }
            print(Fore.GREEN + f"Loaded solarsystem table {solarsystem_id} with item {item_id} to RAM")
            print(Fore.CYAN + str(self.solarsystem_ram[solarsystem_id]))
        else:
            print(Fore.RED + f"Failed to load solarsystem table {solarsystem_id} to RAM")
    
    def load_galaxy(self, galaxy_id):
        self.cursor.execute('''
            SELECT name, pos_x, pos_y, radius
            FROM galaxy
            WHERE galaxy_id = ?
            ''',
            (galaxy_id,)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.galaxy_ram[galaxy_id] = {
                "name": pre_ram[0],
                "pos_x": pre_ram[1],
                "pos_y": pre_ram[2],
                "radius": pre_ram[3]
            }
            print(Fore.GREEN + f"Loaded galaxy table {galaxy_id} to RAM")
            print(Fore.CYAN + str(self.galaxy_ram[galaxy_id]))
        else:
            print(Fore.RED + f"Failed to load galaxy table {galaxy_id} to RAM")
    
    def load_ship_equipment(self, ship_id, slot_type):
        self.cursor.execute('''
            SELECT item_id
            FROM ship_equipment
            WHERE ship_id = ? AND slot_type = ?
            ''',
            (ship_id, slot_type)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.ship_equipment_ram[(ship_id, slot_type)] = {
                "item_id": pre_ram[0]
            }
            print(Fore.GREEN + f"Loaded ship_equipment table {ship_id} with slot_type {slot_type} to RAM")
            print(Fore.CYAN + self.ship_equipment_ram[(ship_id, slot_type)])
        else:
            print(Fore.RED + f"Failed to load ship_equipment table {ship_id} with slot_type {slot_type} to RAM")