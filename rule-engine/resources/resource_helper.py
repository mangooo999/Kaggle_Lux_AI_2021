import collections
import math
from typing import List
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.game_objects import Cargo, CityTile, DIRECTIONS


class Resources:
    def __init__(self, game_state, player):

        width, height = game_state.map_width, game_state.map_height

        self.all_resources_tiles: List[Cell] = []
        self.available_resources_tiles: List[Cell] = []
        self.wood_tiles: List[Cell] = []
        self.coal_tiles: List[Cell] = []
        self.uranium_tiles: List[Cell] = []
        self.total_fuel = 0
        self.available_fuel = 0
        self.cargo = Cargo()
        for y in range(height):
            for x in range(width):
                cell = game_state.map.get_cell(x, y)
                if cell.has_resource():
                    self.all_resources_tiles.append(cell)
                    if cell.resource.type == RESOURCE_TYPES.WOOD:
                        self.wood_tiles.append(cell)
                        self.cargo.wood += cell.resource.amount
                        self.total_fuel += cell.resource.amount
                        self.available_resources_tiles.append(cell)
                        self.available_fuel += cell.resource.amount
                    elif cell.resource.type == RESOURCE_TYPES.COAL:
                        self.coal_tiles.append(cell)
                        self.cargo.coal += cell.resource.amount
                        self.total_fuel += cell.resource.amount * 10
                        if player.researched_coal():
                            self.available_resources_tiles.append(cell)
                            self.available_fuel += cell.resource.amount * 10
                    elif cell.resource.type == RESOURCE_TYPES.URANIUM:
                        self.uranium_tiles.append(cell)
                        self.cargo.uranium += cell.resource.amount
                        self.total_fuel += cell.resource.amount * 40
                        if player.researched_uranium():
                            self.available_resources_tiles.append(cell)
                            self.available_fuel += cell.resource.amount * 40


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








