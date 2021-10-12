

class ConfigManager():
    def __init__(self, map_size:int,pr):
        self.cluster_wood_overcrowded = 5

        if map_size==12:
            pr("ConfigManager,map size",map_size)
        elif map_size==16:
            pr("ConfigManager,map size", map_size)
        elif map_size == 24:
            pr("ConfigManager,map size", map_size)
        elif map_size == 32:
            pr("ConfigManager,map size", map_size)
        else:
            pr("ConfigManager, invalid map size", map_size)
            raise NameError('ConfigManager, invalid map size'+ str(map_size))

