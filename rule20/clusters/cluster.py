import math
import sys
from collections import defaultdict
from typing import DefaultDict, List
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
import maps.map_analysis as MapAnalysis
import resources.resource_helper as ResourceService

# from missions.mission import Mission
from lux.game_objects import Player


class Cluster:
    def __init__(self, id: str, resource_cells: List[Cell], type: RESOURCE_TYPES):
        self.id: str = id
        self.resource_cells: List[Cell] = resource_cells
        self.units: List[str] = []
        self.enemy_unit: List[str] = []
        self.exposed_perimeter: List[Position] = []
        self.resource_type: RESOURCE_TYPES = type
        self.closest_unit = ''
        self.closest_unit_distance = math.inf
        self.closest_enemy_distance = math.inf

    def add_unit(self, unit_id: str):
        if unit_id not in self.units:
            self.units.append(unit_id)

    def add_enemy_unit(self, unit_id: str):
        if unit_id not in self.enemy_unit:
            self.enemy_unit.append(unit_id)

    def to_string_light(self) -> str:
        return "{0} {1} r={2} u={3} e={4}".format(self.id, self.get_centroid(), len(self.resource_cells),
                                                  len(self.units), len(self.enemy_unit))

    def is_more_units_than_res(self) -> bool:
        return len(self.units) > len(self.resource_cells)

    def has_no_units_no_enemy(self) -> bool:
        return len(self.units) ==0 and len(self.enemy_unit)==0

    def distance_to(self,pos) -> int:
        return self.get_centroid().distance_to(pos)

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

    def update(self,
               game_state,
               player: Player, opponent: Player,
               ):
        '''
        This is to update the cluster information.
        We update resource cells because resource cells are consumed.
        Some of its assigned units (workers) may die or leave.
        We update how much of its perimeter is not guarded by citytile.

        WARNING: Most bugs I had were caused by this function. Take care
        if you change this.
        '''
        resource_cells: List[Cell] = ResourceService \
            .get_resource_cells_by_positions(
            game_state,
            [cell.pos for cell in self.resource_cells]
        )

        self.resource_cells = resource_cells

        alive_units = [
            id for id in self.units if id in
                                       [u.id for u in player.units]
        ]
        self.units = alive_units

        perimeter: List[Position] = MapAnalysis.get_perimeter(
            resource_cells,
            game_state.map.width,
            game_state.map.height
        )

        exposed_perimeter = [
            p for p in perimeter
            if game_state.map.get_cell_by_pos(p).citytile is None and
               not game_state.map.get_cell_by_pos(p).has_resource()
        ]
        self.exposed_perimeter = exposed_perimeter

        # refresh units around this cluster
        self.units = []
        self.enemy_unit = []
        for r in self.resource_cells:
            for u in player.units:
                if r.pos.is_adjacent(u.pos):
                    print('XXXX', self.id, 'resource ', r.pos, 'close to unit ',u.id,u.pos, file=sys.stderr)
                    self.add_unit(u.id)
            for e in opponent.units:
                if r.pos.is_adjacent(e.pos):
                    self.add_enemy_unit(e.id)

        # if there are no units, store the unit id and distance to closest
        if len(self.units) == 0:
            self.closest_unit_distance = math.inf
            for r in self.resource_cells:
                for u in player.units:
                    dist = r.pos.distance_to(u.pos)
                    if dist < self.closest_unit_distance:
                        self.closest_unit_distance = dist
                        self.closest_unit = u.id
        else:
            self.closest_unit_distance = 0

        # if there are no enemy units, store the distance to closest enemy
        if len(self.enemy_unit) == 0:
            self.closest_enemy_distance = math.inf
            for r in self.resource_cells:
                for e in opponent.units:
                    dist = r.pos.distance_to(e.pos)
                    if dist < self.closest_enemy_distance:
                        self.closest_enemy_distance = dist
        else:
            self.closest_enemy_distance = 0
