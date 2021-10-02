import collections
import math
from typing import List, Tuple, Dict
from lux.game_map import Cell, Position, RESOURCE_TYPES
from GameInfo import GameInfo

from lux.game_objects import CityTile, DIRECTIONS


def get_resources(game_state) -> List[Cell]:
    '''
    Get all resource cells in the game map.
    '''
    resource_cells = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_cells.append(cell)
    return resource_cells


def get_minable_resource_cells(
    player,
    resource_cells: List[Cell]
) -> List[Cell]:
    '''
    Get resource cells that can be mined by the player.
    '''
    minable_resource_types = [RESOURCE_TYPES.WOOD]
    if player.researched_coal():
        minable_resource_types.append(RESOURCE_TYPES.COAL)
    if player.researched_uranium():
        minable_resource_types.append(RESOURCE_TYPES.URANIUM)

    minable_resource_cells = [
        resource_cell for resource_cell in resource_cells
        if resource_cell.resource.type in minable_resource_types
    ]
    return minable_resource_cells


def get_closest_resource_tile(pos, resource_tiles):
    closest_distance = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_distance:
            closest_distance = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile, closest_distance


def get_resource_cells_by_positions(
    game_state,
    positions: List[Position]
) -> List[Cell]:
    '''
    Returns all the resource cells in given positions
    '''

    resource_cells = []

    for pos in positions:
        cell = game_state.map.get_cell_by_pos(pos)
        if cell.has_resource():
            resource_cells.append(cell)

    return resource_cells


def find_all_resources(game_state, player) -> (List[Cell], List[Cell], List[Cell]):
    resource_tiles_all: List[Cell] = []
    resource_tiles_available: List[Cell] = []
    wood_tiles: List[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles_all.append(cell)
                if cell.resource.type == RESOURCE_TYPES.WOOD:
                    wood_tiles.append(cell)
                    resource_tiles_available.append(cell)
                if (cell.resource.type == RESOURCE_TYPES.COAL and player.researched_coal()) \
                        or (cell.resource.type == RESOURCE_TYPES.URANIUM and player.researched_uranium()):
                    resource_tiles_available.append(cell)

    return resource_tiles_all, resource_tiles_available, wood_tiles


# the next snippet all resources distance and return as sorted order.
def find_resources_distance(pos, player, resource_tiles, game_info: GameInfo) -> Dict[CityTile,
                                                                                      Tuple[int, int, DIRECTIONS]]:
    resources_distance = {}
    for resource_tile in resource_tiles:

        dist = resource_tile.pos.distance_to(pos)

        if resource_tile.resource.type == RESOURCE_TYPES.WOOD:
            resources_distance[resource_tile] = (dist, -resource_tile.resource.amount, resource_tile.resource.type)
        else:
            expected_resource_additional = (float(dist * 2.0) * float(game_info.get_research_rate(5)))
            expected_resource_at_distance = float(game_info.reseach_points) + expected_resource_additional
            # check if we are likely to have researched this by the time we arrive
            if resource_tile.resource.type == RESOURCE_TYPES.COAL and \
                    expected_resource_at_distance < 50.0:
                continue
            elif resource_tile.resource.type == RESOURCE_TYPES.URANIUM and \
                    expected_resource_at_distance < 200.0:
                continue
            else:
                # order by distance asc, resource asc
                resources_distance[resource_tile] = (dist, -resource_tile.resource.amount, resource_tile.resource.type)

    resources_distance = collections.OrderedDict(sorted(resources_distance.items(), key=lambda x: x[1]))
    return resources_distance

def is_position_adjacent_to_resource(resource_tiles, pos) -> bool:
    for r in resource_tiles:
        if r.pos.is_adjacent(pos):
            return True
    return False


def is_position_resource(resource_tiles, pos) -> bool:
    for r in resource_tiles:
        if r.pos.equals(pos):
            return True
    return False

