'''类声明模块'''

class Vehicle:
    '''车辆类'''
    def __init__(self, type_id, id, capacity_weight, capacity_volume, start_cost):
        '''type_id: 车辆类型, 1,2,3,4,5'''
        self.type_id = type_id # 1,2,3燃油车, 4,5新能源车
        self.vehicle_id = id # 车辆自己的id
        self.capacity_weight = capacity_weight
        self.capacity_volume = capacity_volume
        self.start_cost = start_cost
        self.current_weight = 0.0
        self.current_volume = 0.0


class Customer:
    '''客户类'''
    def __init__(self, id, x, y, timeWindow: list[float]):
        self.id = id
        self.x = x
        self.y = y
        self.timewindow : list[float] = timeWindow

class Order:
    '''订单类'''
    def __init__(self, id, customer_id, weight, volume):
        self.order_id = id
        self.customer_id = customer_id
        self.demand_weight = weight
        self.demand_volume = volume

class Route:
    '''路径类'''
    def __init__(self, vehicle: Vehicle):
        self.nodes = []
        self.times = []
        self.orders : list[list[Order]] = []
        self.distance = []
        self.vehicle : Vehicle = vehicle
        self.cost = 0

