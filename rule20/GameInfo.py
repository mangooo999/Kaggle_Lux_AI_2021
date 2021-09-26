from lux.game_objects import Player
from lux.game import Game

import sys
import itertools


class GameInfo:
    def __init__(self):
        """
        initialize state
        """
        self.log_prefix = 'GameInfo'
        self.reseach_points = 0
        self.turn = 0
        self.increase_research_points_last_turn = 0
        self.increase_research_points_sequence = []
        self.at_start_resources_within3 = 0

    def update(self, player: Player, game_state: Game):
        self.increase_research_points_last_turn = player.research_points - self.reseach_points
        self.reseach_points = player.research_points
        self.increase_research_points_sequence.insert(0, self.increase_research_points_last_turn)
        self.turn = game_state.turn
        self.log_research_stats(5)
        self.log_prefix = 'GameInfo#' + self.turn.__str__()
        self.research_this_turn=0

    def get_research_increase_last_n_turns(self, n: int) -> int:
        sum = 0
        for r in itertools.islice(self.increase_research_points_sequence, n):
            sum += r
        return sum

    def do_research(self,actions, city_tile, msg):
        actions.append(city_tile.research())
        print(msg, file=sys.stderr)
        self.research_this_turn += 1

    def get_research_rate(self, n: int) -> float:
        return float(self.get_research_increase_last_n_turns(n)) / float(n)

    def log_research_stats(self, n: int):
        print(self.log_prefix, 'Research points', self.reseach_points, ' research rate', self.get_research_rate(5),
              file=sys.stderr)

    def get_total_reseach(self):
        return self.reseach_points+self.research_this_turn

    def still_can_do_reseach(self):
        return self.get_total_reseach()<200




