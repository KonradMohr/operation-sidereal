import json
import sys
from colorama import Fore, init
import sqlite3
from pathlib import Path
import numpy as np

init(autoreset=True)

# This sets up the static jsons and adds commands to make it load.
class Registry:
    def __init__(self):
        self._items = {}
        self._ship_types = {}
        self._crafting_recipe = {}
        self._machine = {}
    
    def load(self, file_path, target_dict_name):
        try:
            with open(file_path, "r") as file:
                parsed_data = json.load(file)

                if target_dict_name == "item":
                    self._items = parsed_data
                elif target_dict_name == "ship_type":
                    self._ship_types = parsed_data
                elif target_dict_name == "crafting_recipe":
                    self._crafting_recipe = parsed_data
                elif target_dict_name == "machine":
                    self._machine = parsed_data

            print(Fore.GREEN + f"Parsed {file_path.name} successfully!")
        except json.JSONDecodeError:
            sys.exit(Fore.RED + f"ERROR: failed to parse JSON {file_path.name}, possibly corrupted or formatted badly")

    def load_item(self, item_id):
        item = self._items.get(item_id)

        if item is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent item '{item_id}'.")
            return {"name": None, "type": None, "mass": None, "sprite": None}

        return item
    
    def load_ship_type(self, ship_type_id):
        ship_type = self._ship_types.get(ship_type_id)

        if ship_type is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent ship type '{ship_type_id}'.")
            return {"name": None, "type": None, "speed": None, "acceleration": None, "health": None, "sprite": None}
        
        return ship_type
    
    def load_crafting_recipe(self, crafting_id):
        crafting_recipe = self._crafting_recipe.get(crafting_id)

        if crafting_recipe is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent crafting recipe '{crafting_id}'.")
            return {"name": None, "input": None, "output": None, "machine_type": None, "min_machine_lv": None}
        
        return crafting_recipe

    def load_machine(self, machine_id):
        machine = self._machine.get(machine_id)

        if machine is None:
            print(Fore.YELLOW + f"WARNING: Attempted to fetch non-existent machine '{machine_id}'.")
            return {"name": None, "tile_id": None, "machine_type": None, "machine_lv": None, "power_requirment": None, "power_output": None, "max_input": None, "speed": None, "width": None, "height": None}
        return machine

