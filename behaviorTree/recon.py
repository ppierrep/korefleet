from itertools import groupby
from numpy import number
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

class FindRaidingCandidates(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)

        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="planner", access=common.Access.READ)
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="board", access=common.Access.READ)

        self.blackboard.register_key(key="raid_candidates", access=common.Access.WRITE)
        # self.blackboard.register_key()
    
    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        planner = self.blackboard.planner
        ennemy_shipyards = [shipyard for snap in planner.snapshots.values() for shipyard in snap.shipyards.values() if shipyard.player_id != self.blackboard.board.current_player_id]
        ennemy_max_activity = [(_id, sorted(v, key=lambda x: x.ship_count, reverse=True)[0]) for _id, v in groupby(ennemy_shipyards, key=lambda x: x.id)]  # Get max shipcount per shipyard through the snapshots
        
        candidates = []
        # select candidates
        for shipyard_id, shipyard in ennemy_max_activity:
            # should pass several criterion: should be in range for an attack, its regeneration potential has to be strickly lower than our fleet
            current_ship_count = self.blackboard.shipyard.ship_count
            dist = self.blackboard.shipyard.position.distance_to(shipyard.position, size=21)

            # TODO: Theorically, we have to take into account: ship refueling and max spawn increasing
            expected_ship_count = shipyard.ship_count + dist * shipyard.max_spawn

            if expected_ship_count < current_ship_count:
                candidates.append((shipyard.position, dist, expected_ship_count))
        
        self.blackboard.raid_candidates = candidates
        return common.Status.SUCCESS if len(self.blackboard.raid_candidates) else common.Status.FAILURE


class MoreFleet(behaviour.Behaviour):
    def __init__(self, name, by):
        super().__init__(name)
        self.number = by
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="me", access=common.Access.READ)
        self.blackboard.register_key(key="board", access=common.Access.READ)
    
    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        ennemy_player = self.blackboard.board.players[[_id for _id in self.blackboard.board.players.keys() if _id != self.blackboard.board.current_player_id][0]]
        ennemy_fleet_count = sum([self.blackboard.board.fleets[_id].ship_count for _id in ennemy_player.fleet_ids])
        my_fleet_count = sum([self.blackboard.board.fleets[_id].ship_count for _id in self.blackboard.me.fleet_ids])

        return common.Status.SUCCESS if ennemy_fleet_count <= my_fleet_count - self.number else common.Status.FAILURE