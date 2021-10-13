import math
import sys
from typing import List, Tuple
from collections import defaultdict
from functools import cmp_to_key
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.game_objects import CityTile, DIRECTIONS, City


def find_neighbors(v, resource_cells):
    '''
    This function returns the 8 neighbors if exist, of a given cell.
    We need to check if the neighbor is in resource cells because
    we want to return only neigbor resource cells.
    '''
    pos = v['pos']
    neighbors = []

    # N, S, E, W, NE, NW, SE, SW
    n = pos.translate('n', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(n)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    s = pos.translate('s', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(s)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    e = pos.translate('e', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(e)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    w = pos.translate('w', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(w)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    ne = n.translate('e', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(ne)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    nw = n.translate('w', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(nw)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    se = s.translate('e', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(se)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    sw = s.translate('w', 1)
    neighbor = next(
        (tile for tile in resource_cells if tile['pos'].equals(sw)),
        None
    )
    if neighbor is not None:
        neighbors.append(neighbor)

    return neighbors


def dfs(nodes, v):
    '''
    Standard Depth First Search implementation.
    We use iterative DFS because it is easier to debug and
    it is more suitable for this case.
    '''
    group = []

    stack = []
    stack.append(v)

    while len(stack):
        v = stack[-1]
        stack.pop()

        if not v['visited']:
            v['visited'] = True
            group.append(v)

        neighbors = find_neighbors(v, nodes)

        for neighbor in neighbors:
            if not neighbor['visited']:
                stack.append(neighbor)

    return group


def get_resource_groups(resource_cells: List[Cell]):
    '''
    Use Depth First Search to find connected components of resource cells.
    '''
    nodes = []
    for resource_cell in resource_cells:
        nodes.append({
            'pos': resource_cell.pos,
            'visited': False,
            'tile': resource_cell
        })

    groups = []
    for node in nodes:
        if not node['visited']:
            group = dfs(nodes, node)
            group = list(map(lambda x: x['tile'], group))
            groups.append(group)

    return groups


def get_perimeter(
        cells: List[Cell],
        width: int,
        height: int
) -> List[Position]:
    '''
    For all the given cells, this returns unique perimeter.
    Perimeter means 4 adjacent cells' positions. North, South, East, West.
    '''
    perimeter_dict = defaultdict()

    for tile in cells:
        n = tile.pos.translate('n', 1)
        s = tile.pos.translate('s', 1)
        e = tile.pos.translate('e', 1)
        w = tile.pos.translate('w', 1)

        sides = [n, s, e, w]

        for side in sides:
            side_tile = next(
                (t for t in cells if t.pos.equals(side)),
                None
            )

            if side_tile is None:
                if (side.x >= 0 and side.x < width) and \
                        (side.y >= 0 and side.y < height):
                    perimeter_dict[str(side.x) + str(side.y)] = side

    return list(perimeter_dict.values())


def get_full_perimeter(
        cells: List[Cell],
        width: int,
        height: int
) -> List[Position]:
    perimeter_dict = defaultdict()

    for tile in cells:
        n = tile.pos.translate('n', 1)
        s = tile.pos.translate('s', 1)
        e = tile.pos.translate('e', 1)
        w = tile.pos.translate('w', 1)
        ne = n.translate('e', 1)
        nw = n.translate('w', 1)
        se = s.translate('e', 1)
        sw = s.translate('w', 1)

        sides = [n, s, e, w, ne, nw, se, sw]

        for side in sides:
            side_tile = next(
                (t for t in cells if t.pos.equals(side)),
                None
            )

            if side_tile is None:
                if (side.x >= 0 and side.x < width) and \
                        (side.y >= 0 and side.y < height):
                    perimeter_dict[str(side.x) + str(side.y)] = side

    return list(perimeter_dict.values())


def sort_cells_by_distance(pos, cells: List[Cell]):
    def compare(cell1, cell2):
        nonlocal pos
        return pos.distance_to(cell1.pos) - pos.distance_to(cell2.pos)

    return sorted(cells, key=cmp_to_key(compare))


def get_closest_position(position: Position, positions: [Position]) -> (Position, int):
    closest_pos = None
    closest_distance = math.inf

    for pos in positions:
        distance = position.distance_to(pos)
        # print(' XXXX get_closest_position', pos, distance, file=sys.stderr)
        if distance < closest_distance:
            closest_distance = distance
            closest_pos = pos

    return closest_pos, closest_distance


def get_closest_position_cells(position: Position, cells: [Cell]) -> (Position, int):
    closest_pos = None
    closest_distance = math.inf

    for c in cells:
        distance = position.distance_to(c.pos)
        # print(' XXXX get_closest_position', pos, distance, file=sys.stderr)
        if distance < closest_distance:
            closest_distance = distance
            closest_pos = c.pos

    return closest_pos, closest_distance


def get_closest_to_positions(position: Position, positions: [Position]) -> (Position, int):
    closest_pos = None
    closest_distance = math.inf

    for pos in positions:
        distance = position.distance_to(pos)
        # print(' XXXX get_closest_position', pos, distance, file=sys.stderr)
        if distance < closest_distance:
            closest_distance = distance
            closest_pos = pos

    return closest_pos, closest_distance

def get_city_id_from_pos(pos, actor):
    for city in actor.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.equals(pos):
                return city.cityid

    return ''

def is_position_city(pos: Position,actor) -> bool:
    return get_city_id_from_pos(pos, actor) != ''

def get_units_around(actor, pos: Position, max_dist) -> int:
    num = 0
    for unit in actor.units:
        if pos.distance_to(unit.pos) <= max_dist:
            num += 1

    return num


def get_resources_around(resource_tiles: List[Cell], pos: Position, max_dist) -> List[Cell]:
    resources = []
    for r in resource_tiles:
        if pos.distance_to(r.pos) <= max_dist:
            resources.append(r)

    return resources


# snippet to find the all city tiles, cities distance and sort them.
def find_number_of_adjacent_city_tile(pos, player) -> (int, int):
    tup = find_adjacent_city_tile(pos, player)
    return len(tup[0]), len(tup[1])


def find_adjacent_city_tile(pos, player) -> ([Position], [City]):
    tiles = []
    cities = []
    for city in player.cities.values():
        is_city_near = False
        for citytiles in city.citytiles:
            if citytiles.pos.is_adjacent(pos):
                tiles.append(pos)
                is_city_near = True
        if is_city_near:
            cities.append(city)

    return tiles, cities


def find_all_adjacent_empty_tiles(game_state, pos) -> List[Position]:
    adjacent_positions = [Position(pos.x, pos.y + 1), Position(pos.x - 1, pos.y), Position(pos.x, pos.y - 1),
                          Position(pos.x + 1, pos.y)]
    empty_tiles = []
    for adjacent_position in adjacent_positions:
        if not is_position_valid(adjacent_position, game_state):
            continue
        try:
            if game_state.map.get_cell_by_pos(adjacent_position) is None:
                continue
            if not adjacent_position.is_adjacent(pos):
                # strangely the above return cell on the other side of the map
                continue
            if is_cell_empty(adjacent_position, game_state):
                empty_tiles.append(adjacent_position)
        except Exception:
            continue
    return empty_tiles


def is_direction_valid(position, direction, game_state) -> bool:
    next_pos = position.translate(direction, 1)
    return is_position_valid(next_pos, game_state)


def is_position_valid(position, game_state) -> bool:
    return not (position.x < 0 or position.y < 0 \
                or position.x >= game_state.map_width or position.y >= game_state.map_height)


def is_position_adjacent_city(player, pos, do_log=False) -> bool:
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.is_adjacent(pos):
                if do_log:
                    print(pos, "is_position_adjacent_city", city_tile.pos, file=sys.stderr)
                return True

    return False


def get_next3_directions(without_direction: DIRECTIONS) -> [DIRECTIONS]:
    directions: [DIRECTIONS] = get_4_directions()
    directions.remove(without_direction)
    return directions


def get_4_directions() -> [DIRECTIONS]:
    return [DIRECTIONS.SOUTH, DIRECTIONS.NORTH, DIRECTIONS.WEST, DIRECTIONS.EAST]


def get_4_positions(pos: Position, game_state) -> [Position]:
    positions = []
    for direction in get_4_directions():
        next_pos = pos.translate(direction, 1)
        if is_position_valid(next_pos, game_state):
            positions.append(next_pos)

    return positions


def get_12_positions(pos: Position, game_state) -> [Position]:
    positions = []
    for x in range(pos.x - 2, pos.x + 2):
        for y in range(pos.y - 2, pos.y + 3):
            next_pos = Position(x, y)
            if 0 < pos.distance_to(next_pos) <= 2:
                if is_position_valid(next_pos, game_state):
                    positions.append(next_pos)

    return positions


def directions_to(start_pos: 'Position', target_pos: 'Position') -> [DIRECTIONS]:
    """
    Return closest position to target_pos from this position
    """
    check_dirs = [
        DIRECTIONS.NORTH,
        DIRECTIONS.EAST,
        DIRECTIONS.SOUTH,
        DIRECTIONS.WEST,
    ]
    closest_dist = start_pos.distance_to(target_pos)
    closest_dirs = [DIRECTIONS.CENTER]
    for direction in check_dirs:
        newpos = start_pos.translate(direction, 1)
        dist = target_pos.distance_to(newpos)
        if dist < closest_dist:
            closest_dirs = [direction]
            closest_dist = dist
        elif dist == closest_dist:
            closest_dirs.append(direction)
            closest_dist = dist
    return closest_dirs

def directions_to_no_city(start_pos: 'Position', target_pos: 'Position', player) -> [DIRECTIONS]:
    """
    Return closest position to target_pos from this position, avoiding city tiles from player
    """
    check_dirs = directions_to(start_pos,target_pos)
    return_dirs = []

    for direction in check_dirs:
        newpos = start_pos.translate(direction, 1)
        if is_position_city(newpos,player):
            continue
        else:
            return_dirs.append(direction)

    return return_dirs

def direction_to_no_city(start_pos: 'Position', target_pos: 'Position', player) -> DIRECTIONS:
    """
    Return closest position to target_pos from this position, avoiding city tiles from player
    """
    check_dirs = directions_to(start_pos,target_pos)

    for direction in check_dirs:
        newpos = start_pos.translate(direction, 1)
        if is_position_city(newpos,player):
            continue
        else:
            return direction

    return DIRECTIONS.CENTER

def find_closest_city_tile(pos, player) -> CityTile:
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile


def find_closest_adjacent_enemy_city_tile(pos, opponent) -> CityTile:
    closest_city_tile = None
    if len(opponent.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in opponent.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile

    # and now one step back
    return closest_city_tile


# return dist of cities, autonomy
def adjacent_cities(player, pos: Position, dist=1) -> {City, Tuple[int, int, DIRECTIONS]}:
    cities = {}
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.distance_to(pos) <= dist:
                # pr(pos, "adjacent_cities", city_tile.pos)
                cities[city] = (
                    len(city.citytiles), city.get_autonomy_turns(), directions_to(pos, city_tile.pos)[0])

    return cities


def is_position_adjacent_to_resource(resource_tiles, pos) -> bool:
    return is_position_adjacent_to_resource_distance(resource_tiles,pos,1)

def is_position_adjacent_to_resource_distance(resource_tiles, pos: Position, distance) -> bool:
    for r in resource_tiles:
        if pos.distance_to(r.pos) <= distance:
            return True
    return False

def get_max_fuel_harvest_in_pos(resource_tiles: List[Cell], pos) -> int:
    fuel = 0
    for cell in resource_tiles:
        if cell.pos.is_adjacent(pos):
            if cell.resource.type == RESOURCE_TYPES.WOOD:
                fuel += 20
            elif cell.resource.type == RESOURCE_TYPES.COAL:
                fuel += 100
            elif cell.resource.type == RESOURCE_TYPES.URANIUM:
                fuel += 100
    return fuel


def is_position_resource(resource_tiles, pos) -> bool:
    for r in resource_tiles:
        if r.pos.equals(pos):
            return True
    return False


def is_position_in_X_adjacent_to_resource(resource_tiles, pos) -> (bool, bool):
    adjacent = False
    for r in resource_tiles:
        if r.pos.equals(pos):
            return (True, True)  # if equal is also adjacent!
        if r.pos.is_adjacent(pos):
            adjacent = True

    return (False, adjacent)


def is_cell_empty(pos, game_state) -> bool:
    cell = game_state.map.get_cell(pos.x, pos.y)
    result = (not cell.has_resource()) and cell.citytile is None;
    # print("- ", pos, 'empty',result, file=sys.stderr)
    return result


def is_cell_empty_or_empty_next(pos, game_state) -> (bool, bool):
    is_empty = is_cell_empty(pos, game_state)
    has_empty_next = len(find_all_adjacent_empty_tiles(game_state, pos)) > 0
    return is_empty, has_empty_next



