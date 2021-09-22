from . import maze
import math


def fill_shortest_path(board, start: maze.Position, end: maze.Position, max_distance=math.inf):
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

    manhattan_distance = start.distance_to(end)

    directions = get_manattham_direction(end, start)

    manattham_result = get_distance_array(manhattan_distance, nboard, directions, start, end, True)
    if manattham_result[1]:
        print('found as manhattan')
        return manattham_result
    else:
        print('not found as manhattan, searching large using max_distance', max_distance)
        directions = [maze.Position(-1, 0), maze.Position(1, 0), maze.Position(0, -1), maze.Position(0, 1)]
        return get_distance_array(max_distance, nboard, directions, start, end, False)


def get_manattham_direction(end, start):
    directions = []
    # (x,y) offsets from current cell
    if end.x > start.x:
        directions.append(maze.Position(1, 0))
    elif end.x < start.x:
        directions.append(maze.Position(-1, 0))
    if end.y > start.y:
        directions.append(maze.Position(0, 1))
    elif end.y < start.y:
        directions.append(maze.Position(0, -1))
    return directions


def get_distance_array(max_distance, input_board, neighbours, start: maze.Position, end: maze.Position, walk_only_manattham):
    # The "open node list" is a vector of positions in the grid. It contains all the locations we need to search for
    # a path. We’ll initialize the list with the maze's starting location. We’ll also set the count to 0,
    # since the start is a distance of zero.
    return_board = input_board.clone()

    # we start here, thus a distance of 0
    open_list = [start]
    return_board.at(start).count = 0
    # we count number of steps so we have an idea of how much complexity
    performed_steps = 0
    found = False
    found_distance = None
    # We loop until the open_list is empty.
    while open_list:
        performed_steps += 1
        cur_pos = open_list.pop(0)
        cur_cell = return_board.at(cur_pos)

        for direction in neighbours:
            next_pos = maze.add_points(cur_pos, direction)
            dist = cur_cell.count + 1
            print(' - ', cur_pos, next_pos, dist)
            # We must take the edges of the grid into consideration though, which is what is_valid_point does. For
            # example, if we’re at the right edge of the grid, then the offset [1,0], which moves one to the right,
            # is no longer on the graph, so we’ll skip that.
            if not return_board.is_valid_point(next_pos):
                continue

            # if we are walking only manattham, then we cannot get out the rectangle identified by start and end
            if walk_only_manattham:
                if next_pos.x < min(start.x, end.x) or next_pos.x > max(start.x, end.x) \
                    or next_pos.y < min(start.y, end.y) or next_pos.y > max(start.y, end.y):
                    continue

            # We’ll also skip any cells that isn’t empty, as these are the walls in the maze and we can't walk through them
            cell: maze.Cell = return_board.at(next_pos)

            if cell.type != maze.CellType.Empty:
                continue

            if dist > max_distance:
                continue

            # If this distance is eq or more than the one from its neighbor, then it is not a good solution
            if dist >= cell.count:
                continue

            # If this distance is more than an already found path, abort
            if found_distance is not None and dist >= found_distance:
                continue

            # If this distance is less than the one from its neighbor, we’ll update the neighbor and add it to the open list.
            cell.count = dist
            cell.path_from = cur_cell
            open_list.append(next_pos)

            # if we reached the end, then flag it
            if next_pos.equals(end):
                found = True
                found_distance = dist
                print('Got it! at distance ', found_distance)
                if walk_only_manattham:
                    break

    print('found', found,' at distance ',found_distance)
    print('performed_steps', performed_steps)
    return return_board, found, found_distance


def backtrack_to_start(board, end):
    """ Returns the path to the end, assuming the board has been filled in via fill_shortest_path """
    cell = board.at(end)
    path = []
    while cell != None:
        path.append(cell)
        cell = cell.path_from

    print('***backtrack_to_start', path)
    if len(path) > 1:
        print('*** first direction', path[-2].path_from)
    return path
