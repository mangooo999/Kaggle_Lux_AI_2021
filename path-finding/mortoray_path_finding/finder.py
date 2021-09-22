from . import maze
import math


def fill_shortest_path(board, start, end, max_distance=math.inf):
    """ Creates a duplicate of the board and fills the `Cell.count` field with the distance from the start to that cell. """

    # The algorithm implemented in the function is called fill_shortest_path. It's helpful to have that code open
    # while reading this explanation. This function doesn't directly find the shortest path, but rather, measures the
    # distance from a starting location to other cells in the maze. We'll see how this information is used to generate
    # the path later.

    nboard = board.clone()
    nboard.clear_count(math.inf)

    # mark the start and end for the UI
    nboard.at(start).mark = maze.CellMark.Start
    nboard.at(end).mark = maze.CellMark.End

    # The "open node list" is a vector of positions in the grid. It contains all the locations we need to search for
    # a path. We’ll initialize the list with the maze's starting location. We’ll also set the count to 0,
    # since the start is a distance of zero.

    # we start here, thus a distance of 0
    open_list = [start]
    nboard.at(start).count = 0

    # (x,y) offsets from current cell
    neighbours = [[-1, 0], [1, 0], [0, -1], [0, 1]]

    # We loop until the open_list is empty.
    while open_list:
        cur_pos = open_list.pop(0)
        cur_cell = nboard.at(cur_pos)

        for neighbour in neighbours:
            next_pos = maze.add_points(cur_pos, neighbour)

            # We must take the edges of the grid into consideration though, which is what is_valid_point does. For
            # example, if we’re at the right edge of the grid, then the offset [1,0], which moves one to the right,
            # is no longer on the graph, so we’ll skip that.
            if not nboard.is_valid_point(next_pos):
                continue
            # We’ll also skip any cells that isn’t empty, as these are the walls in the maze and we can't walk through them
            cell = nboard.at(next_pos)

            if cell.type != maze.CellType.Empty:
                continue

            dist = cur_cell.count + 1
            if dist > max_distance:
                continue
            # If this distance is less than the one from its neighbor, we’ll update the neighbor and add it to the open list.
            if cell.count > dist:
                cell.count = dist
                cell.path_from = cur_cell
                open_list.append(next_pos)

    return nboard


def backtrack_to_start(board, end):
    """ Returns the path to the end, assuming the board has been filled in via fill_shortest_path """
    cell = board.at(end)
    path = []
    while cell != None:
        path.append(cell)
        cell = cell.path_from

    print('***backtrack_to_start', path)
    if len(path)>1:
        print('*** first direction',path[-2].path_from)
    return path
