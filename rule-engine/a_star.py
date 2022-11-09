import numpy as np
from queue import PriorityQueue
import copy

from lux.game_position import Position


def is_valid(mat, row, col):
    M, N = mat.shape
    return (row >= 0) and (row < M) and (col >= 0) and (col < N) \
        and mat[row][col] == 0


def manhattan_distance(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)


def a_star(pr, s:Position, e:Position, walls, size):

    start = (s.x, s.y)
    end = (e.x, e.y)
    mat = np.zeros((size, size))
    for i in walls:
        mat[i] = 1

    pr(mat)

    # explore 4 neighbors
    row = [-1, 0, 0, 1]
    col = [0, -1, 1, 0]

    q = PriorityQueue()
    count = 0
    q.put((0, count, start))
    g_score = {}
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            g_score[(i, j)] = float('inf')

    f_score = copy.deepcopy(g_score)
    g_score[start] = 0
    f_score[start] = manhattan_distance(*start, *end)
    q_hash = {start}
    came_from = {}
    while not q.empty():
        current = q.get()[2]
        q_hash.remove(current)

        for k in range(4):
            coordinate = (current[0] + row[k], current[1] + col[k])

            if is_valid(mat, *coordinate):
                temp_g_score = g_score[current] + 1
                if temp_g_score < g_score[coordinate]:
                    came_from[coordinate] = current
                    g_score[coordinate] = temp_g_score
                    f_score[coordinate] = temp_g_score + manhattan_distance(*coordinate, *end)
                    if coordinate not in q_hash:
                        count += 1
                        q_hash.add(coordinate)
                        q.put((f_score[coordinate], count, coordinate))
                        pr('*', *coordinate)

        if current == end:
            count = 0
            pr('@', *end)
            while current in came_from:
                current = came_from[current]
                pr('+', *current)
                count += 1
            pr('@', *start)
            pr("The shortest path from source to destination has length",count)
            break
    pr("Destination can't be reached from a given source")





