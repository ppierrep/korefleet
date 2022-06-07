from collections import defaultdict
from tracemalloc import start
from typing import *
from xml.etree.ElementTree import PI
import math

from kaggle_environments.envs.kore_fleets.helpers import Point, Cell, Direction, Board
from fleet import CustomFleet
from map import Map
from utils import collection_rate_for_ship_count, get_min_ship

from trajectory import Trajectory, TrajectoryInfo, compress

class CollisionAndComeBackRoute():  # TODO: Merge with trajectory
    def __init__(self, fleet: CustomFleet, time_elapsed: int, distance_to_drifter: int, turn: int, origin_point: Point, target_point: Point) -> None:
        self.travel_time_to_drifter = distance_to_drifter
        self.time_until_collection = time_elapsed
        self.time_before_sending_ship = time_elapsed - distance_to_drifter - 1 # time to build ship
        self.total_mission_time = time_elapsed +  2 * distance_to_drifter  # Assuming for now that withdrawer only get one ship
        
        # collection spec
        self.minimum_ship_number = fleet.ship_count + 1 # TODO: count using TrajPlanner
        self.drifter_kore = fleet.kore

        # TODO: Filter by role
        self.target = fleet
        self.origin_point = origin_point
        self.target_point = target_point
        self.round_trip_path = self.compute_flight_plan(round_trip=True)

    def compute_flight_plan(self, round_trip: bool=False) -> str:
        vector = self.target_point - self.origin_point
        components = abs(vector)
        _x = 'W' if vector.x < 0 else 'E'
        _y = 'S' if vector.y < 0 else 'N'

        xc = components.x if components.x <= 1 else components.x - 1  # "N5E" go north > 5E go north > 4E ...
        yc = components.y if components.y <= 1 else components.y - 1

        if not round_trip:
            return compress(''.join([_x * xc] + [_y * yc]), compress_last=True)  # first deplacement is always free
        else:
            one_way = ''.join([_x * xc] + [_y * yc])
            round_trip = ''.join(reversed([Direction.from_char(char).opposite().to_char() for char in one_way]))
            return compress(one_way + round_trip, compress_last=True)


