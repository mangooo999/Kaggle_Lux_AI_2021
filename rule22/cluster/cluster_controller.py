import sys
from functools import cmp_to_key
from collections import defaultdict
from typing import List, DefaultDict, ValuesView
from lux.game_map import RESOURCE_TYPES, Position, Cell
from lux.game_objects import Unit, Player
import maps.map_analysis as MapAnalysis
from .cluster import Cluster
import resources.resource_helper as ResourceService
from UnitInfo import UnitInfo


class ClusterControl:
    def __init__(self, game_state):
        '''
        This is called only once, when the game starts.
        The cluster types are wood, coal, and uranium.
        If two resource cells are adjacent, or diagonal to each other,
        we assume they are in the same cluster.
        '''
        self.clusters: DefaultDict[str, Cluster] = defaultdict(Cluster)

        resource_cells = ResourceService.get_resources(game_state)

        # creating wood cluster
        wood_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.WOOD
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(wood_resource_cells)):
            self.clusters[f'wood_{i}'] = Cluster(f'wood_{i}', rc,RESOURCE_TYPES.WOOD)

        # creating coal cluster
        coal_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.COAL
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(coal_resource_cells)):
            self.clusters[f'coal_{i}'] = Cluster(f'coal_{i}', rc,RESOURCE_TYPES.COAL)

        # creating uranium cluster
        uranium_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.URANIUM
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(uranium_resource_cells)):
            self.clusters[f'uranium_{i}'] = Cluster(f'uranium_{i}', rc,RESOURCE_TYPES.URANIUM)

    def get_clusters (self)-> ValuesView[Cluster]:
        return self.clusters.values()

    def get_cluster_from_centroid(self,pos:Position)-> Cluster:
        for k in self.clusters.values():
            if k.get_centroid() == pos:
                return k

        return None

    def update(self,game_state, player:Player, opponent:Player,unit_info : DefaultDict[str, UnitInfo]):
        for k in list(self.clusters.keys()):
            self.clusters[k].update(
                game_state,
                player,opponent,unit_info
            )
            if len(self.clusters[k].resource_cells)==0:
                print("T_" + str(game_state.turn),"cluster",k, "terminated", file=sys.stderr)
                del self.clusters[k]




    def get_units_without_clusters(self) -> List[Unit]:

        units_with_clusters = []
        for k in self.clusters:
            units_with_clusters.extend(self.clusters[k].units)

        units_without_clusters = []
        for unit in self.units:
            if unit.id not in units_with_clusters:
                units_without_clusters.append(unit)

        return units_without_clusters


# def get_citytiles_without_clusters(citytiles, cluster):
#     citytiles_with_cluster = []
#     for k in cluster:
#         citytiles_with_cluster.extend(cluster[k].citytiles)

#     citytiles_without_cluster = []
#     for citytile in citytiles:
#         if unit.id not in units_with_clusters:
#             units_without_clusters.append(unit)

#     return units_without_clusters
