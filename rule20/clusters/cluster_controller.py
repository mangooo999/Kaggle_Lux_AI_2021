import sys
from functools import cmp_to_key
from collections import defaultdict
from typing import List, DefaultDict
from lux.game_map import RESOURCE_TYPES, Position, Cell
from lux.game_objects import Unit, Player
import maps.map_analysis as MapAnalysis
from clusters.cluster import Cluster
import resources.resource_service as ResourceService
#import models.cluster_model as ClusterModel

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

        # creating wood clusters
        wood_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.WOOD
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(wood_resource_cells)):
            self.clusters[f'wood_{i}'] = Cluster(f'wood_{i}', rc,RESOURCE_TYPES.WOOD)

        # creating coal clusters
        coal_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.COAL
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(coal_resource_cells)):
            self.clusters[f'coal_{i}'] = Cluster(f'coal_{i}', rc,RESOURCE_TYPES.COAL)

        # creating uranium clusters
        uranium_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.URANIUM
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(uranium_resource_cells)):
            self.clusters[f'uranium_{i}'] = Cluster(f'uranium_{i}', rc,RESOURCE_TYPES.URANIUM)

    def get_clusters (self)->DefaultDict[str, Cluster]:
        return self.clusters.values()

    def update(self,game_state, player:Player, opponent:Player):
        for k in list(self.clusters.keys()):
            self.clusters[k] = self.update_cluster(
                self.clusters[k],
                game_state,
                player,opponent
            )
            if len(self.clusters[k].resource_cells)==0:
                print("T_" + str(game_state.turn),"cluster",k, "terminated", file=sys.stderr)
                del self.clusters[k]

    def update_cluster(self,
        cluster: Cluster,
        game_state,
        player:Player, opponent:Player,
    ) -> Cluster:
        '''
        This is to update the cluster information.
        We update resource cells because resource cells are consumed.
        Some of its assigned units (workers) may die or leave.
        We update how much of its perimeter is not guarded by citytile.

        WARNING: Most bugs I had were caused by this function. Take care
        if you change this.
        '''
        resource_cells: List[Cell] = ResourceService \
            .get_resource_cells_by_positions(
                game_state,
                [cell.pos for cell in cluster.resource_cells]
            )

        cluster.resource_cells = resource_cells

        alive_units = [
            id for id in cluster.units if id in
            [u.id for u in player.units]
        ]
        cluster.units = alive_units

        perimeter: List[Position] = MapAnalysis.get_perimeter(
            resource_cells,
            game_state.map.width,
            game_state.map.height
        )

        exposed_perimeter = [
            p for p in perimeter
            if game_state.map.get_cell_by_pos(p).citytile is None and
            not game_state.map.get_cell_by_pos(p).has_resource()
        ]
        cluster.exposed_perimeter = exposed_perimeter

        #refresh units around this cluster
        cluster.units = []
        cluster.enemy_unit = []
        for r in cluster.resource_cells:
            for u in player.units:
                if r.pos.is_adjacent(u.pos):
                    cluster.add_unit(u.id)
            for u in opponent.units:
                if r.pos.is_adjacent(u.pos):
                    cluster.add_enemy_unit(u.id)

        return cluster


    def get_units_without_clusters(self) -> List[Unit]:

        units_with_clusters = []
        for k in self.clusters:
            units_with_clusters.extend(self.clusters[k].units)

        units_without_clusters = []
        for unit in self.units:
            if unit.id not in units_with_clusters:
                units_without_clusters.append(unit)

        return units_without_clusters


# def get_citytiles_without_clusters(citytiles, clusters):
#     citytiles_with_cluster = []
#     for k in clusters:
#         citytiles_with_cluster.extend(clusters[k].citytiles)

#     citytiles_without_cluster = []
#     for citytile in citytiles:
#         if unit.id not in units_with_clusters:
#             units_without_clusters.append(unit)

#     return units_without_clusters
