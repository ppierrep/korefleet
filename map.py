from itertools import permutations, product
from copy import deepcopy
from typing import *
import re

import networkx as nx
from kaggle_environments.envs.kore_fleets.helpers import Board, Cell, Direction, Point

class Trajectory():
    def __init__(self, origin_cell: Cell) -> None:
        self.instructions: List[Direction] = []
        self.origin_cell = origin_cell
        self.flight_plan = None
        self.kore = None
        self.kore_inclunding_drift = None
        self.finish_in_shipyard = None
        self.leads_to_shipyard = None

    def add(self, dir: Direction):
        self.instructions.append(dir)
    
    def set_flight_plan(self, flight_plan: str) -> None:
        self.flight_plan = flight_plan
        actual_cell = self.origin_cell

        real_plan = ''  # if encountering shipyard, crop plan
        instructions_chunks = re.findall(r'(\d{0,2})([NSWE])', flight_plan)
        for nb_repeat, instruction in instructions_chunks:
            nb_repeat = 1 if not nb_repeat else nb_repeat  # '' handling
            for i in range(int(nb_repeat)):
                dir = Direction.from_char(instruction)
                self.add(dir)
                actual_cell = actual_cell.neighbor(dir.to_point())
                real_plan += dir.to_char()

                if actual_cell.shipyard:
                    self.finish_in_shipyard = True
                    break
            break
        
        # See if last traj leads to shipyard
        for i in range(20):
            if actual_cell.shipyard:
                self.leads_to_shipyard = True
            actual_cell = actual_cell.neighbor(self.instructions[-1].to_point())
        
        real_plan = compress(real_plan)
        self.flight_plan = real_plan

    
    def evaluate(self):
        # TODO: Take in account kore regeneration and timelaps
        actual_cell = self.origin_cell
        self.kore = 0
        self.kore_inclunding_drift = 0

        for _dir in self.instructions:
            actual_cell = actual_cell.neighbor(_dir.to_point())
            self.kore += actual_cell.kore
        
        self.kore_inclunding_drift = self.kore
        for i in range(40):
            if actual_cell.shipyard:
                self.leads_to_shipyard = True

            actual_cell = actual_cell.neighbor(self.instructions[-1].to_point())
            self.kore_inclunding_drift += actual_cell.kore
    
    def __repr__(self) -> str:
        return f"{self.instructions}"


class Map():
    def __init__(self, board: Board):
        self.map_cells: Dict[Point, Cell] = board.cells
        pass
    
    def convert_flight_plan_to_trajectories(self, origin_cell: Cell, flight_plans: List[str]):
        trajectories = []
        for flight_plan in flight_plans:
            traj = Trajectory(origin_cell)
            traj.set_flight_plan(flight_plan)
            trajectories.append(traj)
        return trajectories


direction_re = '[NSWE]'
quantifier_re = '([1-9]|1[0-9]|2[10])'  # limit to 21+

def get_all_flight_plans_under_length(length: int) -> List[str]:
    def _is_flight_plan_conform(plan: str) -> bool:
        # Finishing by direction
        # Quantifier always followed by direction
        match = re.search(r'^({quantifier}?{direction}+)+$'.format(quantifier=quantifier_re, direction=direction_re), plan)
        match2 = re.search(r'{direction}{direction}$'.format(direction=direction_re), plan)  # limit end  N15E == NE
        match3 = re.search(r'(NN|WW|EE|SS)', plan)
        match4 = re.search(r'^{direction}'.format(direction=direction_re), plan)
        return bool(match) and bool(match2) and not bool(match3) and bool(match4)

    alphabet = 'NSWE0123456789'
    all_path = []
    for i in range(1, length + 1):
        _paths = [''.join(path) for path in product(alphabet, repeat=i)]
        _valid_paths = [path for path in _paths if _is_flight_plan_conform(path)]
        all_path.extend(_valid_paths)
    return all_path


def compress(expanded_flight_plan: str) -> str:
    '''
        Compress an expanded flight plan (EEEEENSS) into a compact one (5EN2S) while maintaining the order.
    '''
    res = ''
    cursor = ''
    counter = 1
    for s in expanded_flight_plan:
        if not cursor:
            cursor = s
            continue
        if s == cursor:
            counter += 1
        else:
            res += f'{counter}{cursor}'
            cursor = s
            counter = 1

    res += f'{counter}{cursor}'
    res = re.sub(r'(?<!\d)(1)(?=[NSWE])', '', res)
    return res