from map import get_all_flight_plans_under_length
from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point

from utils import get_max_flight_plan

class AvailableRoutes(behaviour.Behaviour):
    def __init__(self, name, greedy):
        """
        Minimal one-time initialisation. A good rule of thumb is
        to only include the initialisation relevant for being able
        to insert this behaviour in a tree for offline rendering to
        dot graphs.

        Other one-time initialisation requirements should be met via
        the setup() method.
        """
        super().__init__(name)
        self.maximum_length = 7 if greedy else 0
        
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="board", access=common.Access.READ)
        self.blackboard.register_key(key="planner", access=common.Access.READ)
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="not_needed_fleet", access=common.Access.READ)

        self.blackboard.register_key(key="selected_route", access=common.Access.WRITE)

    def setup(self):
        """
        When is this called?
          This function should be either manually called by your program
          to setup this behaviour alone, or more commonly, via
          :meth:`~py_trees.behaviour.Behaviour.setup_with_descendants`
          or :meth:`~py_trees.trees.BehaviourTree.setup`, both of which
          will iterate over this behaviour, it's children (it's children's
          children ...) calling :meth:`~py_trees.behaviour.Behaviour.setup`
          on each in turn.

          If you have vital initialisation necessary to the success
          execution of your behaviour, put a guard in your
          :meth:`~py_trees.behaviour.Behaviour.initialise` method
          to protect against entry without having been setup.

        What to do here?
          Delayed one-time initialisation that would otherwise interfere
          with offline rendering of this behaviour in a tree to dot graph
          or validation of the behaviour's configuration.

          Good examples include:

          - Hardware or driver initialisation
          - Middleware initialisation (e.g. ROS pubs/subs/services)
          - A parallel checking for a valid policy configuration after
            children have been added or removed
        """
        self.logger.debug("  %s [Foo::setup()]" % self.name)

    def initialise(self):
        """
        When is this called?
          The first time your behaviour is ticked and anytime the
          status is not RUNNING thereafter.

        What to do here?
          Any initialisation you need before putting your behaviour
          to work.
        """
        self.logger.debug("  %s [Foo::initialise()]" % self.name)

    def update(self):
        """
        When is this called?
          Every time your behaviour is ticked.

        What to do here?
          - Triggering, checking, monitoring. Anything...but do not block!
          - Set a feedback message
          - return a py_trees.common.Status.[RUNNING, SUCCESS, FAILURE]
        """
        self.logger.debug("  %s [Foo::update()]" % self.name)
        board = self.blackboard.board
        planner = self.blackboard.planner
        turn = board.step
        shipyard = self.blackboard.shipyard

        if not self.maximum_length:
          self.maximum_length = self.blackboard.not_needed_fleet
          self.maximum_length = get_max_flight_plan(self.blackboard.not_needed_fleet)

        routes = get_all_flight_plans_under_length(self.maximum_length)
        travel_simulations = planner.get_simulations(origin_cell=shipyard.cell, turn=turn, routes=routes)

        high_kore_routes = list(sorted([el for el in travel_simulations if not el.intercepted], key=lambda x: x.mined_kore_per_step, reverse=True))[0:35]  # get higly rewarded routes
        closest_routes = list(sorted([el for el in high_kore_routes], key=lambda x: x.max_dist, reverse=False))[0:10]  # get closest routes
        low_wasted_routes = list(sorted([el for el in closest_routes], key=lambda x: x.empty_cells_ratio, reverse=False))[0:5]  # get routes with lower empty cells count
        selected_route = list(sorted([el for el in low_wasted_routes], key=lambda x: x.same_trajectory_count, reverse=False))

        self.blackboard.selected_route = selected_route
        return common.Status.SUCCESS

    def terminate(self, new_status):
        """
        When is this called?
           Whenever your behaviour switches to a non-running state.
            - SUCCESS || FAILURE : your behaviour's work cycle has finished
            - INVALID : a higher priority branch has interrupted, or shutting down
        """
        self.logger.debug("  %s [Foo::terminate().terminate()][%s->%s]" % (self.name, self.status, new_status))


class IsRoute(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="selected_route", access=common.Access.READ)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        if len(self.blackboard.selected_route):
          return common.Status.SUCCESS
        return common.Status.FAILURE


class LaunchFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="selected_route", access=common.Access.READ)
        self.blackboard.register_key(key="action", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        selected_route = self.blackboard.selected_route[0]
        action = ShipyardAction.launch_fleet_with_flight_plan(selected_route.min_fleet, selected_route.flight_plan)
        self.blackboard.action = action
        return common.Status.SUCCESS


class NotEnoughFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        if self.blackboard.shipyard.ship_count < 21:
            return common.Status.SUCCESS
        return common.Status.FAILURE
