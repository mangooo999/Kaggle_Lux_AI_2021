
from typing import List, Set, Tuple

from .constants import Constants
from .game_objects import CityTile, Unit
from .game_position import Position

RESOURCE_TYPES = Constants.RESOURCE_TYPES


class Resource:
    def __init__(self, r_type: str, amount: int):
        self.type = r_type
        self.amount = amount


class Cell:
    def __init__(self, x, y):
        self.pos = Position(x, y)
        self.resource: Resource = None
        self.citytile: CityTile = None
        self.unit: Unit = None
        self.road = 0
        self.x = x
        self.y = y

    def has_resource(self):
        return self.resource is not None and self.resource.amount > 0

    def __repr__(self):
        return f"Cell({self.x},{self.y})"

    def distance_to(self, pos: 'Position') -> int:
        """
        Returns Manhattan (L1/grid) distance to pos
        """
        return self.pos.distance_to(pos)

    def distance_to_mult(self, positions: '[Position]') -> int:
        """
        Returns Manhattan (L1/grid) distance to multiple pos
        """
        return self.pos.distance_to_mult(positions)


class GameMap:
    def __init__(self, width, height):
        self.height = height
        self.width = width
        self.map: List[List[Cell]] = [None] * height
        for y in range(0, self.height):
            self.map[y] = [None] * width
            for x in range(0, self.width):
                self.map[y][x] = Cell(x, y)

    def get_cell_by_pos(self, pos) -> Cell:
        return self.map[pos.y][pos.x]

    def get_cell(self, x, y) -> Cell:
        return self.map[y][x]

    def _setResource(self, r_type, x, y, amount):
        """
        do not use this function, this is for internal tracking of state
        """
        cell = self.get_cell(x, y)
        cell.resource = Resource(r_type, amount)
