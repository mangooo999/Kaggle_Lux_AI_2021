import random, types, copy
from enum import Enum

class CellType(Enum):
    Empty = 1
    Block = 2

class CellMark(Enum):
    No = 0
    Start = 1
    End = 2

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __sub__(self, pos) -> int:
        return abs(pos.x - self.x) + abs(pos.y - self.y)

    def distance_to(self, pos):
        """
        Returns Manhattan (L1/grid) distance to pos
        """
        return self - pos

    def is_adjacent(self, pos):
        return (self - pos) <= 1

    def __eq__(self, pos) -> bool:
        return self.x == pos.x and self.y == pos.y

    def equals(self, pos):
        return self == pos

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def get_from_me(self, b) :
        return Position(self.x + b.x, self.y + b.y)

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



