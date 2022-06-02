from collections import defaultdict
from msilib.schema import Directory
from tracemalloc import start
from typing import *
from xml.etree.ElementTree import PI

from kaggle_environments.envs.kore_fleets.helpers import Point, Cell, Direction
from fleet import CustomFleet

from trajectory import Trajectory, TrajectoryInfo, compress

class CollisionAndComeBackRoute():  # TODO: Merge with trajectory
    def __init__(self, fleet: CustomFleet, time_elapsed: int, distance_to_drifter: int, turn: int, origin_point: Point, target_point: Point) -> None:
        self.travel_time_to_drifter = distance_to_drifter
        self.time_until_collection = time_elapsed
        self.time_before_sending_ship = time_elapsed - distance_to_drifter
        self.total_mission_time = time_elapsed +  2 * distance_to_drifter  # Assuming for now that withdrawer only get one ship
        
        # collection spec
        self.minimum_ship_number = fleet.ship_count + 1
        self.drifter_kore = fleet.kore

        self.target = fleet
        self.origin_point = origin_point
        self.target_point = target_point
        # TODO: Filter by role
    
    def compute_flight_plan(self) -> str:
        vector = self.target_point - self.origin_point
        components = abs(vector)
        if vector.x < 0:
            _x = 'W'
        else:
            _x = 'E'

        if vector.y < 0:
            _y = 'S'
        else:
            _y = 'N'

        return compress(''.join([_x * components.x] + [_y * components.y]))


class TrajectoryPlanner():
    def __init__(self, total_turns: int, map_points: List[Point]) -> None:
        self.fleet_planner = {}
        self.registered_fleet = {}
        for turn in range(1, total_turns + 1):
            self.fleet_planner[turn] = {point: defaultdict(list) for point in map_points}

        self.fleet_handled = set()

    def diagnostic_trajectory(self, trajectory : Trajectory, turn: int, map_fleets: Dict[str, CustomFleet]) -> None:
        '''Test trajectory inplace'''
        traj_infos = trajectory.trajectory_info
        for step, point in enumerate(trajectory.points):
            met_fleets_ids = self.fleet_planner[turn + step][point]
            if len(met_fleets_ids) > 0:
                traj_infos.is_intercepted = True
                traj_infos.is_intercepted_by_withrdrawer = True if traj_infos.is_intercepted_by_withrdrawer else any([map_fleets[fleet_id].role == 'withdrawer' for fleet_id in met_fleets_ids])
                return
        
        traj_infos.is_intercepted = False
        traj_infos.is_intercepted_by_withrdrawer = False
        traj_infos.is_drifting = True
        return
    
    def add_trajectory(self, turn: int, fleet: CustomFleet) -> None:
        # traj_infos = fleet.trajectory.trajectory_info
        if fleet.id not in self.registered_fleet:
            self.registered_fleet[fleet.id] = fleet
        for step, point in enumerate(fleet.trajectory.points[:15]):
            space = self.fleet_planner[turn + step][point]
            if not len(space):
                self.fleet_planner[turn + step][point].append(fleet.id)
            else:
                # collision
                _, fleet_to_remove = combine_fleets(space[0], fleet)
                # TODO: 
                    # resolve any allied fleets that ended up in the same square DONE
                    # Check for fleet to fleet collisions (ennemy)
                    # Check for fleet to shipyard collisions
                self.remove_trajectory(fleet_to_remove, turn + step)

    def remove_trajectory(self, fleet: CustomFleet, starting_from_turn: int) -> None:
        trajectory = fleet.trajectory
        steps_to_remove = starting_from_turn - trajectory.started_at_turn
        points = []
        for step, point in enumerate(trajectory.points):
            turn = starting_from_turn + step
            if step < steps_to_remove:
                # do nothing to trajectory
                points.append(point)

            else:
                fleet.finished_at_turn = turn if not fleet.finished_at_turn else fleet.finished_at_turn
                # remove all traces
                self.fleet_planner[turn][point] = [f for f in self.fleet_planner[turn][point] if not fleet.id == f.id]
                assert len(self.fleet_planner[turn][point]) < 2
        
        fleet.trajectory.points = points

    def get_drifter_interception_routes(self, from_cell: Cell, turn: int, drifter_id: int):
        '''only launch when perigee'''
        routes = []
        for time_elapsed, screenshot in enumerate(self.fleet_planner[turn: turn + 16]):  # Compute all possible routes from now to 15 turn ahead
            for target, fleet_ids in screenshot.items():
                # Check the feasibility of launching a withdrawer to this pos
                if drifter_id in fleet_ids and target.distance_to(from_cell.position) <= time_elapsed:  # withdrawer has enough time to get to drifter
                    fleet = self.registered_fleet[drifter_id]
                    route = CollisionAndComeBackRoute(
                        fleet=fleet,
                        time_elapsed=time_elapsed,
                        distance_to_drifter=target.distance_to(from_cell),
                        turn=turn,
                        origin_point=from_cell.position,
                        target_point=target
                    )
                    pass




            
        
# from helper
def combine_fleets(f1: CustomFleet, f2: CustomFleet) -> Tuple[CustomFleet, CustomFleet]:
    if f1.less_than_other_allied_fleet(f2):
        f1, f2 = f2, f1
    f1._kore += f2.kore
    f1._ship_count += f2._ship_count

    return f1.id, f2.id