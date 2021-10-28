import math

from lux import annotate
from typing import Dict, List

from .constants import Constants
from .game_position import Position
from .game_constants import GAME_CONSTANTS

UNIT_TYPES = Constants.UNIT_TYPES
DIRECTIONS = Constants.DIRECTIONS



class City:
    def __init__(self, teamid, cityid, fuel, light_upkeep):
        self.cityid = cityid
        self.team = teamid
        self.fuel = fuel
        self.citytiles: list[CityTile] = []
        self.light_upkeep = light_upkeep
        self.fuel_needed_for_remaining_nights = -1  # [TODO]

    def _add_city_tile(self, x, y, cooldown):
        ct = CityTile(self.team, self.cityid, x, y, cooldown)
        self.citytiles.append(ct)
        return ct

    def get_light_upkeep(self):
        return self.light_upkeep

    def get_autonomy_turns(self) -> int:
        turns_city_can_live = self.fuel // self.get_light_upkeep()
        return turns_city_can_live

    def get_num_tiles(self) -> int:
        return len(self.citytiles)

    def get_positions(self) -> [Position]:
        results = []
        for ct in self.citytiles:
            results.append(ct.pos)
        return results

class CityTile:
    def __init__(self, teamid, cityid, x, y, cooldown):
        self.cityid = cityid
        self.team = teamid
        self.pos = Position(x, y)
        self.cooldown = cooldown

    def can_act(self) -> bool:
        """
        Whether or not this unit can research or build
        """
        return self.cooldown < 1

    def research(self) -> str:
        """
        returns command to ask this tile to research this turn
        """
        return "r {} {}".format(self.pos.x, self.pos.y)

    def build_worker(self) -> str:
        """
        returns command to ask this tile to build a worker this turn
        """
        return "bw {} {}".format(self.pos.x, self.pos.y)

    def build_cart(self) -> str:
        """
        returns command to ask this tile to build a cart this turn
        """
        return "bc {} {}".format(self.pos.x, self.pos.y)

    def __repr__(self) -> str:
        return "ct {}".format(self.pos.__repr__())


class Cargo:
    def __init__(self):
        self.wood = 0
        self.coal = 0
        self.uranium = 0

    def get_space_used(self) -> int:
        return self.wood + self.coal + self.uranium;

    def __str__(self) -> str:
        return f"Cargo | Wood: {self.wood}, Coal: {self.coal}, Uranium: {self.uranium}"

    def fuel(self) -> int:
        return self.wood + self.coal * 10 + self.uranium * 40

    def to_string(self):
        return_value = ''
        if self.wood > 0:
            return_value = return_value + f"Wood:{self.wood}"
        if self.coal > 0:
            return_value = return_value + f" Coal:{self.coal}"
        if self.uranium > 0:
            return_value = return_value + f" Uran:{self.uranium}"

        return return_value


