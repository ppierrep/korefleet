from typing import *
from collections import defaultdict, Counter
import re

from kaggle_environments.envs.kore_fleets.helpers import Cell, Direction, Board, PlayerId, Player, FleetId, Fleet, ShipyardId, Shipyard
from utils import get_min_ship, collection_rate_for_ship_count
from turnSnapshot import turnSnapshot

class Planner():
    '''
        Class responsible to show future events, so that agent can act respectively.
    '''
    
    def __init__(self, board: 'Board', turn: int) -> None:
        self.snapshots = {}
        self.turn = turn

        self.snapshots[turn] = turnSnapshot.convert(board)
    
    def compute_snapshots(self, board):
        self.snapshots = {}
        snapshot = turnSnapshot.convert(board)
        self.snapshots[0] = snapshot
        for i in range(1, 30):
            new_snapshot = snapshot.next()
            self.snapshots[i] = new_snapshot

    def get_simulations(self, origin_cell: Cell, turn: int, routes: List[int]):
            res = []
            for route in routes:
                res.append(self.get_simulation(origin_cell, turn, route))
            return res

    def get_simulation(self, origin_cell: Cell, turn: int, route: str):
        route.replace('C', '') # simulation route does not need C
        info = RouteSimulationInfo(route, turn)

        total_kore = 0
        mined_kore = 0 
        empty_cells = 0
        already_mined = defaultdict(int)

        points = []
        actual_cell = origin_cell
        instructions_chunks = re.findall(r'([NSWE])(\d{0,2})?', route)

        # Get all points
        for instruction, nb_repeat in instructions_chunks:
            nb_repeat = 1 if not nb_repeat else int(nb_repeat) + 1  # '' handling
            for i in range(nb_repeat):
                dir = Direction.from_char(instruction)
                actual_cell = actual_cell.neighbor(dir.to_point())
                points.append(actual_cell.position)

        for step, point in enumerate(points):
            if turn + step < 400 and step < len(self.snapshots.keys()) - 1:
                cell = self.snapshots[step].cells[point]

                kore = cell.kore * (1 - already_mined[point] * info.min_kore_mining_ratio)
                total_kore += kore
                mined_kore += info.min_kore_mining_ratio * kore

                dist = point.distance_to(origin_cell.position, size=21)
                if dist > info.max_dist:
                    info.max_dist = dist

                already_mined[point] +=1
                if kore == 0:
                    empty_cells += 1
                if not cell.fleet_id:
                    continue
                else:
                    info.intercepted = True
                    break

        places_visited = Counter(already_mined)
        info.same_trajectory_count = sum(places_visited.values()) - len(places_visited.values())  # number of time we are on the same tile twice

        info.flight_plan_time = step + 1
        info.kore = total_kore
        info.mined_kore = mined_kore

        info.empty_cells = empty_cells
        info.empty_cells_ratio = empty_cells / info.flight_plan_time
        info.kore_per_step = total_kore / info.flight_plan_time
        info.mined_kore_per_step = mined_kore / info.flight_plan_time

        return info


class RouteSimulationInfo():
    def __init__(self, flight_plan: str, turn: int):
        self.min_fleet = get_min_ship(flight_plan)
        self.max_dist = 0
        self.flight_plan = flight_plan
        self.turn = turn
        self.min_kore_mining_ratio = collection_rate_for_ship_count(self.min_fleet)

        self.kore = 0
        self.empty_cells = 0
        self.empty_cells_ratio = 0
        self.mined_kore = 0
        self.kore_per_step = 0
        self.mined_kore_per_step = 0

        # binary
        self.intercepted = False

        # events
        self.flight_plan_time = None

        self.same_trajectory_count = 0
