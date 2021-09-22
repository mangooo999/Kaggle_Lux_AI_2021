import math, random, types, copy
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


def create_empty_maze(x, y):
    return types.SimpleNamespace(
        board=CellGrid([[Cell(type=CellType.Empty, pos=[ix, iy]) for iy in range(y)] for ix in range(x)]),
        start=[random.randrange(0, x), random.randrange(0, y)],
        end=[random.randrange(0, x), random.randrange(0, y)])


def create_wall_maze(width, height):
    board = [[Cell(type=CellType.Empty, pos=[ix, iy]) for iy in range(height)] for ix in range(width)]
    for i in range(0, width):
        board[i][int(height / 2)].type = CellType.Block
    for i in range(0, height):
        board[int(width / 2)][i].type = CellType.Block

    board[random.randint(0, width / 2 - 1)][int(height / 2)].type = CellType.Empty
    board[random.randint(width / 2 + 1, width - 1)][int(height / 2)].type = CellType.Empty
    board[int(width / 2)][random.randint(0, height / 2 - 1)].type = CellType.Empty
    board[int(width / 2)][random.randint(height / 2 + 1, height - 1)].type = CellType.Empty

    return types.SimpleNamespace(board=CellGrid(board),
                                 start=Position(random.randrange(0, width / 2), random.randrange(height / 2 + 1, height)),
                                 end=Position(random.randrange(width / 2 + 1, width), random.randrange(0, height / 2)))


def add_points(a: Position, b: Position)->Position:
    return Position(a.x + b.x, a.y + b.y)
