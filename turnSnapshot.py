from ast import arg
from typing import *
from kaggle_environments.envs.kore_fleets.helpers import Point, Cell, Direction, Board, PlayerId, Player, FleetId, Fleet, ShipyardId, Shipyard
from kaggle_environments.helpers import Point, group_by, Direction
from copy import deepcopy

from event import Event
from trajectoryPlanner import CollisionAndComeBackRoute


class turnSnapshot(Board):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.events = []

    @staticmethod
    def convert(board: Board) -> 'turnSnapshot':
        actions = [player.next_actions for player in board.players.values()]
        ts = turnSnapshot(board.observation, board.configuration, actions)

        ts._step = board.step
        ts._remaining_overage_time = board._remaining_overage_time
        ts._configuration = board.configuration
        ts._current_player_id = board.current_player_id
        ts._players = board.players  # Dict[PlayerId, Player]
        ts._fleets = board.fleets  # Dict[FleetId, Fleet]
        ts._shipyards = board.shipyards  # Dict[ShipyardId, Shipyard]
        ts._cells = board.cells  # Dict[Point, Cell]

        # Events:
        #       - 
        ts.events = []

        # TODO: better convert custom.__dict__.update(base.__dict__)
        # trajectory = Trajectory(origin_cell=fleet.cell)
        return ts

    def __deepcopy__(self, _) -> 'Board':
        actions = [player.next_actions for player in self.players.values()]
        return turnSnapshot(self.observation, self.configuration, actions)

    def next(self) -> 'turnSnapshot':
        """
        Returns a new board with the current board's next actions applied.
        The current board is unmodified.
        This can form a kore interpreter, e.g.
            next_observation = Board(current_observation, configuration, actions).next().observation
        """
        # Create a copy of the board to modify so we don't affect the current board
        board = deepcopy(self)
        configuration = board.configuration
        convert_cost = configuration.convert_cost
        spawn_cost = configuration.spawn_cost
        uid_counter = 0

        # This is a consistent way to generate unique strings to form fleet and shipyard ids
        def create_uid():
            nonlocal uid_counter
            uid_counter += 1
            return f"{self.step + 1}-{uid_counter}"

        # Process actions and store the results in the fleets and shipyards lists for collision checking
        for player in board.players.values():
            def find_first_non_digit(candidate_str):
                for i in range(len(candidate_str)):
                    if not candidate_str[i].isdigit():
                        return i
                else:
                    return len(candidate_str) + 1
                return 0

            for fleet in player.fleets:
                # remove any errant 0s
                while fleet.flight_plan and fleet.flight_plan.startswith("0"):
                    fleet._flight_plan = fleet.flight_plan[1:]
                if fleet.flight_plan and fleet.flight_plan[0] == "C" and fleet.ship_count >= convert_cost and fleet.cell.shipyard_id is None:
                    player._kore += fleet.kore
                    fleet.cell._kore = 0
                    board._add_shipyard(Shipyard(ShipyardId(create_uid()), fleet.ship_count - convert_cost, fleet.position, player.id, 0, board))
                    board._delete_fleet(fleet)
                    continue

                while fleet.flight_plan and fleet.flight_plan[0] == "C":
                    # couldn't build, remove the Convert and continue with flight plan
                    fleet._flight_plan = fleet.flight_plan[1:]

                if fleet.flight_plan and fleet.flight_plan[0].isalpha():
                    fleet._direction = Direction.from_char(fleet.flight_plan[0])
                    fleet._flight_plan = fleet.flight_plan[1:]
                elif fleet.flight_plan:
                    idx = find_first_non_digit(fleet.flight_plan)
                    digits = int(fleet.flight_plan[:idx])
                    rest = fleet.flight_plan[idx:]
                    digits -= 1
                    if digits > 0:
                        fleet._flight_plan = str(digits) + rest
                    else:
                        fleet._flight_plan = rest

                # continue moving in the fleet's direction
                fleet.cell._fleet_id = None
                fleet._position = fleet.position.translate(fleet.direction.to_point(), configuration.size)
                # We don't set the new cell's fleet_id here as it would be overwritten by another fleet in the case of collision.

            def combine_fleets(fid1: FleetId, fid2: FleetId) -> FleetId:
                f1 = board.fleets[fid1]
                f2 = board.fleets[fid2]
                if f1.less_than_other_allied_fleet(f2):
                    f1, f2 = f2, f1
                    fid1, fid2 = fid2, fid1
                f1._kore += f2.kore
                f1._ship_count += f2._ship_count
                board._delete_fleet(f2)
                return fid1
            
            # resolve any allied fleets that ended up in the same square
            fleets_by_loc = group_by(player.fleets, lambda fleet: fleet.position.to_index(configuration.size))
            for value in fleets_by_loc.values():
                value.sort(key=lambda fleet: (fleet.ship_count, fleet.kore, -fleet.direction.to_index()), reverse=True)
                fid = value[0].id
                for i in range (1, len(value)):
                    fid = combine_fleets(fid, value[i].id)

            # Lets just check and make sure.
            assert player.kore >= 0

        def resolve_collision(fleets: List[Fleet]) -> Tuple[Optional[Fleet], List[Fleet]]:
            """
            Accepts the list of fleets at a particular position (must not be empty).
            Returns the fleet with the most ships or None in the case of a tie along with all other fleets.
            """
            if len(fleets) == 1:
                return fleets[0], []
            fleets_by_ships = group_by(fleets, lambda fleet: fleet.ship_count)
            most_ships = max(fleets_by_ships.keys())
            largest_fleets = fleets_by_ships[most_ships]
            if len(largest_fleets) == 1:
                # There was a winner, return it
                winner = largest_fleets[0]
                return winner, [fleet for fleet in fleets if fleet != winner]
            # There was a tie for most ships, all are deleted
            return None, fleets

        # Check for fleet to fleet collisions
        fleet_collision_groups = group_by(board.fleets.values(), lambda fleet: fleet.position)
        for position, collided_fleets in fleet_collision_groups.items():
            winner, deleted = resolve_collision(collided_fleets)
            shipyard = group_by(board.shipyards.values(), lambda shipyard: shipyard.position).get(position)

            event = Event(actors=[f.id for f in collided_fleets], actors_shipcount=[f.ship_count for f in collided_fleets], event_type='collision', turn=self.step, position=position)
            if winner is not None:
                winner.cell._fleet_id = winner.id
                max_enemy_size = max([fleet.ship_count for fleet in deleted]) if deleted else 0
                winner._ship_count -= max_enemy_size

            for fleet in deleted:
                board._delete_fleet(fleet)
                event.fleet_balance += -1 if fleet.player_id == self.current_player_id else 1
                if winner is not None:
                    # Winner takes deleted fleets' kore
                    winner._kore += fleet.kore
                    event.kore_balance += fleet.kore if winner.player_id == self.current_player_id else -fleet.kore
                elif winner is None and shipyard and shipyard[0].player:
                    # Desposit the kore into the shipyard
                    shipyard[0].player._kore += fleet.kore
                    event.deposited_kore += fleet.kore if shipyard[0].player.id == self.current_player_id else -fleet.kore
                    event.kore_balance += 0 if shipyard[0].player.id == self.current_player_id else -fleet.kore
                elif winner is None:
                    # Desposit the kore on the square
                    board.cells[position]._kore += fleet.kore
            
            if len(collided_fleets) > 1:
                board.events.append(event)


        # Check for fleet to shipyard collisions
        for shipyard in list(board.shipyards.values()):
            fleet = shipyard.cell.fleet
            if fleet is not None and fleet.player_id != shipyard.player_id:
                event = Event(actors=[fleet.id, shipyard.id], actors_shipcount=[f.ship_count for f in [fleet, shipyard]], event_type='shipyard_collision', turn=self.step, position=shipyard.cell.position)
                if fleet.ship_count > shipyard.ship_count:
                    count = fleet.ship_count - shipyard.ship_count
                    board._delete_shipyard(shipyard)
                    board._add_shipyard(Shipyard(ShipyardId(create_uid()), count, shipyard.position, fleet.player.id, 1, board))
                    fleet.player._kore += fleet.kore
                    board._delete_fleet(fleet)
                    
                    event.deposited_kore += fleet.kore if fleet.player.id == self.current_player_id else -fleet.kore
                    event.kore_balance += 0 if fleet.player.id == self.current_player_id else -fleet.kore
                    event.shipyard_balance += 1 if fleet.player.id == self.current_player_id else -1
                    event.fleet_balance += -1 if fleet.player.id == self.current_player_id else 1
                else:
                    shipyard._ship_count -= fleet.ship_count
                    shipyard.player._kore += fleet.kore
                    board._delete_fleet(fleet)

                    event.deposited_kore += -fleet.kore if fleet.player.id == self.current_player_id else fleet.kore
                    event.kore_balance += -fleet.kore if fleet.player.id == self.current_player_id else 0
                    event.fleet_balance += -1 if fleet.player.id == self.current_player_id else 1
                board.events.append(event)

        # Deposit kore from fleets into shipyards
        for shipyard in list(board.shipyards.values()):
            fleet = shipyard.cell.fleet
            if fleet is not None and fleet.player_id == shipyard.player_id:
                event = Event(actors=[fleet.id, shipyard.id], actors_shipcount=[f.ship_count for f in [fleet, shipyard]], event_type='kore_deposit', turn=self.step, position=shipyard.cell.position)
                shipyard.player._kore += fleet.kore
                shipyard._ship_count += fleet.ship_count
                board._delete_fleet(fleet)
                
                event.deposited_kore += fleet.kore if fleet.player_id == self.current_player_id else -fleet.kore
                board.events.append(event)

        # apply fleet to fleet damage on all orthagonally adjacent cells
        incoming_fleet_dmg = DefaultDict(lambda: DefaultDict(int))
        for fleet in board.fleets.values():
            for direction in Direction.list_directions():
                curr_pos = fleet.position.translate(direction.to_point(), board.configuration.size)
                fleet_at_pos = board.get_fleet_at_point(curr_pos)
                if fleet_at_pos and not fleet_at_pos.player_id == fleet.player_id:
                    incoming_fleet_dmg[fleet_at_pos.id][fleet.id] = fleet.ship_count

        # dump 1/2 kore to the cell of killed fleets
        # mark the other 1/2 kore to go to surrounding fleets proportionally
        to_distribute = DefaultDict(lambda: DefaultDict(int))
        for fleet_id, fleet_dmg_dict in incoming_fleet_dmg.items():
            fleet = board.fleets[fleet_id]
            damage = sum(fleet_dmg_dict.values())
            event = Event(
                actors=[fleet.id] + [fid for fid in fleet_dmg_dict.keys()],
                actors_shipcount=[fleet.ship_count] + [f for f in fleet_dmg_dict.values()],
                event_type='adjacent_combat',
                turn=self.step,
                position=fleet.cell.position
            )
            if damage >= fleet.ship_count:
                fleet.cell._kore += fleet.kore / 2
                to_split = fleet.kore / 2
                for f_id, dmg in fleet_dmg_dict.items():
                    to_distribute[f_id][fleet.position.to_index(board.configuration.size)] = to_split * dmg/damage
                board._delete_fleet(fleet)

                event.fleet_balance += 1 if fleet.player_id != self.current_player_id else -1
                # TODO find usage for damage since it is reciprocal
            else:
                fleet._ship_count -= damage
            
            board.events.append(event)

        # give kore claimed above to surviving fleets, otherwise add it to the kore of the tile where the fleet died
        for fleet_id, loc_kore_dict in to_distribute.items():
            fleet = board.fleets.get(fleet_id)
            if fleet:
                fleet._kore += sum(loc_kore_dict.values())
            else:
                for loc_idx, kore in loc_kore_dict.items():
                    board.cells.get(Point.from_index(loc_idx, board.configuration.size))._kore += kore

        # Collect kore from cells into fleets
        for fleet in board.fleets.values():
            cell = fleet.cell
            delta_kore = round(cell.kore * min(fleet.collection_rate, .99), 3)
            if delta_kore > 0:
                fleet._kore += delta_kore
                cell._kore -= delta_kore

        # Regenerate kore in cells
        for cell in board.cells.values():
            if cell.fleet_id is None and cell.shipyard_id is None:
                if cell.kore < configuration.max_cell_kore:
                    next_kore = round(cell.kore * (1 + configuration.regen_rate), 3)
                    cell._kore = next_kore

        board._step += 1

        return board
