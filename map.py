from itertools import permutations, product
from copy import deepcopy
from typing import *
import re

import networkx as nx
import numpy as np
import scipy.signal
from kaggle_environments.envs.kore_fleets.helpers import Board, Cell, Direction, Point

from trajectory import Trajectory



class Map():
    def __init__(self, board: Board):
        self.map_cells: Dict[Point, Cell] = board.cells
        self.player = board.current_player

    def get_map_shipyard_position_candidates(self, distA: int, distB: int):
        me = self.player
        # dirty but working
        ally_shipyard_positions = [s.cell.position for s in me.shipyards]
        positions = []
        for point in [point for point in self.map_cells]:
            # altleast one at minDist/maxDist and all >= mindist 
            dists = [point.distance_to(spoint, 21) for spoint in ally_shipyard_positions]
            if all([d >= distA for d in dists]) and any([d <= distB for d in dists]):
                positions.append(point)

        return positions
    
    
    # def convert_flight_plan_to_trajectories(self, origin_cell: Cell, flight_plans: List[str], turn: int):
    #     trajectories = []
    #     for flight_plan in flight_plans:
    #         traj = Trajectory(origin_cell)
    #         traj.set_flight_plan(flight_plan, turn)
    #         trajectories.append(traj)
    #     return trajectories


direction_re = '[NSWE]'
quantifier_re = '([1-9]|1[0-9]|2[10])'  # limit to 21+

# def get_all_flight_plans_under_length(length: int) -> List[str]:
#     def _is_flight_plan_conform(plan: str) -> bool:
#         # Finishing by direction
#         # Quantifier always followed by direction
#         match = re.search(r'^{direction}({quantifier}?{direction}+)+$'.format(quantifier=quantifier_re, direction=direction_re), plan)
#         match2 = re.search(r'{direction}{direction}$'.format(direction=direction_re), plan)  # limit end  N15E == NE
#         match3 = re.search(r'(NN|WW|EE|SS)', plan)
#         return bool(match) and bool(match2) and not bool(match3)

#     alphabet = 'NSWE0123456789'
#     all_path = []
#     for i in range(1, length + 1):
#         _paths = [''.join(path) for path in product(alphabet, repeat=i)]
#         _valid_paths = [path for path in _paths if _is_flight_plan_conform(path)]
#         all_path.extend(_valid_paths)
#     return all_path

def generate_length_3_pos() -> List[str]:
    '''
        Generate flight plan, allowing vessels to comeback to base. 
        Returns: canonical flight plans
        example: NiS where i can be [0-9]
    '''
    paths = []
    for fst_dir in ['N', 'S', 'W', 'E']:
        flight_plan = fst_dir + 'i' + Direction.from_char(fst_dir).opposite().to_char()
        paths.append(flight_plan)
    return paths

def generate_length_5_pos() -> List[str]:
    '''
        Generate flight plan, allowing vessels to comeback to base. 
        Returns: canonical flight plans
        example: NiEWS / NEiSW where i can be [0-9]
    '''
    # NiEWS elbow
    paths = []
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir + 'i'
            flight_plan += scd_dir + Direction.from_char(scd_dir).opposite().to_char()
            flight_plan += _dir.opposite().to_char()
            paths.append(flight_plan)
    
    # ENdWS box
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir
            flight_plan += scd_dir + 'i' + _dir.opposite().to_char()
            flight_plan += Direction.from_char(scd_dir).opposite().to_char()
            paths.append(flight_plan)
    return paths


def generate_length_7_pos() -> List[str]:
    '''
        Generate flight plan, allowing vessels to comeback to base. 
        Returns: canonical flight plans
        example: NiWjEjS where i x j two integers
    '''
    # NiWjEjS elbow
    paths = []
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir + 'i'
            flight_plan += scd_dir + 'j'
            flight_plan += Direction.from_char(scd_dir).opposite().to_char() + 'j'
            flight_plan += _dir.opposite().to_char()
            paths.append(flight_plan)
    
    # NiWjSiE box
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir + 'i'
            flight_plan += scd_dir + 'j'
            flight_plan += _dir.opposite().to_char() + 'i'
            flight_plan += Direction.from_char(scd_dir).opposite().to_char()
            paths.append(flight_plan)

    # NiWNjES spoon
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir + 'i'
            flight_plan += scd_dir
            flight_plan += fst_dir + 'i'
            flight_plan += Direction.from_char(scd_dir).opposite().to_char()
            flight_plan += _dir.opposite().to_char()
            paths.append(flight_plan)
    
    # ESiENiW Flag
    for fst_dir in ['N', 'S', 'W', 'E']:
        _dir = Direction.from_char(fst_dir)
        for scd_dir in [_dir.rotate_right().to_char(), _dir.rotate_left().to_char()]:
            flight_plan = fst_dir
            flight_plan += scd_dir + 'i'
            flight_plan += fst_dir
            flight_plan += Direction.from_char(scd_dir).opposite().to_char() + 'i'
            flight_plan += _dir.opposite().to_char()
            paths.append(flight_plan)

    return paths

def get_all_flight_plans_under_length(length: int) -> List[str]:
    '''
    Returns: Set of precalculated routes that allow vessels to mine without drifing.
    '''
    # TODO: Prettify using class attribute generated call
    routes = []
    funcs = {
        3 : generate_length_3_pos,
        5 : generate_length_5_pos,
        7 : generate_length_7_pos,
    }
    for k, func in funcs.items():
        if length >= k:
            routes.extend(func())
    
    res = set()
    for route in routes:
        numbers = '123456789'
        for i in numbers:
            for j in numbers:
                r = route.replace('i', i)
                r = r.replace('j', j)
                res.add(r)
    return list(res)


def gkern(l=5, sig=1.):
    """
    creates gaussian kernel with side length `l` and a sigma of `sig`
    central value must be zeroed, quick and dirty -> odd value for length 
    """
    ax = np.linspace(-(l - 1) / 2., (l - 1) / 2., l)
    gauss = np.exp(-0.5 * np.square(ax) / np.square(sig))
    gauss[int(len(gauss) / 2)] = 0
    kernel = np.outer(gauss, gauss)
    return kernel / np.sum(kernel)

def get_map_kore_convolutions(board, length):
    map_infos = {
        "pos": [(pos.x, pos.y) for pos in board.cells.keys()],
        "kore": [cell.kore for cell in board.cells.values()],
        "shipyard": [bool(cell.shipyard) for cell in board.cells.values()]
    }

    arr = np.zeros((21, 21))
    for pos, kore, shipyard in zip(map_infos['pos'], map_infos['kore'], map_infos['shipyard']):
        arr[pos] = kore if not shipyard else 0 
    return scipy.signal.convolve2d(arr, gkern(l=length, sig=1.), boundary='wrap')
        
