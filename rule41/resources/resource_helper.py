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
    total_fuel = 0
    available_fuel = 0
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles_all.append(cell)
                if cell.resource.type == RESOURCE_TYPES.WOOD:
                    wood_tiles.append(cell)
                    resource_tiles_available.append(cell)
                    total_fuel += cell.resource.amount
                    available_fuel += cell.resource.amount
                if cell.resource.type == RESOURCE_TYPES.COAL:
                    total_fuel += cell.resource.amount * 10
                    if player.researched_coal():
                        resource_tiles_available.append(cell)
                        available_fuel += cell.resource.amount * 10

                if cell.resource.type == RESOURCE_TYPES.URANIUM:
                    total_fuel += cell.resource.amount * 40
                    if player.researched_uranium():
                        resource_tiles_available.append(cell)
                        available_fuel += cell.resource.amount * 40

    return resource_tiles_all, resource_tiles_available, wood_tiles, total_fuel, available_fuel





