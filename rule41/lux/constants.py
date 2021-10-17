import random
random.seed(50)

class Constants:
    class INPUT_CONSTANTS:
        RESEARCH_POINTS = "rp"
        RESOURCES = "r"
        UNITS = "u"
        CITY = "c"
        CITY_TILES = "ct"
        ROADS = "ccd"
        DONE = "D_DONE"
    class DIRECTIONS:
        NORTH = "n"
        WEST = "w"
        SOUTH = "s"
        EAST = "e"
        CENTER = "c"

        def opposite(dir: 'DIRECTIONS') -> 'DIRECTIONS':
            if dir == Constants.DIRECTIONS.NORTH:
                return Constants.DIRECTIONS.SOUTH
            elif dir == Constants.DIRECTIONS.SOUTH:
                return Constants.DIRECTIONS.NORTH
            elif dir == Constants.DIRECTIONS.WEST:
                return Constants.DIRECTIONS.EAST
            elif dir == Constants.DIRECTIONS.EAST:
                return Constants.DIRECTIONS.WEST
            else:
                return Constants.DIRECTIONS.CENTER

        def get_random_directions() -> '[DIRECTIONS]':
            random_sequence = random.choice([0, 1, 2, 3])
            # randomly choose which sequence to start with, so not to have a rotational probailistic skew
            if random_sequence == 0:
                return [Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.WEST, Constants.DIRECTIONS.EAST]
            elif random_sequence == 1:
                return [Constants.DIRECTIONS.EAST, Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.WEST]
            elif random_sequence == 2:
                return [Constants.DIRECTIONS.WEST, Constants.DIRECTIONS.EAST, Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.NORTH]
            else:
                return [Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.WEST, Constants.DIRECTIONS.EAST, Constants.DIRECTIONS.SOUTH]

    class UNIT_TYPES:
        WORKER = 0
        CART = 1
    class RESOURCE_TYPES:
        WOOD = "wood"
        URANIUM = "uranium"
        COAL = "coal"
