class ConfigManager():
    def __init__(self, map_size: int, pr):
        self.cluster_wood_overcrowded = 5
        self.distance_wood_coal_to_move_building = 2
        self.super_fast_expansion = False
        self.ml_find_resources = True

        pr("ConfigManager,map size{0}".format(map_size))
        if map_size == 12:
            self.cluster_wood_overcrowded = 3
        elif map_size == 16:
            self.cluster_wood_overcrowded = 3
        elif map_size == 24:
            self.cluster_wood_overcrowded = 3
        elif map_size == 32:
            self.cluster_wood_overcrowded = 5
        else:
            pr("ConfigManager, invalid map size", map_size, f=True)
            raise NameError('ConfigManager, invalid map size ' + str(map_size))
