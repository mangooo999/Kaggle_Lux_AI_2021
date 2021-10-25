import math
import sys
import time

from collections import defaultdict
from typing import List, DefaultDict, ValuesView
from lux.game_map import RESOURCE_TYPES, Position, Cell
from lux.game_objects import Unit, Player
import maps.map_analysis as MapAnalysis
from .cluster import Cluster
import resources.resource_helper as ResourceService
from UnitInfo import UnitInfo


class ClusterControl:
    def __init__(self, game_state, pr):
        '''
        This is called only once, when the game starts.
        The cluster types are wood, coal, and uranium.
        If two resource cells are adjacent, or diagonal to each other,
        we assume they are in the same cluster.
        '''
        self.clusters: DefaultDict[str, Cluster] = defaultdict(Cluster)
        self.pr=pr

        resource_cells = ResourceService.get_resources(game_state)

        # creating wood cluster
        wood_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.WOOD
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(wood_resource_cells)):
            self.clusters[f'wood_{i}'] = Cluster(f'wood_{i}', rc, RESOURCE_TYPES.WOOD)

        # creating coal cluster
        coal_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.COAL
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(coal_resource_cells)):
            self.clusters[f'coal_{i}'] = Cluster(f'coal_{i}', rc, RESOURCE_TYPES.COAL)

        # creating uranium cluster
        uranium_resource_cells = [
            resource_tile for resource_tile in resource_cells
            if resource_tile.resource.type == RESOURCE_TYPES.URANIUM
        ]
        for i, rc in enumerate(MapAnalysis.get_resource_groups(uranium_resource_cells)):
            self.clusters[f'uranium_{i}'] = Cluster(f'uranium_{i}', rc, RESOURCE_TYPES.URANIUM)

        self.resource_pos_to_cluster = {}

        for k in self.clusters.values():
            for r in k.resource_cells:
                self.resource_pos_to_cluster[r.pos] = k

    def get_clusters(self) -> ValuesView[Cluster]:
        return self.clusters.values()

    def get_cluster_from_centroid(self, pos: Position) -> Cluster:
        for k in self.clusters.values():
            if k.get_centroid() == pos:
                return k

        return None

    def update(self, game_state, player: Player, opponent: Player, unit_info: DefaultDict[str, UnitInfo]):

        # function_start_time = time.process_time()

        # update cell distribution
        for k in list(self.clusters.keys()):
            self.clusters[k].update(
                game_state,
                player, opponent, unit_info
            )
            if len(self.clusters[k].resource_cells) == 0:
                self.pr("T_" + str(game_state.turn), "cluster", k, "terminated")
                del self.clusters[k]

        # attribute friendly unit to the closer cluster

        # first clear them up
        for k in list(self.clusters.keys()):
            self.clusters[k].cleanup()

        for u in player.units:

            if u.id in unit_info.keys():
                # if explorer\traveler add the target position as cluster reference
                if unit_info[u.id].is_role_explorer() or unit_info[u.id].is_role_traveler():
                    if unit_info[u.id].target_position is not None:
                        closest_cluster,dist = self.get_closest_cluster(player, unit_info[u.id].target_position)
                        if closest_cluster is not None:
                            closest_cluster.add_incoming_explorer(u.id,unit_info[u.id].target_position)

                    # anyway next, unit
                    continue

            # otherwise just the position
            closest_cluster,dist = self.get_closest_cluster(player, u.pos)

            if closest_cluster is not None:
                if dist <= 2:
                    closest_cluster.add_unit(u.id)

        for city in player.cities.values():
            for city_tile in city.citytiles:

                closest_cluster, dist = self.get_closest_cluster(player, city_tile.pos)

                # if we found one
                if closest_cluster is not None:
                    closest_cluster.add_city_tile(city_tile, city.get_autonomy_turns())


        # update closest unit and enemy
        for k in list(self.clusters.keys()):
            self.clusters[k].update_closest(player, opponent)

        for k in list(self.clusters.keys()):
            self.clusters[k].refresh_score()

        # ms = "{:10.2f}".format(1000. * (time.process_time() - function_start_time))
        # print("T_" + str(game_state.turn), "cluster refresh performance", ms, file=sys.stderr)



    def get_closest_cluster(self, player, pos:Position) -> (Cluster,int):
        closest_cluster_distance = math.inf
        closest_cluster = None
        for k in list(self.clusters.values()):
            if k.res_type == RESOURCE_TYPES.WOOD or \
                    (k.res_type == RESOURCE_TYPES.COAL and player.researched_coal()) or \
                    (k.res_type == RESOURCE_TYPES.URANIUM and player.researched_uranium()):

                #dist = pos.distance_to(k.get_centroid())
                dist = pos.distance_to_mult(k.resource_cells)
                if dist < closest_cluster_distance:
                    closest_cluster_distance = dist
                    closest_cluster = k
                    if dist == 0:
                        break
        return closest_cluster, closest_cluster_distance

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
