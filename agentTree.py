
import functools
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point
from py_trees import behaviours, composites, blackboard, common, display, logging, visitors, trees
import functools

from behaviorTree import gathering, build
from planner import Planner

planner = None
schedule_next_action = []


import debugpy

debugpy.listen(5678)
print("Waiting for debugger attach")
debugpy.wait_for_client()
# logging.level = logging.Level.DEBUG

def post_tick_handler(snapshot_visitor, behaviour_tree, show = False):
    if show:
        print(
        display.unicode_tree(
            behaviour_tree.root,
            visited=snapshot_visitor.visited,
            previously_visited=snapshot_visitor.visited,
            show_status=True
        )
    )


def create_root():
    root = composites.Selector("root (gathering)")
    
    not_enough_fleet_sequence = composites.Sequence("Fleet number check")
    not_enough_fleet = gathering.NotEnoughFleet("Not Enough Fleet")
    build_fleet_1 = build.BuildFleet("Build fleet")
    
    go_gather_sequence = composites.Sequence("Gathering")
    get_all_available_routes = gathering.AvailableRoutes(name="Get all routes of max length 7", maximum_length=7)
    isRoute_selector = composites.Selector("Is_Route")
    
    launch_sequence = composites.Sequence("Launch Fleet")
    is_route = gathering.IsRoute("Is available routes (greedy)?")
    launch_fleet = gathering.LaunchFleet("Launch  fleet (greedy)")
    
    build_fleet_2 = build.BuildFleet("Build fleet")
    
    root.add_children([not_enough_fleet_sequence, go_gather_sequence])
    not_enough_fleet_sequence.add_children([not_enough_fleet, build_fleet_1])

    go_gather_sequence.add_children([get_all_available_routes, isRoute_selector])
    isRoute_selector.add_children([launch_sequence, build_fleet_2])
    launch_sequence.add_children([is_route, launch_fleet])
    
    return root

# build_fleet

planner = None
root = create_root()
blackboard = blackboard.Client(name="Board")
blackboard.register_key(key="board", access=common.Access.WRITE)
blackboard.register_key(key="planner", access=common.Access.WRITE)
blackboard.register_key(key="shipyard", access=common.Access.WRITE)
blackboard.register_key(key="me", access=common.Access.WRITE)
blackboard.register_key(key="action", access=common.Access.READ)
root.setup_with_descendants()


def baselineTree(obs, config):
    global blackboard
    global planner
    global root
    board = Board(obs, config)
    me = board.current_player
    turn = board.step

    if not planner:
        planner = Planner(board, turn)
    
    planner.turn = turn
    planner.compute_snapshots(board=board)

    blackboard.board = board
    blackboard.planner = planner
    blackboard.me = me

    snapshot_visitor = visitors.SnapshotVisitor()
    behaviour_tree = trees.BehaviourTree(root)
    behaviour_tree.add_post_tick_handler(
        functools.partial(
            post_tick_handler,
            snapshot_visitor,
            show=True
        ))
    behaviour_tree.visitors.append(snapshot_visitor)
    
    for shipyard in me.shipyards:
        blackboard.shipyard = shipyard
        behaviour_tree.tick()
        shipyard.next_action = blackboard.action

    return me.next_actions

