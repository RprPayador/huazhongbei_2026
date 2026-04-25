'''类声明模块'''

class Vehicle:
    '''车辆类'''
    def __init__(self, type):
        '''type: 车辆类型, 0,1,2,3,4'''
        self.start_cost = 400
        self.current_weight = 0.0
        self.current_volume = 0.0
        if(type == 0):
            self.type_id = 0 # 0燃油车, 1新能源车
            self.capacity_weight = 3000
            self.capacity_volume = 13.5
        elif(type == 2):pass
        elif(type == 3):pass
        elif(type == 4):pass
        elif(type == 5):pass
        else:pass

class Customer:
    '''客户类'''
    def __init__(self, id, x, y, timeWindow: list[float]):
        self.customer_id = id
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
        self.orders = []
        self.distance = []
        self.vehicle : Vehicle = vehicle
    def __init__(self, vehicle):
        self.nodes = []
        self.times = []
        self.orders = []
        self.length = []
        self.vehicle = vehicle
        self.cost = 0

