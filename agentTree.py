
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point
from py_trees import behaviours, composites

import behaviorTree

planner = None
schedule_next_action = []


def create_root():
    root = composites.Sequence("Gathering")
    get_all_available_routes = behaviorTree.gathering.AvailableRoutes(
        name="Get all routes of max length 7",
        maximum_length=7
    )
    selector = composites.Selector("Is_Route")
    
    launch = composites.Sequence("Launch Fleet")
    is_route = behaviorTree.gathering.IsRoute("Is available routes (greedy)?")
    launch_fleet = behaviorTree.gathering.LaunchFleet("Launch  fleet (greedy)")

    build_fleet = behaviorTree.build.BuildFleet("Build fleet")
    
    launch.add_children([is_route, launch_fleet])
    selector.add_children([launch, build_fleet])
    root.add_children([get_all_available_routes, selector])
   
    # write_blackboard_variable = BlackboardWriter(name="Writer")
    # check_blackboard_variable = py_trees.behaviours.CheckBlackboardVariableValue(
    #     name="Check Nested Foo",
    #     check=py_trees.common.ComparisonExpression(
    #         variable="nested.foo",
    #         value="bar",
    #         operator=operator.eq
    #     )
    # )
    # params_and_state = ParamsAndState()
    # root.add_children([
    #     set_blackboard_variable,
    #     write_blackboard_variable,
    #     check_blackboard_variable,
    #     params_and_state
    # ])
    return root


def baseline(obs, config):
    board = Board(obs, config)
    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore
    

    root = create_root()
    root.setup_with_descendants()


    return me.next_actions

