from itertools import permutations, product
from copy import deepcopy
from typing import *
import re

import networkx as nx
from kaggle_environments.envs.kore_fleets.helpers import Board, Cell, Direction, Point

from trajectory import Trajectory



class Map():
    def __init__(self, board: Board):
        self.map_cells: Dict[Point, Cell] = board.cells
        pass
    
    # def convert_flight_plan_to_trajectories(self, origin_cell: Cell, flight_plans: List[str], turn: int):
    #     trajectories = []
    #     for flight_plan in flight_plans:
    #         traj = Trajectory(origin_cell)
    #         traj.set_flight_plan(flight_plan, turn)
    #         trajectories.append(traj)
    #     return trajectories


direction_re = '[NSWE]'
quantifier_re = '([1-9]|1[0-9]|2[10])'  # limit to 21+

def get_all_flight_plans_under_length(length: int) -> List[str]:
    def _is_flight_plan_conform(plan: str) -> bool:
        # Finishing by direction
        # Quantifier always followed by direction
        match = re.search(r'^{direction}({quantifier}?{direction}+)+$'.format(quantifier=quantifier_re, direction=direction_re), plan)
        match2 = re.search(r'{direction}{direction}$'.format(direction=direction_re), plan)  # limit end  N15E == NE
        match3 = re.search(r'(NN|WW|EE|SS)', plan)
        return bool(match) and bool(match2) and not bool(match3)

    alphabet = 'NSWE0123456789'
    all_path = []
    for i in range(1, length + 1):
        _paths = [''.join(path) for path in product(alphabet, repeat=i)]
        _valid_paths = [path for path in _paths if _is_flight_plan_conform(path)]
        all_path.extend(_valid_paths)
    return all_path
