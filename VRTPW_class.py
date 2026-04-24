'''类声明模块'''

class Vehicle:
    '''车辆类'''
    def __init__(self, type_id, capacity_weight, capacity_volume, start_cost=400):
        self.type_id = type_id
        self.capacity_weight = capacity_weight
        self.capacity_volume = capacity_volume
        self.start_cost = start_cost
        self.current_weight = 0
        self.current_volume = 0

class Customer:
    '''客户类'''
    def __init__(self, id, x, y, timeWindow):
        self.customer_id = id
        self.x = x
        self.y = y
        self.timewindow = timeWindow

class Order:
    '''订单类'''
    def __init__(self, id, customer_id, weight, volume):
        self.order_id = id
        self.customer_id = customer_id
        self.demand_weight = weight
        self.demand_volume = volume

class Route:
    '''路径类'''
    def __init__(self, vehicle):
        self.nodes = []
        self.times = []
        self.orders = []
        self.length = []
        self.vehicle = vehicle
        self.cost = 0

