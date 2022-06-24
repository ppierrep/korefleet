from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point


class isIncomingFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="planner", access=common.Access.READ)
        self.blackboard.register_key(key="incoming_fleet_infos", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        planner = self.blackboard.planner
        event = [ev for snap in planner.snapshots.values() for ev in snap.events if ev.event_type == 'shipyard_collision']
        # for the moment shipyard is FFA
        for ev in event:
            if((_id:= self.blackboard.shipyard.id) in ev.actors):

                ally_pos = ev.actors.index(_id)
                ally_fleet_shipcount = ev.actors_shipcount[ally_pos]

                tmp = ev.actors_shipcount.copy()
                tmp.pop(ally_pos)
                ennemy_fleet_shipcount = sum(tmp)

                infos = {
                    'shipyard_id' : _id,
                    'incomming_fleet_number': ennemy_fleet_shipcount,
                    'residing_fleet_number': ally_fleet_shipcount,
                    'eta': ev.turn - self.blackboard.planner.turn,
                    'estimated_victory': ev.shipyard_balance
                }
                self.blackboard.incoming_fleet_infos = infos
                return common.Status.SUCCESS
        
        return common.Status.FAILURE


class EnnemyIsAmmassingFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="board", access=common.Access.READ)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        ennemy_shipyard = [(sy, self.blackboard.shipyard.position.distance_to(sy.position, 21)) for sy in self.blackboard.board.shipyards.values() if sy.player_id != self.blackboard.board.current_player_id]
        ennemy_shipyard = list(sorted(ennemy_shipyard, key=lambda x: x[1]))[0][0]
        if ennemy_shipyard.ship_count > 50:
            return common.Status.SUCCESS
        else:
            return common.Status.FAILURE