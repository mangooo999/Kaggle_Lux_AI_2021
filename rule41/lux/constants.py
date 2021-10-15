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

    class UNIT_TYPES:
        WORKER = 0
        CART = 1
    class RESOURCE_TYPES:
        WOOD = "wood"
        URANIUM = "uranium"
        COAL = "coal"
