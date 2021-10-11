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
from lux.game_objects import Player, CityTile
from UnitInfo import UnitInfo


class Cluster:
    def __init__(self, id: str, resource_cells: List[Cell], resource_type: RESOURCE_TYPES):
        self.id: str = id
        self.resource_cells: List[Cell] = resource_cells
        self.units: List[str] = []
        self.incoming_explorers: List[str] = []
        self.city_tiles: List[CityTile] = []
        self.enemy_unit: List[str] = []
        self.perimeter: List[Position] = []
        self.exposed_perimeter: List[Position] = [] # empty (no resources, no city)
        self.accessible_perimeter: List[Position] = [] # no enemy city
        self.walkable_perimeter: List[Position] = [] # no enemy city, no enemy units
        self.res_type: RESOURCE_TYPES = resource_type
        self.closest_unit = ''
        self.closest_unit_distance = math.inf
        self.closest_enemy_distance = math.inf
        self.score = 0.

    def refresh_score(self) -> int:
        self.score = -(
                + float(len(self.resource_cells)) / 10.
               - float(len(self.incoming_explorers) ) * 3
               - float(len(self.enemy_unit)) * 1.
               )



    def add_unit(self, unit_id: str):
        if unit_id not in self.units:
            self.units.append(unit_id)

    def add_incoming_explorer(self, unit_id: str):
        if unit_id not in self.incoming_explorers:
            self.incoming_explorers.append(unit_id)

    def add_city_tile(self, ct: CityTile):
        if ct not in self.city_tiles:
            self.city_tiles.append(ct)

    def add_enemy_unit(self, unit_id: str):
        if unit_id not in self.enemy_unit:
            self.enemy_unit.append(unit_id)

    def to_string_light(self) -> str:
        return "{0} {1} r={2} f={3} u={4} iu={10} c={5} e={6} ed={7} pl={8} pw={9} sc={11:1.2f}".format(self.id,
                                                                                    self.get_centroid(),
                                                                                    len(self.resource_cells),
                                                                                    self.get_available_fuel(),
                                                                                    len(self.units),
                                                                                    len(self.city_tiles),
                                                                                    len(self.enemy_unit),
                                                                                    self.closest_enemy_distance,
                                                                                    len(self.accessible_perimeter),
                                                                                    len(self.walkable_perimeter),
                                                                                    len(self.incoming_explorers),
                                                                                    self.score
                                                                                    )

    def is_more_units_than_res(self) -> bool:
        return len(self.units) > len(self.resource_cells)

    def has_eq_gr_units_than_res(self) -> bool:
        return len(self.units) >= len(self.resource_cells)

    def has_eq_gr_units_than_fuel(self) -> bool:
        return len(self.units) >= self.get_available_fuel()/500.

    def is_overcrowded(self) -> bool:
        equivalent_units = self.get_equivalent_units()
        equivalent_resources = self.get_equivalent_resources()
        return equivalent_units >= equivalent_resources

    def get_equivalent_units(self) -> int:
        u = len(self.units)
        ct = len(self.city_tiles)
        return min(max(u, ct), u + 2)  # logic is that if units<ct, we can spawn units

    def get_equivalent_resources(self) -> int:
        return min(len(self.resource_cells), int(float(self.get_available_fuel()) / 500.))

    def has_no_units(self) -> bool:
        return len(self.units) == 0

    def has_no_enemy(self) -> bool:
        return len(self.enemy_unit) == 0

    def has_no_units_no_enemy(self) -> bool:
        return self.has_no_units() and self.has_no_enemy()

    def num_units(self) -> int:
        return len(self.units)

    def distance_to(self, pos) -> int:
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

    def get_closest_distance_to_perimeter(self, pos: Position) -> (Position, int):
        return MapAnalysis.get_closest_position(
            pos,
            self.exposed_perimeter
        )

    def update(self,
               game_state,
               player: Player, opponent: Player, unit_info: DefaultDict[str, UnitInfo]
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

        perimeter: List[Position] = MapAnalysis.get_perimeter(
            resource_cells,
            game_state.map.width,
            game_state.map.height
        )
        self.perimeter = perimeter

        exposed_perimeter = [
            p for p in self.perimeter
            if game_state.map.get_cell_by_pos(p).citytile is None and
               not game_state.map.get_cell_by_pos(p).has_resource()
        ]
        self.exposed_perimeter = exposed_perimeter

        accessible_perimeter = []
        for p in self.perimeter:
            city_tile = game_state.map.get_cell_by_pos(p).citytile
            if city_tile is None:
                # no city
                # todo maybe exclude occupied enemy tiles
                accessible_perimeter.append(p)
            elif MapAnalysis.get_city_id_from_pos(p, player) != '':
                # our city
                accessible_perimeter.append(p)

        self.accessible_perimeter = accessible_perimeter

        accessible_perimeter_now = []
        for p in self.accessible_perimeter:
            add = True
            for e in opponent.units:
                if p.equals(e.pos):
                    add = False
                    break
            if add:
                accessible_perimeter_now.append(p)

        self.walkable_perimeter = accessible_perimeter_now

    def update_closest(self, player: Player, opponent: Player):

        # refresh units around this cluster

        self.enemy_unit = []
        self.closest_enemy_distance = math.inf
        for r in self.resource_cells:
            # friendly units are added in the controller

            # add enemy units if they are closer than 2 from any resource cell
            for e in opponent.units:
                dist = r.pos.distance_to(e.pos)

                # store the closest anyway
                if dist < self.closest_enemy_distance:
                    self.closest_enemy_distance = dist

                # incrememnt the counter for enemy within 2 of range
                if dist <= 2:
                    self.add_enemy_unit(e.id)

        # if there are no units, store the unit id and distance to closest
        self.closest_unit = ''
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

    def is_reachable(self) -> bool:
        return len(self.accessible_perimeter) > 0
