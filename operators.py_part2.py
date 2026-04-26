# ==============================================================================
# 问题 2：环保政策限行专用算子
# ==============================================================================

def is_illegal_stop(node_id, arrival_time, vehicle_type, customer_pool):
    """判定一个停靠点是否违反限行政策"""
    if node_id == 0: return False # 配送中心不限行
    # 燃油车 (1,2,3) 在 8:00-16:00 (480-960) 禁止进入绿区
    if vehicle_type <= 3:
        if 480 <= arrival_time <= 960:
            c = customer_pool.get(node_id)
            if c:
                dist_to_center = ((c.x - 20)**2 + (c.y - 20)**2)**0.5
                if dist_to_center <= 10:
                    return True
    return False

def policy_violation_removal(solution, customer_pool):
    """特殊的破坏算子：剔除所有违反限行政策的订单"""
    removed_order_ids = []
    # 遍历所有路径
    for route in solution.routes:
        v_type = route.vehicle.type_id
        if v_type > 3: continue # 新能源车不限行
        
        # 记录需要移除的节点索引
        to_remove_indices = []
        for i in range(1, len(route.nodes) - 1):
            node_id = route.nodes[i]
            arrival_time = route.times[i]
            if is_illegal_stop(node_id, arrival_time, v_type, customer_pool):
                to_remove_indices.append(i)
        
        for idx in reversed(to_remove_indices):
            # 获取该停靠点的所有订单 ID
            orders_at_stop = route.orders[idx-1]
            for o in orders_at_stop:
                removed_order_ids.append(o.order_id)
                solution.unassignedOrders.append(o)
                if o.order_id in solution.order2routeMap:
                    solution.order2routeMap.pop(o.order_id)
            route.nodes.pop(idx)
            route.orders.pop(idx-1)
            
    # 物理移除空路径
    solution.routes = [r for r in solution.routes if len(r.orders) > 0]
    for route in solution.routes:
        route.times = []
        route.cost = 0
    return removed_order_ids

def _check_route_legality_p2(route, dist_matrix, customer_pool):
    """检查一整条路径是否合法（P2 政策）"""
    if route.vehicle.type_id > 3: return True 
    from VRTPW_class import calc_route_total_cost
    
    # 尝试 1：常规出发 (通常是 08:00)
    calc_route_total_cost(route, dist_matrix, customer_pool)
    is_legal = True
    for i in range(1, len(route.nodes) - 1):
        if is_illegal_stop(route.nodes[i], route.times[i], route.vehicle.type_id, customer_pool):
            is_legal = False; break
    if is_legal: return True
    
    # 尝试 2：16:00 延迟出发
    original_times = route.times[:]
    route.times = [960.0] 
    calc_route_total_cost(route, dist_matrix, customer_pool)
    
    is_legal = True
    if route.times[-1] > 1440: # 凌晨之前必须回来
        is_legal = False
    else:
        for i in range(1, len(route.nodes) - 1):
            if is_illegal_stop(route.nodes[i], route.times[i], route.vehicle.type_id, customer_pool):
                is_legal = False; break
    if not is_legal: route.times = original_times
    return is_legal

def greedy_repair_p2(solution, dist_matrix, customer_pool, vehicle_pool):
    """带限行约束的贪婪修复算子"""
    from VRTPW_class import calc_route_total_cost
    unassigned = solution.unassignedOrders[:]
    solution.unassignedOrders = []
    
    for order in unassigned:
        best_cost_gain = float('inf')
        best_insert = None 
        
        for r in solution.routes:
            for i in range(len(r.nodes) - 1):
                old_nodes, old_orders, old_cost = r.nodes[:], r.orders[:], r.cost
                target_node = order.customer_id
                node_exists_at_i = (i+1 < len(r.nodes)-1 and r.nodes[i+1] == target_node)
                
                if node_exists_at_i: r.orders[i].append(order)
                else:
                    r.nodes.insert(i+1, target_node)
                    r.orders.insert(i, [order])
                
                # 校验：载重 (修正属性名为 weight 和 volume)
                cur_w = sum(sum(o.weight for o in stop) for stop in r.orders)
                cur_v = sum(sum(o.volume for o in stop) for stop in r.orders)
                
                if cur_w > r.vehicle.capacity_weight or cur_v > r.vehicle.capacity_volume:
                    legal = False
                else:
                    legal = _check_route_legality_p2(r, dist_matrix, customer_pool)
                
                if legal:
                    gain = r.cost - old_cost
                    if gain < best_cost_gain:
                        best_cost_gain = gain
                        best_insert = (r, i, node_exists_at_i)
                
                # 还原现场
                r.nodes, r.orders, r.cost, r.times = old_nodes, old_orders, old_cost, []
        
        if best_insert is None:
            used_vids = {r.vehicle.vehicle_id for r in solution.routes}
            for bv in vehicle_pool:
                if bv.vehicle_id not in used_vids:
                    # 载重预检
                    if order.weight > bv.capacity_weight or order.volume > bv.capacity_volume: continue
                    new_r = Route(bv)
                    new_r.nodes, new_r.orders = [0, order.customer_id, 0], [[order]]
                    if _check_route_legality_p2(new_r, dist_matrix, customer_pool):
                        solution.routes.append(new_r)
                        solution.order2routeMap[order.order_id] = len(solution.routes)-1
                        best_insert = "NEW"; break
        
        if best_insert:
            if best_insert == "NEW":
                # 已在创建时处理过 solution.routes 和 Map
                pass
            else:
                r, pos, exists = best_insert
                if exists: r.orders[pos].append(order)
                else:
                    r.nodes.insert(pos+1, order.customer_id)
                    r.orders.insert(pos, [order])
                # 最终确认时间表
                _check_route_legality_p2(r, dist_matrix, customer_pool)
                solution.order2routeMap[order.order_id] = solution.routes.index(r)
        else:
            solution.unassignedOrders.append(order)

def regret_repair_p2(solution, dist_matrix, customer_pool, vehicle_pool):
    """这里简单复用贪婪逻辑，实际可扩展为多级 Regret 逻辑"""
    greedy_repair_p2(solution, dist_matrix, customer_pool, vehicle_pool)
