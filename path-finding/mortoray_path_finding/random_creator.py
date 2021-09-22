import random
from .maze import *


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