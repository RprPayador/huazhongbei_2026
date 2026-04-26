'''ALNS(自适应大邻域搜索)算法模块'''

import numpy as np
from VRTPW_class import *

class Solution:
    '''解法类'''
    def __init__(self):
        self.routes : list[Route] = [] # 所有路径列表
        self.vehiclesTimeTable : dict[int, list] = {} # 车辆时间表, key是车辆编号, value是车辆的时间表
        self.order2routeMap : dict[int, int] = {} # 订单到路径的映射, key是订单编号, value是routes的索引值
        self.unassignedOrders : list[Order] = [] # 未分配的订单列表

    def initSolution(self, vehicle_pool: list[Vehicle], customer_pool: dict[int, Customer], order_pool: list[Order], dist_matrix: np.ndarray):
        '''初始化解法函数：生成初始解

        算法步骤：
        1. 以早上八点(480分钟)为最早发车时间，初始化self.unassignedOrders为order_pool
        2. 优先使用载重最大的新能源车，在self.vehiclesTimeTable中筛选当前车辆可用的时段
        3. 新建Route实例，从配送中心出发，在customer_pool中寻找时间窗内的且最近的客户
        4. 当前Route满载后，返回配送中心，将Route添加到self.routes列表中，更新self.vehiclesTimeTable
        5. 重复2~4，直到全天排满或没有可送订单
        6. 当self.unassignedOrders为空，初始解求取完成
        '''
        DEPARTURE_TIME = 480
        SERVICE_TIME = 20
        DEPOT_ID = 0

        self.unassignedOrders = order_pool.copy()

        ev_vehicles = [v for v in vehicle_pool if v.type_id in [4, 5]]
        fv_vehicles = [v for v in vehicle_pool if v.type_id in [1, 2, 3]]
        ev_vehicles.sort(key=lambda v: v.capacity_weight, reverse=True)
        fv_vehicles.sort(key=lambda v: v.capacity_weight, reverse=True)
        all_vehicles = ev_vehicles + fv_vehicles

        for v in vehicle_pool:
            self.vehiclesTimeTable[v.vehicle_id] = []

        available_orders = self.unassignedOrders.copy()

        # 初始化客户订单字典
        customer_orders = {}
        for cid in customer_pool.keys():
            if cid == DEPOT_ID:
                continue
            customer_orders[cid] = []

        # 填充客户订单
        for order in available_orders:
            cid = order.customer_id
            if cid in customer_orders:
                customer_orders[cid].append(order)

        def get_available_time(vehicle):
            time_slots = self.vehiclesTimeTable.get(vehicle.vehicle_id, [])
            if not time_slots:
                return DEPARTURE_TIME
            last_slot = time_slots[-1]
            return last_slot[1]

        def get_best_customer(vehicle, current_node, current_time, current_weight, current_volume):
            best_customer = None
            best_order_count = 0
            min_distance = float('inf')

            for cid, orders in customer_orders.items():
                if not orders:
                    continue

                customer = customer_pool[cid]
                tw_start, tw_end = customer.timewindow

                total_weight = sum(o.demand_weight for o in orders)
                total_volume = sum(o.demand_volume for o in orders)

                if current_weight + total_weight > vehicle.capacity_weight:
                    continue
                if current_volume + total_volume > vehicle.capacity_volume:
                    continue

                travel_dist = dist_matrix[current_node][cid]
                travel_time = travel_dist / 35.0 * 60
                arrival_time = current_time + travel_time

                if arrival_time > tw_end:
                    continue

                if arrival_time < tw_start:
                    arrival_time = tw_start

                arrival_time += SERVICE_TIME

                if arrival_time > tw_end:
                    continue

                if len(orders) > best_order_count or (len(orders) == best_order_count and travel_dist < min_distance):
                    best_order_count = len(orders)
                    min_distance = travel_dist
                    best_customer = cid

            return best_customer, min_distance

        for vehicle in all_vehicles:
            vehicle.current_weight = 0.0
            vehicle.current_volume = 0.0

            available_time = get_available_time(vehicle)

            while available_time < 1440 and available_orders:
                route = Route(vehicle)
                route.nodes.append(DEPOT_ID)
                route.times.append(available_time)

                current_node = DEPOT_ID
                current_time = available_time
                current_weight = 0.0
                current_volume = 0.0

                route_full = False

                while not route_full:
                    next_cid, _ = get_best_customer(
                        vehicle, current_node, current_time, current_weight, current_volume
                    )

                    if next_cid is None:
                        route_full = True
                        continue

                    customer = customer_pool[next_cid]
                    orders_to_deliver = customer_orders[next_cid]

                    travel_dist = dist_matrix[current_node][next_cid]
                    travel_time = travel_dist / 35.0 * 60
                    arrival_time = current_time + travel_time

                    tw_start, _ = customer.timewindow
                    if arrival_time < tw_start:
                        arrival_time = tw_start

                    route.nodes.append(next_cid)
                    route.times.append(arrival_time)

                    # 修改为嵌套结构：一次性添加该客户的所有订单
                    route.orders.append(list(orders_to_deliver))
                    
                    for order in orders_to_deliver:
                        # 记录订单到路径索引的映射
                        self.order2routeMap[order.order_id] = len(self.routes)
                        current_weight += order.demand_weight
                        current_volume += order.demand_volume
                        if order in available_orders:
                            available_orders.remove(order)

                    # 清空该客户的订单列表，避免重复选择
                    customer_orders[next_cid] = []

                    current_node = next_cid
                    current_time = arrival_time + SERVICE_TIME

                    if current_weight >= vehicle.capacity_weight * 0.95:
                        route_full = True
                    if current_volume >= vehicle.capacity_volume * 0.95:
                        route_full = True

                    if current_time >= 1440:
                        route_full = True

                if len(route.nodes) > 1:
                    return_dist = dist_matrix[current_node][DEPOT_ID]
                    return_time = return_dist / 35.0 * 60
                    arrival_at_depot = current_time + return_time

                    route.nodes.append(DEPOT_ID)
                    route.times.append(arrival_at_depot)

                    route.distance = []
                    for i in range(len(route.nodes) - 1):
                        route.distance.append(dist_matrix[route.nodes[i]][route.nodes[i+1]])

                    route.cost = 0

                    self.routes.append(route)

                    vehicle.current_weight = current_weight
                    vehicle.current_volume = current_volume

                    self.vehiclesTimeTable[vehicle.vehicle_id].append((available_time, arrival_at_depot))
                    available_time = arrival_at_depot
                else:
                    break

            if not available_orders:
                break

        self.unassignedOrders = available_orders