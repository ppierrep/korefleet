import math


def get_max_flight_plan(ship_number):
    return math.floor(2 * math.log(ship_number)) + 1


