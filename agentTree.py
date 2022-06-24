
import functools
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point
from py_trees import behaviours, composites, blackboard, common, display, logging, visitors, trees
import functools
import pandas as pd

from behaviorTree import gathering, build, recon, defence, generic
from planner import Planner

planner = None
schedule_next_action = []


# import debugpy

# debugpy.listen(5679)
# print("Waiting for debugger attach")
# debugpy.wait_for_client()
# # logging.level = logging.Level.DEBUG

def post_tick_handler(snapshot_visitor, behaviour_tree, show = False, tree_res=None, activity_stream=None):
    if show:
        print(
        display.unicode_tree(
            behaviour_tree.root,
            visited=snapshot_visitor.visited,
            previously_visited=snapshot_visitor.visited,
            show_status=True
            )
        )
    elif tree_res is not None:
        tree_res[0] = display.unicode_tree(
                    behaviour_tree.root,
                    visited=snapshot_visitor.visited,
                    previously_visited=snapshot_visitor.visited,
                    show_status=True
        )


def create_gathering(greedy=True):
    '''
        Args: 
            greedy: Always take the highest gross route independently of fleet number
    '''
    root = composites.Selector("root (gathering)")
    
    not_enough_fleet_sequence = composites.Sequence("Fleet number check")
    not_enough_fleet = gathering.NotEnoughFleet("Not Enough Fleet")
    build_fleet_1 = build.BuildFleet("Build fleet")
    
    go_gather_sequence = composites.Sequence("Gathering")
    get_all_available_routes = gathering.AvailableRoutes(name="Get all routes of max length 7", greedy=greedy)
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

def create_shipyard_defence():
    '''
        sequence >> inc fleet ?, enough_to_defend, selector
        selector >> sequence1, sequence2
        sequence1 >> need to build, build ship
        sequence2 >> gathering (with leftovers ship) 
    '''
    root = composites.Sequence("root (shipyard defence)")
    is_inc_fleet = recon.isIncomingFleet("Incoming fleet")
    enough_to_defend = defence.EnoughToDefend("Enough fleet to defend")
    selector = composites.Selector("Build or use leftover fleet to mine")
    root.add_children([is_inc_fleet, enough_to_defend, selector])

    sequence1 = composites.Sequence("Fleet production")
    gather = create_gathering(greedy=False)  # add leftover number which will define number of usablefleet for a mining mission
    selector.add_children([sequence1, gather])

    need_to_build = build.NeedToBuild("Need to build")
    build_fleet = build.BuildFleet("Build fleet")
    sequence1.add_children([need_to_build, build_fleet])

    return root

def create_shipyard_expand():
    '''
        sequence >> enough fleets, expand
    '''
    root = composites.Sequence("root (shipyard expand)")
    enough_fleet = generic.EnoughFleet('Is enough fleet for shipyard building', number=75)
    enough_kore = generic.EnoughKore('Is enough kore for shipyard building', number=300)
    build_shipyard = build.BuildShipyard('Build Shipyard')
    root.add_children([enough_fleet, build_shipyard, enough_kore])

    return root

def scale_fleet_generation_with_ennemy():
    '''
        sequence >> ennemies are amassing units, build fleet
    '''
    root = composites.Sequence("root (fleet generation mirroring)")
    ennemy_is_bluiding_up_fleet = recon.EnnemyIsAmmassingFleet('Closest ennemy is Amassing Fleet')
    build_up_force = build.BuildFleet("Build fleet")
    root.add_children([ennemy_is_bluiding_up_fleet, build_up_force])

    return root

def raid_shipyards():
    root = composites.Sequence("root (raid shyipyard)")
    
    is_actual_raider_in_need_of_assisstance = None
    assist_raider = None

    find_best_possible_candidates = None
    launch_raider = None

    return 

# build_fleet

planner = None
root = composites.Selector("Bot")
root.add_children([create_shipyard_defence(), scale_fleet_generation_with_ennemy(), create_shipyard_expand(), create_gathering()])

blackboard.Blackboard.enable_activity_stream(maximum_size=100)
_blackboard = blackboard.Client(name="Board")
_blackboard.register_key(key="board", access=common.Access.WRITE)
_blackboard.register_key(key="planner", access=common.Access.WRITE)
_blackboard.register_key(key="shipyard", access=common.Access.WRITE)
_blackboard.register_key(key="me", access=common.Access.WRITE)
_blackboard.register_key(key="action", access=common.Access.READ)


_blackboard.register_key(key="incoming_fleet_infos", access=common.Access.READ)
_blackboard.register_key(key="not_needed_fleet", access=common.Access.READ)
_blackboard.register_key(key="need_to_build", access=common.Access.READ)

root.setup_with_descendants()

turns = []
tree_res = []
activity_stream = []
def baselineTree(obs, config):
    global _blackboard
    global planner
    global root
    board = Board(obs, config)
    me = board.current_player
    turn = board.step
    
    # visualization only
    global turns
    global tree_res
    global activity_stream
    tree = ["", ""]


    if not planner:
        planner = Planner(board, turn)
    
    planner.turn = turn
    planner.compute_snapshots(board=board)

    _blackboard.board = board
    _blackboard.planner = planner
    _blackboard.me = me

    snapshot_visitor = visitors.SnapshotVisitor()
    behaviour_tree = trees.BehaviourTree(root)
    behaviour_tree.add_post_tick_handler(
        functools.partial(
            post_tick_handler,
            snapshot_visitor,
            show=False,
            tree_res=tree
        ))
    behaviour_tree.visitors.append(snapshot_visitor)
    
    for shipyard in me.shipyards:
        _blackboard.shipyard = shipyard
        behaviour_tree.tick()
        # if isinstance(event :=_blackboard.action, str):
        #     # special events 
        shipyard.next_action = _blackboard.action


    turns.append(turn)
    tree_res.append(tree[0])
    activity_stream_items = [el for el in blackboard.Blackboard.activity_stream.data if el.key in ['/incoming_fleet_infos', '/not_needed_fleet', '/need_to_build']]
    if len(activity_stream_items):
        activity_stream.append(str([{el.key: el.current_value} for el in  activity_stream_items]))
    else:
        activity_stream.append("")

    blackboard.Blackboard.activity_stream.data.clear()
    pd.DataFrame(
        data={
            'turn': turns,
            'tree': tree_res,
            'activity_stream': activity_stream
        }
    ).to_csv('tree_res.csv')

    return me.next_actions

