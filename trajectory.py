from typing import *
import re
from itertools import groupby

from kaggle_environments.envs.kore_fleets.helpers import Cell, Direction, Point

class TrajectoryInfo():
    def __init__(self) -> None:
        self.is_intercepted = None
        self.is_intercepted_by_withrdrawer = None
        self.is_drifting = None

        self.started_at_turn = None
        self.finished_at_turn = None

        self.finish_in_shipyard = None
        self.drift_to_shipyard = None
        # self.is_intercepted_by_ennemy = None

        self.kore = None
        self.kore_inclunding_drift = None


class Trajectory():
    def __init__(self, origin_cell: Cell) -> None:
        self.points : List[Point] = []
        self.origin_cell = origin_cell
        self.flight_plan = None

        self.trajectory_info = TrajectoryInfo()
    
    def add_cell_route(self, cell: Cell) -> None:
        self.points.append(cell.position)
    
    def set_flight_plan(self, fleet, turn: int) -> None:
        flight_plan = fleet.flight_plan if len(fleet.flight_plan) else fleet.direction.to_char()
        self.trajectory_info.started_at_turn = turn
        self.flight_plan = flight_plan
        actual_cell = self.origin_cell
        self.add_cell_route(actual_cell)

        real_plan = ''  # if encountering shipyard, crop plan
        instructions_chunks = re.findall(r'([NSWE]|^)(\d{0,2})?', flight_plan)
        for instruction, nb_repeat in instructions_chunks:
            nb_repeat = 1 if not nb_repeat else nb_repeat  # '' handling
            for i in range(int(nb_repeat)):
                if instruction:
                    dir = Direction.from_char(instruction)
                else:
                    dir = fleet.direction

                actual_cell = actual_cell.neighbor(dir.to_point())
                self.add_cell_route(actual_cell)
                real_plan += dir.to_char()

                if actual_cell.shipyard:
                    self.trajectory_info.finish_in_shipyard = True
                    break
        
        # Compute all drifting trajectory
        for i in range(400 - turn - len(self.points)):
            if actual_cell.shipyard:
                self.trajectory_info.drift_to_shipyard = True
                break

            last_dir = Direction.from_char(instruction)
            actual_cell = actual_cell.neighbor(last_dir.to_point())
            self.add_cell_route(actual_cell)

        if not(self.trajectory_info.drift_to_shipyard or self.trajectory_info.finish_in_shipyard):
            self.trajectory_info.is_drifting = True
        real_plan = compress(real_plan)
        self.flight_plan = real_plan

    
    # def evaluate(self):
    #     # TODO: Take in account kore regeneration and timelaps
    #     actual_cell = self.origin_cell
    #     self.kore = 0
    #     self.kore_inclunding_drift = 0

    #     for points in self.points:
    #         actual_cell = actual_cell.neighbor(points)
    #         self.kore += actual_cell.kore
        
    #     self.kore_inclunding_drift = self.kore
    #     for i in range(40):
    #         if actual_cell.shipyard:
    #             self.drift_to_shipyard = True

    #         actual_cell = actual_cell.neighbor(self.points[-1])
    #         self.kore_inclunding_drift += actual_cell.kore


def compress(expanded_flight_plan: str, compress_last: bool=False) -> str:
    '''
        Compress an expanded flight plan (EEEEENSS) into a compact one (E4ENS) while maintaining the order.
        Examples:
            EEEEENSS -> E4ENS
            NEEENNNEEE -> N3E3NE
    '''
    # TODO: allow path factorization : NEEENNNEEE -> N6EN or N3NE instead of N3E3NE
    path = ''
    _groupby = [(char, len(list(g))) for char, g in groupby(expanded_flight_plan)]
    for str_dir, length in _groupby:
        path += str_dir + str(length) if length > 1 else str_dir
    
    # if last elem is E3, remove quantifier to save space
    return re.sub(r'(\d)$', '', path) if compress_last else path