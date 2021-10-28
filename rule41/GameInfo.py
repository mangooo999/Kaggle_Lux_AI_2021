from lux.game_objects import Player
from lux.game import Game

import sys
import itertools


class ResearchStats:
    def __init__(self):
        """
        initialize state
        """
        self.points = 0
        self.increase_points_last_turn = 0
        self.increase_points_sequence = []

    def update(self, actor: Player):
        self.increase_points_last_turn = actor.research_points - self.points
        self.points = actor.research_points
        self.increase_points_sequence.insert(0, self.increase_points_last_turn)

    def get_increase_last_n_turns(self, n: int) -> int:
        sum_research = 0
        for r in itertools.islice(self.increase_points_sequence, n):
            sum_research += r
        return sum_research

    def get_research_rate(self) -> float:
        return self.get_research_rate_flat()

    def get_research_rate_flat(self, n: int =5) -> float:
        return float(self.get_increase_last_n_turns(n)) / float(n)

    def get_research_rate_exp(self, n: int = 12) -> float:
        sum_research = 0.0
        sum_weights = 0.0
        i = 0.0
        for r in itertools.islice(self.increase_points_sequence, n):
            i += 1.0
            weight = 1.0 / (4.0 + i)
            sum_research += weight * float(r)
            sum_weights += weight

        return sum_research / sum_weights

    def log_research_stats(self, pr, log_prefix, prefix):
        pr(log_prefix, prefix, 'research_points', self.points, ' research_rate', self.get_research_rate())


class GameInfo:
    def __init__(self, pr):
        """
        initialize state
        """
        self.log_prefix = 'GameInfo'
        self.turn = 0
        self.research = ResearchStats()
        self.opponent_research = ResearchStats()
        self.research_this_turn = 0
        self.at_start_resources_within3 = 0
        self.pr = pr

    def update(self, player: Player, opponent: Player, game_state: Game):
        self.research.update(player)
        self.opponent_research.update(opponent)
        self.turn = game_state.turn
        self.log_research_stats()
        self.log_prefix = 'GameInfo#' + self.turn.__str__()
        self.research_this_turn = 0

    def get_research_increase_last_n_turns(self, n: int) -> int:
        return self.research.get_increase_last_n_turns(n)

    def get_opponent_research_increase_last_n_turns(self, n: int) -> int:
        return self.opponent_research.get_increase_last_n_turns(n)

    def do_research(self, actions, city_tile, msg):
        actions.append(city_tile.research())
        self.pr(msg)
        self.research_this_turn += 1

    def get_research_rate(self) -> float:
        return self.research.get_research_rate()

    def get_opponent_research_rate(self) -> float:
        return self.opponent_research.get_research_rate()

    def log_research_stats(self):
        self.research.log_research_stats(self.pr, self.log_prefix, "US ")
        self.opponent_research.log_research_stats(self.pr, self.log_prefix, "OPP")

    def get_total_reseach(self):
        return self.research.points + self.research_this_turn

    def still_can_do_reseach(self):
        return self.get_total_reseach() < 200
