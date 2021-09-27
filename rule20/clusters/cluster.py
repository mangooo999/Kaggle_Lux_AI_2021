import math
from collections import defaultdict
from typing import DefaultDict, List
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS


# from missions.mission import Mission


class Cluster:
    def __init__(self, id: str, resource_cells: List[Cell], type: RESOURCE_TYPES):
        self.id: str = id
        self.resource_cells: List[Cell] = resource_cells
        self.units: List[str] = []
        self.enemy_unit: List[str] = []
        self.exposed_perimeter: List[Position] = []
        self.resource_type: RESOURCE_TYPES = type

    def add_unit(self, unit_id: str):
        if unit_id not in self.units:
            self.units.append(unit_id)

    def add_enemy_unit(self, unit_id: str):
        if unit_id not in self.enemy_unit:
            self.enemy_unit.append(unit_id)

    def to_string_light(self) -> str:
        return "{0} {1} r={2} u={3} e={4}".format(self.id, self.get_centroid(), len(self.resource_cells),
                                                  len(self.units), len(self.enemy_unit))

    def get_available_fuel(self) -> int:
        FUEL_CONVERSION_RATE = \
            GAME_CONSTANTS['PARAMETERS']['RESOURCE_TO_FUEL_RATE']

        def get_cell_fuel(cell: Cell):
            if cell.resource is None:
                return 0
            if cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                return cell.resource.amount * FUEL_CONVERSION_RATE['WOOD']
            if cell.resource.type == Constants.RESOURCE_TYPES.COAL:
                return cell.resource.amount * FUEL_CONVERSION_RATE['COAL']
            if cell.resource.type == Constants.RESOURCE_TYPES.URANIUM:
                return cell.resource.amount * FUEL_CONVERSION_RATE['URANIUM']
            return 0

        return sum([get_cell_fuel(cell) for cell in self.resource_cells])

    def get_fuel_density(self) -> float:
        return self.get_available_fuel() / len(self.resource_cells)

    def get_centroid(self):
        sum_x = sum([rc.pos.x for rc in self.resource_cells])
        sum_y = sum([rc.pos.y for rc in self.resource_cells])
        k = len(self.resource_cells)

        if k > 0:
            return Position(round(sum_x / k), round(sum_y / k))

        return Position(math.inf, math.inf)