# This is used to modify or change values of things that rapidly change. Such as planets, ships, etc...
class GameState:
    
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
        self.factory_tilegrids_ram = {}
        self.grid_data_ram = {}
    
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
                max_storage INTEGER
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
                max_storage INTEGER
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS factory_tilegrids (
                grid_id TEXT PRIMARY KEY,
                planet_id TEXT,
                pos_x REAL,
                pos_y REAL
            )
            '''
        )

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grid_data (
                grid_id TEXT PRIMARY KEY,
                height INTEGER,
                width INTEGER,
                matrix_blob BLOB,
                next_instance INTEGER,
                active_machines_json TEXT
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
        self.conn.commit()

    def make_planet(self, planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path):
        self.cursor.execute('''
            INSERT INTO planets (planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', 
            (planet_id, solarsystem_id, galaxy_id, type, distance, orbit, time, waterlv, map_path)
        )
        self.conn.commit()
    
    def make_planet_inventory(self, planet_id, item_id, quantity, max_storage):
        self.cursor.execute('''
            INSERT INTO planet_inv (planet_id, item_id, quantity, max_storage)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (planet_id, item_id, quantity, max_storage)
        )
        self.conn.commit()

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
        self.conn.commit()
    
    def make_ship_inventory(self, ship_id, item_id, quantity, max_storage):
        self.cursor.execute('''
            INSERT INTO ship_inv (ship_id, item_id, quantity, max_storage)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (ship_id, item_id, quantity, max_storage)
        )
        self.conn.commit()
    
    def make_factory_tilegrid(self, grid_id, planet_id, pos_x, pos_y):
        self.cursor.execute('''
            INSERT INTO factory_tilegrids (grid_id, planet_id, pos_x, pos_y)
            VALUES (?, ?, ?, ?)
            ''',
            (grid_id, planet_id, pos_x, pos_y)
        )
        self.conn.commit()
    
    def make_grid_data(self, grid_id, height, width, matrix_blob, next_instance, active_machines_json):
        self.cursor.execute('''
            INSERT INTO grid_data (grid_id, height, width, matrix_blob, next_instance, active_machines_json)
            VALUES (?, ?, ?, ?)
            ''',
            (grid_id, height, width, matrix_blob, next_instance, active_machines_json)
        )
        self.conn.commit()

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
        self.conn.commit()
    
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

    def remove_factory_tilegrid(self, grid_id):
        self.cursor.execute('''
            DELETE FROM factory_tilegrids
            WHERE grid_id = ?
            ''',
            (grid_id,)
        )
        self.conn.commit()
    
    def remove_grid_data(self, grid_id):
        self.cursor.execute('''
            DELETE FROM grid_data
            WHERE grid_id = ?
            ''',
            (grid_id,)
        )
    
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

    def save_planet_inventory(self, planet_id, item_id, quantity, max_storage):
        self.cursor.execute('''
            UPDATE planet_inv
            SET quantity = ?, max_storage = ?
            WHERE planet_id = ? AND item_id = ?
            ''',
            (quantity, max_storage, planet_id, item_id)
        )
        self.conn.commit()
    
    def save_ship_inventory(self, ship_id, item_id, quantity, max_storage):
        self.cursor.execute('''
            UPDATE ship_inv
            SET quantity = ?, max_storage = ?
            WHERE ship_id = ? AND item_id = ?
            ''',
            (quantity, max_storage, ship_id, item_id)
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
    
    def save_grid_data(self, grid_id, height, width, matrix_blob, next_instance, active_machines_json):
        self.cursor.execute('''
            UPDATE grid_data
            SET height = ?, width = ?, matrix_blob = ?, next_instance = ?, active_machines_json = ?
            WHERE grid_id = ?
            ''',
            (height, width, matrix_blob, next_instance, active_machines_json)
        )
        self.conn.commit()
    

    # LOAD FUNCTIONS: the hardest to make, out of the CRUD functions, but the most useful. well... they are all equally useful.
    
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
            SELECT quantity, max_storage
            FROM ship_inv
            WHERE ship_id = ? AND item_id = ?
            ''',
            (ship_id, item_id)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:

            self.ship_inv_ram[(ship_id, item_id)] = {
                "quantity": pre_ram[0],
                "max_storage": pre_ram[1]
            }

            print(Fore.GREEN + f"Loaded ship inventory table {ship_id} with item {item_id} to RAM")
            print(Fore.CYAN + str(self.ship_inv_ram[(ship_id, item_id)]))
        else:
            print(Fore.RED + f"Failed to load ship inventory table {ship_id} with item {item_id} to RAM")
    
    def load_planet_inventory(self, planet_id, item_id):
        self.cursor.execute('''
            SELECT quantity, max_storage
            FROM planet_inv
            WHERE planet_id = ? AND item_id = ?
            ''',
            (planet_id, item_id)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:

            self.planet_inv_ram[(planet_id, item_id)] = {
                "quantity": pre_ram[0],
                "max_storage": pre_ram[1]
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
                "distance": pre_ram[2],
                "orbit": pre_ram[3],
                "star_type": pre_ram[4]
            }

            print(Fore.GREEN + f"Loaded solarsystem table {solarsystem_id} to RAM")
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
            print(Fore.CYAN + str(self.ship_equipment_ram[(ship_id, slot_type)]))
        else:
            print(Fore.RED + f"Failed to load ship_equipment table {ship_id} with slot_type {slot_type} to RAM")
    
    def load_factory_tilegrid(self, planet_id):
        self.cursor.execute('''
            SELECT grid_id, pos_x, pos_y
            FROM factory_tilegrids
            WHERE planet_id = ?
            ''',
            (planet_id,)
        )
        pre_ram = self.cursor.fetchall()

        if pre_ram:

            if planet_id not in self.factory_tilegrids_ram:
                self.factory_tilegrids_ram[planet_id] = []
            
            for row in pre_ram:
                grid_id = row[0]
                pos_x = row[1]
                pos_y = row[2]

                self.factory_tilegrids_ram[planet_id].append({
                    "grid_id": grid_id,
                    "pos_x": pos_x,
                    "pos_y": pos_y
                })

            print(Fore.GREEN + f"Loaded factory_tilegrids table {planet_id} to RAM")
            print(Fore.CYAN + str(self.factory_tilegrids_ram[planet_id]))
        else:
            print(Fore.RED + f"Failed to load factory_tilegrids table {planet_id} to RAM")

    def load_grid_data(self, grid_id):
        self.cursor.execute('''
            SELECT height, width, matrix_blob, next_instance, active_machines_json
            FROM grid_data
            WHERE grid_id = ?
            ''',
            (grid_id,)
        )
        pre_ram = self.cursor.fetchone()

        if pre_ram:
            self.grid_data_ram[grid_id] = {
                "height": pre_ram[0],
                "width": pre_ram[1],
                "matrix_blob": pre_ram[2],
                "next_instance": pre_ram[3],
                "active_machines_json": pre_ram[4]
            }

            print(Fore.GREEN + f"Loaded grid_data table {grid_id} to RAM")
            print(Fore.CYAN + str(self.grid_data_ram[grid_id]))
        else:
            print(Fore.RED + f"Failed to load grid_data table {grid_id} to RAM")


class GridManagement:
    def __init__(self, active_machines, next_instance, grid_height, grid_width, matrix_blob):
        self.active_machines = active_machines

        if matrix_blob:
            unpacked_grid_data = np.frombuffer(matrix_blob, dtype=int)
            self.grid = unpacked_grid_data.reshape((grid_height, grid_width))
            self._next_instance = next_instance
        else:
            self.grid = np.zeros((grid_height, grid_width), dtype=int)
            self._next_instance = 1
    
    def set_tile(self, machine_id, anchor_pos_x, anchor_pos_y, machine_height, machine_width):
        if anchor_pos_y >= 0 and anchor_pos_x >= 0 and (anchor_pos_y + machine_height) <= self.grid.shape[0] and (anchor_pos_x + machine_width) <= self.grid.shape[1]:

            current_id = self._next_instance

            self.grid[anchor_pos_y: anchor_pos_y + machine_height, anchor_pos_x: anchor_pos_x + machine_width] = current_id
            self.active_machines[current_id] = {"machine_id": machine_id, "anchor_pos_x": anchor_pos_x, "anchor_pos_y": anchor_pos_y}
            self._next_instance += 1
        else:
            print(Fore.RED + f"Failed to place machine {machine_id} on grid! Not in grid range: height {self.grid.shape[0]} and width {self.grid.shape[1]}")
    
    def get_tile(self, pos_x, pos_y):
        if pos_y >= 0 and pos_x >= 0 and pos_y < self.grid.shape[0] and pos_x < self.grid.shape[1]:
            return self.grid[pos_y, pos_x]
        else:
            print(Fore.RED + f"Failed to obtain tile data {pos_x}, {pos_y}")
            return 0
    
    def remove_tile(self, instance_id, width, height):
        target = self.active_machines.get(instance_id)

        if not target: return

        else:
            anchor_pos_y = self.active_machines[instance_id]["anchor_pos_y"]
            anchor_pos_x = self.active_machines[instance_id]["anchor_pos_x"]
        
            self.grid[anchor_pos_y: anchor_pos_y + height, anchor_pos_x: anchor_pos_x + width] = 0

            del self.active_machines[instance_id]
    
    def get_blob(self):
        return self.grid.tobytes()