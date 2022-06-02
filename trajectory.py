from typing import *
import re
from itertools import groupby

from kaggle_environments.envs.kore_fleets.helpers import Cell, Direction, Point

class TrajectoryInfo():
    def __init__(self) -> None:
        self.is_intercepted = None
        self.is_intercepted_by_withrdrawer = None
        self.is_drifting = None
        # self.is_intercepted_by_ennemy = None


class Trajectory():
    def __init__(self, origin_cell: Cell) -> None:
        self.instructions: List[Direction] = []
        self.points : List[Point] = []
        self.obsolete_route_at_turn : int = 0 # TODO: recompute traj when traj become obsolete
        self.origin_cell = origin_cell
        self.flight_plan = None
        self.kore = None
        self.kore_inclunding_drift = None
        self.finish_in_shipyard = None
        self.leads_to_shipyard = None
        self.started_at_turn = None
        self.finished_at_turn = None
        self.trajectory_info = TrajectoryInfo()

    def add(self, dir: Direction):
        self.instructions.append(dir)
    
    def add_cell_route(self, cell: Cell) -> None:
        self.points.append(cell.position)
        self.obsolete_route_at_turn += 1
    
    def set_flight_plan(self, flight_plan: str, turn: int) -> None:
        self.obsolete_route_at_turn = turn
        self.started_at_turn = turn
        self.flight_plan = flight_plan
        actual_cell = self.origin_cell
        self.add_cell_route(actual_cell)

        real_plan = ''  # if encountering shipyard, crop plan
        instructions_chunks = re.findall(r'(\d{0,2})([NSWE])', flight_plan)
        for nb_repeat, instruction in instructions_chunks:
            nb_repeat = 1 if not nb_repeat else nb_repeat  # '' handling
            for i in range(int(nb_repeat)):
                dir = Direction.from_char(instruction)
                self.add(dir)
                actual_cell = actual_cell.neighbor(dir.to_point())
                self.add_cell_route(actual_cell)
                real_plan += dir.to_char()

                if actual_cell.shipyard:
                    self.finish_in_shipyard = True
                    break
        
        # See if last traj leads to shipyard
        for i in range(20):
            if actual_cell.shipyard:
                self.leads_to_shipyard = True
            actual_cell = actual_cell.neighbor(self.instructions[-1].to_point())
            self.add_cell_route(actual_cell)
        
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

# def compress(expanded_flight_plan: str) -> str:
#     '''
#         Compress an expanded flight plan (EEEEENSS) into a compact one (5EN2S) while maintaining the order.
#     '''
#     res = ''
#     cursor = ''
#     counter = 1
#     for s in expanded_flight_plan:
#         if not cursor:
#             cursor = s
#             continue
#         if s == cursor:
#             counter += 1
#         else:
#             res += f'{counter}{cursor}'
#             cursor = s
#             counter = 1

#     res += f'{counter}{cursor}'
#     res = re.sub(r'(?<!\d)(1)(?=[NSWE])', '', res)
#     return res


def compress(expanded_flight_plan: str) -> str:
    '''
        Compress an expanded flight plan (EEEEENSS) into a compact one (E4ENS) while maintaining the order.
        Examples:
            EEEEENSS -> E4ENS
            NEEENNNEEE -> N3E3NE
    '''
    # TODO: allow path factorization : NEEENNNEEE -> N6EN or N3NE instead of N3E3NE
    path = expanded_flight_plan[0]
    _groupby = [(char, len(list(g))) for char, g in groupby(expanded_flight_plan[1:])]
    for str_dir, length in _groupby:
        path += str(length) + str_dir if length > 1 else str_dir
    
    # if last elem is 3E, remove quantifier to save space
    return re.sub(r'(\d{1,2})(?=[NSWE]$)', '', path)
