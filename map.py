from itertools import permutations
from copy import deepcopy
from typing import *

import networkx as nx
from kaggle_environments.envs.kore_fleets.helpers import Board, Cell, Direction, Point

class Trajectory():
    def __init__(self, origin_cell: Cell) -> None:
        self.instructions: List[Direction] = []
        self.origin_cell = origin_cell
        self.kore = None
        self.kore_inclunding_drift = None

    def add_from(self, last_traj):
        if last_traj:
            self.instructions.extend(deepcopy(last_traj.instructions))

    def add(self, dir: Direction):
        self.instructions.append(dir)
    
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
                break

            actual_cell = actual_cell.neighbor(self.instructions[-1].to_point())
            self.kore_inclunding_drift += actual_cell.kore
    
    def __repr__(self) -> str:
        return f"{self.instructions}"

class Map():
    def __init__(self, board: Board):
        self.map_cells: Dict[Point, Cell] = board.cells
        pass

    def list_available_route(self, origin_cell, len_action, last_direction=None, last_trajectory=None) -> List[Trajectory]:
        '''Get all routes with following constraints:
                - Beginning and ending are located at a cluster
                - Number of turns are lower or equal than len_action
        '''
        trajectories = []

        if len_action:
            for dir in Direction.list_directions():
                new_traj = Trajectory(origin_cell)
                new_traj.add_from(last_trajectory)
                new_traj.add(dir)
                trajectories.extend(self.list_available_route(origin_cell, len_action - 1, last_direction=dir, last_trajectory=new_traj))
        
        else:
            # replay trajectory
            actual_cell = origin_cell
            for _dir in last_trajectory.instructions:
                actual_cell = actual_cell.neighbor(_dir.to_point())

            for i in range(40):
                if actual_cell.shipyard:
                    trajectories.append(last_trajectory)
                    break
                
                actual_cell = actual_cell.neighbor(last_direction.to_point())
        
        return trajectories


                