class Unit:
    def __init__(self, teamid, u_type, unitid, x, y, cooldown, wood, coal, uranium):
        self.pos = Position(x, y)
        self.team = teamid
        self.id = unitid
        self.type = u_type
        self.cooldown = cooldown
        self.cargo = Cargo()
        self.cargo.wood = wood
        self.cargo.coal = coal
        self.cargo.uranium = uranium
        self.compute_travel_range()

    def is_worker(self) -> bool:
        return self.type == UNIT_TYPES.WORKER

    def is_cart(self) -> bool:
        return self.type == UNIT_TYPES.CART

    def get_cargo_space_used(self) -> int:
        return self.cargo.get_space_used()

    def get_cargo_space_left(self):
        """
        get cargo space left in this unit
        """
        spaceused = self.get_cargo_space_used()
        if self.type == UNIT_TYPES.WORKER:
            return GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"]["WORKER"] - spaceused
        else:
            return GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"]["CART"] - spaceused

    def can_build(self, game_map) -> bool:
        """
        whether or not the unit can build where it is right now
        """
        cell = game_map.get_cell_by_pos(self.pos)
        if not cell.has_resource() and self.can_act() and (self.cargo.wood + self.cargo.coal + self.cargo.uranium) >= GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]:
            return True
        return False

    def can_act(self) -> bool:
        """
        whether or not the unit can move or not. This does not check for potential collisions into other units or enemy cities
        """
        return self.cooldown < 1

    def move(self, dir) -> str:
        """
        return the command to move unit in the given direction, and annotate
        """
        return "m {} {}".format(self.id, dir)


    def transfer(self, dest_id, resourceType, amount) -> str:
        """
        return the command to transfer a resource from a source unit to a destination unit as specified by their ids
        """
        return "t {} {} {} {}".format(self.id, dest_id, resourceType, amount)

    def build_city(self) -> str:
        """
        return the command to build a city right under the worker
        """
        return "bcity {}".format(self.id)

    def pillage(self) -> str:
        """
        return the command to pillage whatever is underneath the worker
        """
        return "p {}".format(self.id)

    def compute_travel_range(self, turn_info=None) -> None:
        fuel_per_turn = GAME_CONSTANTS["PARAMETERS"]["LIGHT_UPKEEP"]["WORKER"]
        cooldown_required = GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"]["WORKER"]
        day_length = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"]
        night_length = GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]

        turn_survivable = (self.cargo.wood // GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"]["WOOD"]) // fuel_per_turn
        turn_survivable += self.cargo.coal + self.cargo.uranium  # assumed RESOURCE_TO_FUEL_RATE > fuel_per_turn
        self.night_turn_survivable = turn_survivable
        self.night_travel_range = turn_survivable // cooldown_required  # plus one perhaps

        if turn_info:
            turns_to_night, turns_to_dawn, is_day_time = turn_info
            travel_range = max(1, turns_to_night // cooldown_required + self.night_travel_range - cooldown_required)
            if self.night_turn_survivable > turns_to_dawn and not is_day_time:
                travel_range = day_length // cooldown_required + self.night_travel_range
            if self.night_turn_survivable > night_length:
                travel_range = day_length // cooldown_required + self.night_travel_range
            self.travel_range = travel_range

    def encode_tuple_for_cmp(self):
        return (self.cooldown, self.cargo.wood, self.cargo.coal, self.cargo.uranium, self.is_worker())

    def __repr__(self):
        return "Unit("+self.id+")"



class Player:
    def __init__(self, team):
        self.team = team
        self.research_points = 0
        self.units: list[Unit] = []
        self.cities: Dict[str, City] = {}
        self.city_tile_count = 0

        self.units_by_id: Dict[str, Unit] = {}

    def get_num_city_tiles(self) -> int:
        num=0
        for city in self.cities.values():
            num += len(city.citytiles)

        return num

    def researched_coal(self) -> bool:
        return self.research_points >= GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["COAL"]

    def researched_uranium(self) -> bool:
        return self.research_points >= GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["URANIUM"]

    def make_index_units_by_id(self):
        self.units_by_id: Dict[str, Unit] = {}
        for unit in self.units:
            self.units_by_id[unit.id] = unit

    def is_position_adjacent_city(self, pos) -> bool:
        for city in self.cities.values():
            for city_tile in city.citytiles:
                if city_tile.pos.is_adjacent(pos):
                    return True

        return False

    def get_num_units_and_city_number_around_pos(self, pos: Position, distance=1) -> int:
        return len(self.get_units_and_city_number_around_pos(pos, distance=distance))

    def get_units_and_city_number_around_pos(self, pos: Position, distance=1) -> [Position]:
        results = []
        for city in self.cities.values():
            for city_tile in city.citytiles:
                if city_tile.pos.distance_to(pos) <= distance:
                    results.append(city_tile.pos)

        for unit in self.units:
            if unit.pos.distance_to(pos) <= distance:
                results.append(unit.pos)

        return results

    def is_unit_adjacent(self, pos) -> bool:
        for unit in self.units:
            if unit.pos.is_adjacent(pos):
                return True

        return False


    def is_unit_in_pos(self, pos) -> bool:
        for unit in self.units:
            if unit.pos.equals(pos):
                return True

        return False

    def get_unit_in_pos(self, pos) -> Unit:
        for unit in self.units:
            if unit.pos.equals(pos):
                return unit

        return None

    def get_units_number_around_pos(self, pos, distance) -> int:
        return self.get_units_around_pos(pos, distance).__len__()

    def get_units_around_pos(self, pos, distance) -> [Unit]:
        units: [Unit] = []
        for unit in self.units:
            if unit.pos.distance_to(pos) <= distance:
                units.append(unit)

        return units

    def get_closest_unit(self, pos) -> (Unit, int):
        distance = math.inf
        res_unit: Unit = None
        for unit in self.units:
            d = unit.pos.distance_to(pos)
            if d <= distance:
                res_unit = unit
                distance = d
                if distance == 0:
                    break

        return res_unit, distance