class TrajectoryPlanner():
    def __init__(self, total_turns: int, map_points: List[Point], _map: Board) -> None:
        self.fleet_planner = {}
        self.registered_fleet = {}
        self.kore_planner = {}
        for turn in range(total_turns):
            self.fleet_planner[turn] = {point: [] for point in map_points}
            self.kore_planner[turn] = {point: 0 for point in map_points}

        self.fleet_handled = set()
        self.map = _map

    def add_trajectory(self, turn: int, fleet: CustomFleet) -> None:
        # traj_infos = fleet.trajectory.trajectory_info
        if fleet.id not in self.registered_fleet:
            fleet = CustomFleet.convert(fleet, role='')
            fleet.trajectory.set_flight_plan(fleet=fleet, turn=turn)
            self.registered_fleet[fleet.id] = fleet
        
        fleet = self.registered_fleet[fleet.id]
        for step, point in enumerate(fleet.trajectory.points):
            if turn + step >= 400:
                continue
            space = self.fleet_planner[turn + step][point]
            if not len(space) and not self.map.cells[point].shipyard:
                self.fleet_planner[turn + step][point].append(fleet.id)
            elif len(space):
                # Collision
                _, fleet_to_remove_id = combine_fleets(self.registered_fleet[space[0]], fleet)
                # TODO: 
                    # Resolve any allied fleets that ended up in the same square DONE
                    # Check for fleet to fleet collisions (ennemy)
                    # Check for fleet to shipyard collisions
                self.remove_trajectory(self.registered_fleet[fleet_to_remove_id], turn + step)
            else:  # in shipyard
                pass

    def update_kore(self, board, turn) -> None:
        # TODO: Add ship destroyed kore
        map = board.cells
        next_steps = range(1, 30)
        for point, cell in map.items():
            self.kore_planner[turn][point] = cell.kore
        
        for step in next_steps:
            if turn + step >= 400:
                continue
            
            last_kore_map = self.kore_planner[turn + step - 1]
            last_fleet_map = self.fleet_planner[turn + step - 1]

            for point, fleets in last_fleet_map.items():
                consumption = 0
                if len(fleets):
                    num_ship = self.registered_fleet[fleets[0]].ship_count
                    consumption = collection_rate_for_ship_count(num_ship)
                
                regeneration = last_kore_map[point] * .02 if last_kore_map[point] < 500 else 0
                self.kore_planner[turn + step][point] = last_kore_map[point] - consumption + regeneration
        


    # def is_trajectory_intercepted(self, starting_turn: int, points: List[Point]) -> None:     
    #     for step, point in enumerate(points):
    #         if starting_turn + step >= 400:
    #             continue
    #         space = self.fleet_planner[starting_turn + step][point]
    #         if not len(space):
    #             continue
    #         else:
    #             # Collision
    #             # self.registered_fleet
    #             # TODO: 
    #                 # REturn collision with whom fleet, how, when and potential results
    #             self.remove_trajectory(self.registered_fleet[fleet_to_remove_id], turn + step)

    def remove_trajectory(self, fleet: CustomFleet, starting_from_turn: int) -> None:
        trajectory = fleet.trajectory
        steps_to_remove = starting_from_turn - trajectory.trajectory_info.started_at_turn
        points = []
        for step, point in enumerate(trajectory.points):
            turn = starting_from_turn + step
            if step < steps_to_remove:
                # do nothing to trajectory
                points.append(point)

            else:
                fleet.trajectory.trajectory_info.finished_at_turn = turn if not fleet.trajectory.trajectory_info.finished_at_turn else fleet.trajectory.trajectory_info.finished_at_turn
                # remove all traces
                if turn >= 400:
                    continue

                self.fleet_planner[turn][point] = [f for f in self.fleet_planner[turn][point] if not fleet.id == f]
                assert len(self.fleet_planner[turn][point]) < 2
        
        fleet.trajectory.points = points

    def get_drifter_interception_routes(self, from_cell: Cell, turn: int, drifter_id: int) -> List[CollisionAndComeBackRoute]:
        '''only launch when perigee'''
        routes = []
        fleet = self.registered_fleet[drifter_id]
        for time_elapsed, screenshot in enumerate(list(self.fleet_planner.values())[turn: turn + 15]):  # Compute all possible routes from now to 15 turn ahead
            for target, fleet_ids in screenshot.items():
                # Check the feasibility of launching a withdrawer to this pos
                # add followind direction after path has been completed
                if drifter_id in fleet_ids and target.distance_to(from_cell.position, 21) <= time_elapsed and fleet.trajectory.trajectory_info.is_drifting:  # withdrawer has enough time to get to drifter
                    # if drifter_id not in fleet_ids:
                    route = CollisionAndComeBackRoute(
                        fleet=fleet,
                        time_elapsed=time_elapsed,
                        distance_to_drifter=target.distance_to(from_cell.position, 21), # TODO: get board configuration size as distance
                        turn=turn,
                        origin_point=from_cell.position,
                        target_point=target
                    )
                    if route.time_before_sending_ship >= 0:
                        routes.append(route)
        return routes


    def get_simulations(self, origin_cell: Cell, turn: int, routes: List[int], board: 'Board'):
        res = []
        for route in routes:
            res.append(self.get_simulation(origin_cell, turn, route, board))
        return res

    def get_simulation(self, origin_cell: Cell, turn: int, route: str, board: 'Board'):
        # Create placeholder to call set_flight_plan TODO: remove the use of placeholder
        traj = Trajectory(origin_cell)
        traj.set_flight_plan(turn=turn, flight_plan=route)  # Highly convoluted

        info = RouteSimulationInfo(route, turn)
        total_kore = 0
        mined_kore = 0   # kore does not update
        already_mined = defaultdict(int)
        for step, point in enumerate(traj.points):
            if turn + step < 400:
                space = self.fleet_planner[turn + step][point]
                kore = self.kore_planner[turn + step][point] * (1 - already_mined[point] * info.min_kore_mining_ratio)
                total_kore += kore
                mined_kore += info.min_kore_mining_ratio * kore

                already_mined[point] +=1
                if not len(space):
                    continue
                else:
                    info.intercepted = True
                    break
                
        
        info.flight_plan_time = step
        info.kore = total_kore
        info.mined_kore = mined_kore

        info.kore_per_step = total_kore / info.flight_plan_time
        info.mined_kore_per_step = mined_kore / info.flight_plan_time

        return info


class RouteSimulationInfo():
    def __init__(self, flight_plan: str, turn: int):
        self.min_fleet = get_min_ship(flight_plan)
        self.flight_plan = flight_plan
        self.turn = turn
        self.min_kore_mining_ratio = collection_rate_for_ship_count(self.min_fleet)

        self.kore = 0
        self.mined_kore = 0
        self.kore_per_step = 0
        self.mined_kore_per_step = 0

        # binary
        self.intercepted = False

        # events
        self.flight_plan_time = None


def combine_fleets(f1: CustomFleet, f2: CustomFleet) -> Tuple[CustomFleet, CustomFleet]:
    if f1.less_than_other_allied_fleet(f2):
        f1, f2 = f2, f1
    f1._kore += f2.kore
    f1._ship_count += f2._ship_count

    return f1.id, f2.id