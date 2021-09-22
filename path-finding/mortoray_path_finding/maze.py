import random, types, copy
from enum import Enum

from lux.game_map import Position


class CellType(Enum):
    Empty = 1
    Block = 2

class CellMark(Enum):
    No = 0
    Start = 1
    End = 2


class Cell:
    def __init__(self, type=CellType.Empty, pos=None):
        self.type = type
        self.count = 0
        self.mark = CellMark.No
        self.path_from = None
        self.pos = pos

    def __repr__(self):
        return self.pos.__str__()


class CellGrid:
    def __init__(self, board):
        self.board = board

    def get_size(self):
        return [len(self.board), len(self.board[0])]

    def at(self, pos:Position):
        return self.board[pos.x][pos.y]

    def clone(self):
        return CellGrid(copy.deepcopy(self.board))

    def clear_count(self, count):
        for o in self.board:
            for i in o:
                i.count = count
                i.path_from = None

    def is_valid_point(self, pos:Position):
        sz = self.get_size()
        return pos.x >= 0 and pos.y >= 0 and pos.x < sz[0] and pos.y < sz[1]

def add_points(a: Position, b: Position)->Position:
    return Position(a.x + b.x, a.y + b.y)

