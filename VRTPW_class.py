'''类声明与费用计算模块'''

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

# --- 2. 费用计算辅助逻辑 (外部函数实现) ---

# 常量定义
P_FUEL, P_ELEC, P_CARBON = 7.61, 1.64, 0.65
GAMMA_FV, GAMMA_EV = 2.547, 0.501
C_WAIT, C_LATE = 20, 50  # 元/小时

def get_vehicle_constants(type_id):
    '''查询车型的能耗参数 (假设 1-3 燃油, 4-5 新能源)'''
    if type_id in [1, 2, 3]:
        return 'FV', 0.4, GAMMA_FV, P_FUEL
    return 'EV', 0.35, GAMMA_EV, P_ELEC

def get_e0(energy_type, v_kmh):
    '''计算空载百公里能耗'''
    if energy_type == 'FV':
        return 0.0025 * (v_kmh**2) - 0.2554 * v_kmh + 31.75
    return 0.0014 * (v_kmh**2) - 0.12 * v_kmh + 36.19

def get_travel_info(distance, start_time, current_load, vehicle_capacity, energy_type, alpha, gamma):
    '''分段计算行驶时间、能耗和碳排放'''
    # 速度时段定义 (单位: km/min)
    SPEED_PERIODS = [
        (0, 420, 55.3/60), (420, 540, 9.8/60), (540, 1020, 35.4/60), 
        (1020, 1140, 9.8/60), (1140, 1440, 55.3/60)
    ]
    d_rem, t_curr, total_energy = distance, start_time, 0
    while d_rem > 1e-6:
        v_min, t_end = 0, 1440
        for s_start, s_end, speed in SPEED_PERIODS:
            if s_start <= (t_curr % 1440) < s_end:
                v_min, t_end = speed, s_end
                break
        dt_max = t_end - (t_curr % 1440)
        d_max = dt_max * v_min
        d_seg = min(d_rem, d_max)
        dt_seg = d_seg / v_min if v_min > 0 else 0
        
        # 计算该段能耗
        e0 = get_e0(energy_type, v_min * 60)
        e_actual = e0 * (1 + alpha * (current_load / vehicle_capacity))
        total_energy += e_actual * (d_seg / 100)
        
        d_rem -= d_seg
        t_curr += dt_seg
    return t_curr - start_time, total_energy, total_energy * gamma

# --- 3. 核心费用计算函数 ---

def calc_route_total_cost(route, dist_matrix, customer_pool):
    '''计算某条路径的总花费'''
    if not route.nodes: return 0
    
    # 获取车辆基本参数
    v_type, alpha, gamma, p_energy = get_vehicle_constants(route.vehicle.type_id)
    
    # 初始化状态
    t_curr = 480  # 假设 8:00 出发
    # 适配嵌套列表：计算所有订单的总重量
    current_load = sum(sum(o.demand_weight for o in cust_orders) for cust_orders in route.orders)
    total_energy_cost, total_carbon_cost, total_penalty = 0, 0, 0
    route.times = [t_curr]
    
    customer_idx = 0 # 用于追踪当前是第几个客户点
    for i in range(len(route.nodes) - 1):
        u_id, v_id = route.nodes[i], route.nodes[i+1]
        dist = dist_matrix[u_id][v_id]
        
        # 1. 计算路段行驶 (时间、能耗、碳排)
        dt, energy, carbon = get_travel_info(dist, t_curr, current_load, 
                                            route.vehicle.capacity_weight, v_type, alpha, gamma)
        t_curr += dt
        total_energy_cost += energy * p_energy
        total_carbon_cost += carbon * P_CARBON
        
        # 2. 处理到达节点
        if v_id != 0: # 客户点
            cust = customer_pool[v_id]
            route.times.append(t_curr)
            
            # 时间窗惩罚
            e_i, l_i = cust.timewindow[0], cust.timewindow[1]
            wait = max(0, e_i - t_curr)
            late = max(0, t_curr - l_i)
            total_penalty += (wait/60)*C_WAIT + (late/60)*C_LATE
            
            # 更新离开时间
            t_curr = max(t_curr, e_i) + 20
            
            # 适配嵌套列表：卸下当前客户对应的所有订单
            # route.orders[customer_idx] 存储的是到达 v_id 时的订单列表
            for order in route.orders[customer_idx]:
                current_load -= order.demand_weight
            customer_idx += 1
        else: # 回到中心
            route.times.append(t_curr)
            
    # 计算总花费并赋值
    route.cost = route.vehicle.start_cost + total_energy_cost + total_carbon_cost + total_penalty
    return route.cost

# --- 4. 关于类设计的改进建议 (建议后续重构时参考) ---