class ConfigManager():
    def __init__(self, map_size: int, pr):
        self.cluster_wood_overcrowded = 5
        self.distance_wood_coal_to_move_building = 2
        self.super_fast_expansion = False
        self.do_cluster_analyses = True
        self.spread_big_cluster = False

        # ML Parameters
        self.ML_model = 'model3'
        self.ML_model_map_size = 32
        self.ML_model_type = 2

        self.ml_find_resources = True
        self.ml_can_build = False
        self.ml_fallback = False
        self.num_resource_below_no_ML = map_size / 2
        self.ML_number_of_turns_include_resources_coal = 25
        self.ML_number_of_turns_include_resources_uranium = 30
        self.RULEM = False


        pr("ConfigManager,map size{0}".format(map_size))
        if map_size == 12:
            self.cluster_wood_overcrowded = 3
            if self.ml_find_resources:
                self.do_cluster_analyses = False

        elif map_size == 16:
            self.spread_big_cluster = True
            self.cluster_wood_overcrowded = 3
            if self.ml_find_resources:
                self.do_cluster_analyses = False

        elif map_size == 24:
            self.cluster_wood_overcrowded = 3

        elif map_size == 32:
            self.spread_big_cluster = True        
            self.cluster_wood_overcrowded = 5

        else:
            pr("ConfigManager, invalid map size", map_size, f=True)
            raise NameError('ConfigManager, invalid map size ' + str(map_size))

        self.print_attribute_per_line(pr,"ConfigManager:")

    def __str__(self):
        return ','.join("%s: %s" % item for item in vars(self).items())

    def print_attribute_per_line(self,pr, prefix):
        for item in vars(self).items():
            pr(prefix, item[0], '=', item[1])
