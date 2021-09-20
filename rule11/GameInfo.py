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

    def update(self, player: Player, game_state: Game):
        self.increase_research_points_last_turn = player.research_points - self.reseach_points
        self.reseach_points = player.research_points
        self.increase_research_points_sequence.insert(0, self.increase_research_points_last_turn)
        self.turn = game_state.turn
        self.log_research_stats(5)
        self.log_prefix = 'GameInfo#' + self.turn.__str__()

    def get_research_increase_last_n_turns(self, n: int) -> int:
        sum = 0
        for r in itertools.islice(self.increase_research_points_sequence, n):
            sum += r
        return sum

    def get_research_rate(self, n: int) -> float:
        return float(self.get_research_increase_last_n_turns(n)) / float(n)

    def log_research_stats(self, n: int):
        print(self.log_prefix, 'Research points', self.reseach_points, ' research rate', self.get_research_rate(5),
              file=sys.stderr)
