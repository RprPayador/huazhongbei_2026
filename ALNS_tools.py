'''ALNS(自适应大邻域搜索)算法模块'''

import numpy as np
from VRTPW_class import *
import numpy as np
import pandas as pd

class Solution:
    '''解法类'''
    def __init__(self):
        self.routes : list[Route] = [] # 所有路径列表
        self.vehiclesTimeTable : dict[int, list[tuple]] = {} # 车辆时间表, key是车辆编号, value是车辆的时间表
        self.order2routeMap : dict[int, int] = {} # 订单到路径的映射, key是订单编号, value是routes的索引值
        self.unassignedOrders : list[Order] = [] # 未分配的订单列表
        self.total_cost : float = 0.0 # 全局总费用

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

        self.unassignedOrders = list(order_pool)

        ev_vehicles = [v for v in vehicle_pool if v.type_id in [4, 5]]
        fv_vehicles = [v for v in vehicle_pool if v.type_id in [1, 2, 3]]
        ev_vehicles.sort(key=lambda v: (v.capacity_weight, v.type_id), reverse=True)
        fv_vehicles.sort(key=lambda v: (v.capacity_weight, v.type_id), reverse=True)

        for v in vehicle_pool:
            self.vehiclesTimeTable[v.vehicle_id] = []

        available_orders = list(self.unassignedOrders)

        customer_orders = {}
        for cid in customer_pool.keys():
            if cid == DEPOT_ID:
                continue
            customer_orders[cid] = []

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

        def calculate_time_penalty(arrival_time, tw_start, tw_end):
            if arrival_time < tw_start:
                return (tw_start - arrival_time) * 2  # 早到权重为2
            elif arrival_time > tw_end:
                return (arrival_time - tw_end) * 5  # 迟到权重为5
            else:
                return 0

        def get_best_customer(vehicle, current_node, current_time, current_weight, current_volume):
            best_customer = None
            best_penalty = float('inf')
            best_order_count = 0
            best_departure_time = current_time

            for cid, orders in customer_orders.items():
                if not orders:
                    continue

                customer = customer_pool[cid]
                tw_start, tw_end = customer.timewindow

                travel_dist = dist_matrix[current_node][cid]
                travel_time = travel_dist / 35.0 * 60
                
                # 计算理论到达时间
                arrival_time = current_time + travel_time
                
                # 计算时间惩罚
                penalty = calculate_time_penalty(arrival_time, tw_start, tw_end)
                
                # 计算实际发车时间（如果早到，反推发车时间）
                actual_departure_time = current_time
                if arrival_time < tw_start:
                    # 反推发车时间，使其刚好在时间窗开始时到达
                    actual_departure_time = max(current_time, tw_start - travel_time)
                    arrival_time = tw_start
                
                # 计算服务完成时间
                service_completion_time = arrival_time + SERVICE_TIME
                
                # 检查服务完成时间是否超出时间窗
                if service_completion_time > tw_end:
                    # 计算服务完成时间的惩罚
                    service_penalty = calculate_time_penalty(service_completion_time, tw_start, tw_end)
                    penalty = max(penalty, service_penalty)
                
                # 计算订单数量
                order_count = len(orders)
                
                # 选择最佳客户：优先考虑惩罚最小，其次订单数量最多
                if (penalty < best_penalty) or \
                   (penalty == best_penalty and order_count > best_order_count):
                    best_penalty = penalty
                    best_order_count = order_count
                    best_customer = cid
                    best_departure_time = actual_departure_time

            return best_customer, best_departure_time

        route_index = 0

        def process_vehicle(vehicle):
            nonlocal route_index, available_orders
            available_time = get_available_time(vehicle)
            route_count = 0

            while available_time < 1440 and available_orders and route_count < 5:  # 限制每辆车的路径数
                # 获取最佳发车时间
                best_departure_time = available_time
                
                # 创建新路径
                route = Route(vehicle)
                route.nodes.append(DEPOT_ID)
                route.times.append(best_departure_time)

                current_node = DEPOT_ID
                current_time = best_departure_time
                current_weight = 0.0
                current_volume = 0.0

                route_full = False

                while not route_full:
                    # 获取最佳客户和实际发车时间
                    next_cid, actual_departure_time = get_best_customer(
                        vehicle, current_node, current_time, current_weight, current_volume
                    )

                    if next_cid is None:
                        route_full = True
                        continue

                    customer = customer_pool[next_cid]
                    orders_at_customer = customer_orders[next_cid]

                    # 计算实际出发时间
                    if current_node == DEPOT_ID:
                        # 如果从配送中心出发，使用计算出的实际发车时间
                        current_time = actual_departure_time
                        # 更新路径的出发时间
                        route.times[0] = current_time

                    # 分配订单：能处理多少就处理多少
                    orders_to_deliver = []
                    temp_weight = current_weight
                    temp_volume = current_volume

                    for order in orders_at_customer:
                        if pd.isna(order.demand_weight) or pd.isna(order.demand_volume):
                            continue

                        # 检查是否超过车辆容量（不超过100%）
                        if temp_weight + order.demand_weight <= vehicle.capacity_weight and \
                           temp_volume + order.demand_volume <= vehicle.capacity_volume:
                            orders_to_deliver.append(order)
                            temp_weight += order.demand_weight
                            temp_volume += order.demand_volume
                        else:
                            # 不能再装更多订单，停止分配
                            break

                    if not orders_to_deliver:
                        route_full = True
                        continue

                    # 计算行驶时间和到达时间
                    travel_dist = dist_matrix[current_node][next_cid]
                    travel_time = travel_dist / 35.0 * 60
                    arrival_time = current_time + travel_time

                    # 处理时间窗
                    tw_start, tw_end = customer.timewindow
                    if arrival_time < tw_start:
                        # 早到，等待到时间窗开始
                        arrival_time = tw_start
                    # 迟到的情况也接受，会在惩罚函数中体现

                    # 更新路径信息
                    route.nodes.append(next_cid)
                    route.times.append(arrival_time)
                    route.orders.append(orders_to_deliver)

                    # 更新订单分配信息
                    for order in orders_to_deliver:
                        self.order2routeMap[order.order_id] = route_index
                        current_weight += order.demand_weight
                        current_volume += order.demand_volume
                        if order in available_orders:
                            available_orders.remove(order)
                        if order in customer_orders[next_cid]:
                            customer_orders[next_cid].remove(order)

                    # 更新当前状态
                    current_node = next_cid
                    current_time = arrival_time + SERVICE_TIME

                    # 检查是否达到容量或时间限制
                    if current_weight >= vehicle.capacity_weight:
                        route_full = True
                    if current_volume >= vehicle.capacity_volume:
                        route_full = True
                    if current_time >= 1440:
                        route_full = True

                # 如果路径有客户节点，返回配送中心
                if len(route.nodes) > 1:
                    return_dist = dist_matrix[current_node][DEPOT_ID]
                    return_time = return_dist / 35.0 * 60
                    arrival_at_depot = current_time + return_time

                    route.nodes.append(DEPOT_ID)
                    route.times.append(arrival_at_depot)

                    # 计算路径距离
                    route.distance = []
                    for i in range(len(route.nodes) - 1):
                        route.distance.append(dist_matrix[route.nodes[i]][route.nodes[i+1]])

                    route.cost = 0

                    # 添加路径到解决方案
                    self.routes.append(route)

                    # --- 关键：立即同步真实时间 ---
                    # 这一步会根据分段速度模型重写 route.times
                    from VRTPW_class import calc_route_total_cost
                    calc_route_total_cost(route, dist_matrix, customer_pool)

                    # 更新车辆属性
                    vehicle.current_weight = current_weight
                    vehicle.current_volume = current_volume

                    # 更新车辆时间表（使用同步后的真实时间）
                    self.vehiclesTimeTable.setdefault(vehicle.vehicle_id, []).append((route.times[0], route.times[-1]))
                    
                    available_time = route.times[-1] # 下一次的可用时间也用真实回程时间
                    route_index += 1
                    route_count += 1
                else:
                    break

        # 处理车辆的主循环，直到所有订单都被分配
        total_orders = len(order_pool)
        
        # 处理新能源车
        ev_processed = set()
        
        # 循环处理新能源车，直到所有新能源车都被充分利用或无订单可分配
        while available_orders:
            ev_used = False
            for vehicle in ev_vehicles:
                if not available_orders:
                    break
                
                # 检查车辆是否还有可用时间
                available_time = get_available_time(vehicle)
                if available_time >= 1440:
                    if vehicle.vehicle_id not in ev_processed:
                        ev_processed.add(vehicle.vehicle_id)
                    continue
                
                # 处理车辆
                original_order_count = len(available_orders)
                process_vehicle(vehicle)
                
                if len(available_orders) < original_order_count:
                    ev_used = True
            
            # 如果没有新能源车可以处理订单了，退出循环
            if not ev_used:
                break

        # 再次检查新能源车
        while available_orders:
            ev_used = False
            for vehicle in ev_vehicles:
                if not available_orders:
                    break
                
                # 检查车辆是否还有可用时间
                available_time = get_available_time(vehicle)
                if available_time < 1440:
                    # 处理车辆
                    original_order_count = len(available_orders)
                    process_vehicle(vehicle)
                    
                    if len(available_orders) < original_order_count:
                        ev_used = True
            
            # 如果没有新能源车可以处理订单了，退出循环
            if not ev_used:
                break

        # 处理燃油车
        # 只有当所有新能源车都处理完毕后，才开始处理燃油车
        for vehicle in fv_vehicles:
            if not available_orders:
                break
            process_vehicle(vehicle)
        # 再次检查燃油车
        while available_orders:
            fv_used = False
            for vehicle in fv_vehicles:
                if not available_orders:
                    break
                
                # 检查车辆是否还有可用时间
                available_time = get_available_time(vehicle)
                if available_time < 1440:
                    # 处理车辆
                    original_order_count = len(available_orders)
                    process_vehicle(vehicle)
                    
                    if len(available_orders) < original_order_count:
                        fv_used = True
            
            # 如果没有燃油车可以处理订单了，退出循环
            if not fv_used:
                break

        # 最终检查：确保所有订单都被分配
        if available_orders:
            # 尝试为剩余订单分配车辆，不考虑时间窗约束
            for order in available_orders[:]:
                # 找到第一个有可用时间的车辆
                assigned = False
                for vehicle in ev_vehicles + fv_vehicles:
                    available_time = get_available_time(vehicle)
                    if available_time < 1440:
                        # 创建只包含这一个订单的路径
                        route = Route(vehicle)
                        route.nodes.append(DEPOT_ID)
                        route.times.append(available_time)
                        
                        current_node = DEPOT_ID
                        current_time = available_time
                        current_weight = 0.0
                        current_volume = 0.0
                        
                        # 计算到客户的时间
                        cid = order.customer_id
                        customer = customer_pool[cid]
                        travel_dist = dist_matrix[current_node][cid]
                        travel_time = travel_dist / 35.0 * 60
                        arrival_time = current_time + travel_time
                        
                        # 处理时间窗（即使超出也接受）
                        tw_start, tw_end = customer.timewindow
                        if arrival_time < tw_start:
                            arrival_time = tw_start
                        
                        # 添加客户节点
                        route.nodes.append(cid)
                        route.times.append(arrival_time)
                        route.orders.append([order])
                        
                        # 更新订单分配信息
                        self.order2routeMap[order.order_id] = route_index
                        current_weight += order.demand_weight
                        current_volume += order.demand_volume
                        available_orders.remove(order)
                        if order in customer_orders.get(cid, []):
                            customer_orders[cid].remove(order)
                        
                        # 返回配送中心
                        return_dist = dist_matrix[cid][DEPOT_ID]
                        return_time = return_dist / 35.0 * 60
                        arrival_at_depot = arrival_time + SERVICE_TIME + return_time
                        
                        route.nodes.append(DEPOT_ID)
                        route.times.append(arrival_at_depot)
                        
                        # 计算路径距离
                        route.distance = []
                        for i in range(len(route.nodes) - 1):
                            route.distance.append(dist_matrix[route.nodes[i]][route.nodes[i+1]])
                        
                        route.cost = 0
                        
                        # 添加路径到解决方案
                        self.routes.append(route)
                        
                        # 更新车辆属性
                        vehicle.current_weight = current_weight
                        vehicle.current_volume = current_volume
                        
                        # 更新车辆时间表
                        self.vehiclesTimeTable[vehicle.vehicle_id].append((available_time, arrival_at_depot))
                        
                        route_index += 1
                        assigned = True
                        break
                
                if not assigned:
                    # 如果没有车辆可用，创建新的路径（即使时间超出）
                    print(f"  警告：无法分配订单 {order.order_id}")

        self.unassignedOrders = available_orders
        print(f"\n成功求取初始解")
        print(f"总订单数: {total_orders}")
        print(f"已分配订单数: {len(self.order2routeMap)}")
        print(f"未分配订单数: {len(self.unassignedOrders)}")

        # 重建 order2routeMap 并用真实计费函数算总费用
        self.order2routeMap.clear()
        dist_matrix_safe = np.nan_to_num(dist_matrix.astype(float))
        for r_idx, route in enumerate(self.routes):
            for sublist in route.orders:
                for order in sublist:
                    self.order2routeMap[order.order_id] = r_idx
            calc_route_total_cost(route, dist_matrix_safe, customer_pool)
        self.total_cost = sum(r.cost for r in self.routes)
