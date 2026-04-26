import random
import copy
import numpy as np
from ALNS_tools import Solution
from VRTPW_class import *

def _rebuild_maps_and_costs(solution: Solution, dist_matrix, customer_pool):
    '''内部辅助函数：重新构建索引映射、车辆时间表，并刷新所有路径费用'''
    solution.routes = [r for r in solution.routes if len(r.orders) > 0]
    solution.order2routeMap.clear()
    solution.vehiclesTimeTable.clear()
    
    for r_idx, route in enumerate(solution.routes):
        for sublist in route.orders:
            for order in sublist:
                solution.order2routeMap[order.order_id] = r_idx
        
        calc_route_total_cost(route, dist_matrix, customer_pool)
        
        v_id = route.vehicle.vehicle_id
        if v_id not in solution.vehiclesTimeTable:
            solution.vehiclesTimeTable[v_id] = []
        if len(route.times) >= 2:
            solution.vehiclesTimeTable[v_id].append((route.times[0], route.times[-1]))
    
    solution.total_cost = sum(r.cost for r in solution.routes)


def _remove_specific_orders(solution: Solution, order_ids, dist_matrix, customer_pool):
    '''内部辅助函数：执行具体的订单移除操作'''
    for oid in order_ids:
        if oid not in solution.order2routeMap: continue
        route_idx = solution.order2routeMap[oid]
        route = solution.routes[route_idx]
        found = False
        for sub_idx, sublist in enumerate(route.orders):
            for i, order in enumerate(sublist):
                if order.order_id == oid:
                    solution.unassignedOrders.append(sublist.pop(i))
                    found = True
                    if len(sublist) == 0:
                        route.orders.pop(sub_idx)
                        route.nodes.pop(sub_idx + 1)
                    break
            if found: break
        solution.order2routeMap.pop(oid)
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

# --- 破坏算子 (Removal Operators) ---

def random_order_removal(solution: Solution, n_remove: int, dist_matrix, customer_pool):
    if not solution.order2routeMap: return
    n_remove = min(n_remove, len(solution.order2routeMap))
    order_ids = random.sample(list(solution.order2routeMap.keys()), n_remove)
    _remove_specific_orders(solution, order_ids, dist_matrix, customer_pool)

def worst_order_removal(solution: Solution, n_remove: int, dist_matrix, customer_pool, n_sample=200):
    if not solution.order2routeMap: return
    all_assigned_ids = list(solution.order2routeMap.keys())
    sample_ids = random.sample(all_assigned_ids, min(n_sample, len(all_assigned_ids)))
    contributions = []
    for oid in sample_ids:
        route_idx = solution.order2routeMap[oid]
        original_route = solution.routes[route_idx]
        original_cost = original_route.cost
        temp_route = copy.copy(original_route)
        temp_route.orders = [list(sub) for sub in original_route.orders]
        temp_route.nodes = list(original_route.nodes)
        found = False
        for sub_idx, sublist in enumerate(temp_route.orders):
            for i, order in enumerate(sublist):
                if order.order_id == oid:
                    sublist.pop(i)
                    if not sublist:
                        temp_route.orders.pop(sub_idx)
                        temp_route.nodes.pop(sub_idx+1)
                    found = True; break
            if found: break
        new_cost = calc_route_total_cost(temp_route, dist_matrix, customer_pool) if temp_route.orders else 0
        contributions.append((oid, original_cost - new_cost))
    contributions.sort(key=lambda x: x[1], reverse=True)
    to_remove = [x[0] for x in contributions[:n_remove]]
    _remove_specific_orders(solution, to_remove, dist_matrix, customer_pool)

def shaw_order_removal(solution: Solution, n_remove: int, dist_matrix, customer_pool):
    if not solution.order2routeMap: return
    seed_oid = random.choice(list(solution.order2routeMap.keys()))
    seed_route = solution.routes[solution.order2routeMap[seed_oid]]
    seed_order = next(o for sub in seed_route.orders for o in sub if o.order_id == seed_oid)
    seed_cust = customer_pool[seed_order.customer_id]
    similarities = []
    for oid, r_idx in solution.order2routeMap.items():
        if oid == seed_oid: continue
        route = solution.routes[r_idx]
        order = next(o for sub in route.orders for o in sub if o.order_id == oid)
        cust = customer_pool[order.customer_id]
        dist = dist_matrix[seed_cust.id][cust.id]
        time_diff = abs((seed_cust.timewindow[0]+seed_cust.timewindow[1]) - (cust.timewindow[0]+cust.timewindow[1]))/2
        load_diff = abs(seed_order.demand_weight - order.demand_weight)
        score = 1.0 * dist + 0.5 * time_diff + 0.1 * load_diff
        similarities.append((oid, score))
    similarities.sort(key=lambda x: x[1])
    to_remove = [seed_oid] + [x[0] for x in similarities[:n_remove-1]]
    _remove_specific_orders(solution, to_remove, dist_matrix, customer_pool)

def route_removal(solution: Solution, n_remove_routes: int, dist_matrix, customer_pool):
    if not solution.routes: return
    routes_to_remove = random.sample(solution.routes, min(n_remove_routes, len(solution.routes)))
    for route in routes_to_remove:
        for sublist in route.orders:
            for order in sublist:
                solution.unassignedOrders.append(order)
        solution.routes.remove(route)
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

# --- 修复算子逻辑 (Repair Operators) ---

_new_route_cache = {}

def _is_time_table_safe(solution, old_route, new_route, is_new=False):
    v_id = new_route.vehicle.vehicle_id
    all_tasks = solution.vehiclesTimeTable.get(v_id, [])
    if is_new:
        other_tasks = all_tasks
    else:
        current_task = (old_route.times[0], old_route.times[-1])
        other_tasks = [t for t in all_tasks if t != current_task]
    new_start, new_end = new_route.times[0], new_route.times[-1]
    for (s, e) in other_tasks:
        if not (new_end <= s or new_start >= e): return False
    return True

def _try_open_new_route(solution: Solution, order: Order, vehicle_pool, dist_matrix, customer_pool):
    global _new_route_cache
    cust_id = order.customer_id
    best_v, min_delta = None, float('inf')
    unique_types = sorted(list(set(v.type_id for v in vehicle_pool)))
    dist_matrix_safe = np.nan_to_num(dist_matrix.astype(float))
    
    for t_id in unique_types:
        cache_key = (t_id, cust_id)
        if cache_key in _new_route_cache:
            res = _new_route_cache[cache_key]
        else:
            rep_v = next(v for v in vehicle_pool if v.type_id == t_id)
            if order.demand_weight > rep_v.capacity_weight or order.demand_volume > rep_v.capacity_volume:
                res = (float('inf'), 0, 0)
            else:
                temp_route = Route(rep_v); temp_route.nodes = [0, cust_id, 0]; temp_route.orders = [[order]]
                cost = calc_route_total_cost(temp_route, dist_matrix_safe, customer_pool)
                res = (cost, temp_route.times[0], temp_route.times[-1])
            _new_route_cache[cache_key] = res
        
        cost, start_t, end_t = res
        if cost < min_delta:
            for v in vehicle_pool:
                if v.type_id == t_id:
                    mock_route = Route(v); mock_route.times = [start_t, 0, end_t]
                    if _is_time_table_safe(solution, None, mock_route, is_new=True):
                        min_delta, best_v = cost, v; break
    return best_v, min_delta

def _find_all_legal_insertions(solution: Solution, order: Order, dist_matrix, customer_pool, top_k=15):
    '''
    【Top-K 极速版】只搜索距离目标客户最近的 K 条路径，大幅减少计算量。
    '''
    legal_insertions = []
    o_w, o_v = order.demand_weight, order.demand_volume
    cust_id = order.customer_id

    # 1. 按"路径起点到目标客户"的距离，筛选出最近的 top_k 条路径
    #    使用路径中第一个客户节点（nodes[1]）作为近似代表点
    def route_dist_to_cust(r_idx_route):
        _, route = r_idx_route
        if len(route.nodes) < 2:
            return float('inf')
        rep_node = route.nodes[1]  # 路径上第一个客户点
        d = dist_matrix[rep_node][cust_id] if rep_node < dist_matrix.shape[0] and cust_id < dist_matrix.shape[1] else float('inf')
        return float(d) if not np.isnan(d) else float('inf')

    routes_with_idx = list(enumerate(solution.routes))
    routes_with_idx.sort(key=route_dist_to_cust)
    candidate_routes = routes_with_idx[:top_k]

    # 2. 只在候选路径中搜索合法插入点
    for r_idx, route in candidate_routes:
        curr_w = sum(sum(o.demand_weight for o in sub) for sub in route.orders)
        curr_v = sum(sum(o.demand_volume for o in sub) for sub in route.orders)
        if curr_w + o_w > route.vehicle.capacity_weight or curr_v + o_v > route.vehicle.capacity_volume:
            continue

        # A. 合并（同客户已在路径上）
        for sub_idx, node_id in enumerate(route.nodes[1:-1]):
            if node_id == cust_id:
                temp_route = copy.copy(route)
                temp_route.orders = [list(s) for s in route.orders]
                temp_route.orders[sub_idx].append(order)
                new_cost = calc_route_total_cost(temp_route, dist_matrix, customer_pool)
                if _is_time_table_safe(solution, route, temp_route):
                    legal_insertions.append((r_idx, sub_idx, True, new_cost - route.cost))

        # B. 新增节点
        for i in range(len(route.nodes) - 1):
            temp_route = copy.copy(route)
            temp_route.nodes = route.nodes[:i+1] + [cust_id] + route.nodes[i+1:]
            temp_route.orders = route.orders[:i] + [[order]] + route.orders[i:]
            new_cost = calc_route_total_cost(temp_route, dist_matrix, customer_pool)
            if _is_time_table_safe(solution, route, temp_route):
                legal_insertions.append((r_idx, i, False, new_cost - route.cost))

    return legal_insertions


def greedy_repair(solution: Solution, dist_matrix, customer_pool, vehicle_pool=None):
    global _new_route_cache
    _new_route_cache = {}
    dist_matrix_safe = np.nan_to_num(dist_matrix.astype(float))
    while solution.unassignedOrders:
        batch = solution.unassignedOrders[:50]
        best_candidate = None; min_delta = float('inf')
        for o_idx, order in enumerate(batch):
            insertions = _find_all_legal_insertions(solution, order, dist_matrix_safe, customer_pool)
            if insertions:
                bi = min(insertions, key=lambda x: x[3])
                if bi[3] < min_delta: min_delta, best_candidate = bi[3], (o_idx, bi[0], bi[1], bi[2], False)
            if vehicle_pool:
                bv, nd = _try_open_new_route(solution, order, vehicle_pool, dist_matrix_safe, customer_pool)
                if nd < min_delta: min_delta, best_candidate = nd, (o_idx, bv, 0, False, True)
        if best_candidate:
            o_idx, target, pos, is_merge, is_new = best_candidate
            order = solution.unassignedOrders.pop(o_idx)
            if is_new:
                new_r = Route(target); new_r.nodes, new_r.orders = [0, order.customer_id, 0], [[order]]
                calc_route_total_cost(new_r, dist_matrix_safe, customer_pool)
                solution.routes.append(new_r)
                r_idx = len(solution.routes) - 1
                solution.order2routeMap[order.order_id] = r_idx
                v_id = new_r.vehicle.vehicle_id
                solution.vehiclesTimeTable.setdefault(v_id, []).append((new_r.times[0], new_r.times[-1]))
                solution.total_cost += new_r.cost
            else:
                route = solution.routes[target]
                old_cost = route.cost
                if is_merge:
                    route.orders[pos].append(order)
                else:
                    route.nodes.insert(pos + 1, order.customer_id)
                    route.orders.insert(pos, [order])
                new_cost = calc_route_total_cost(route, dist_matrix_safe, customer_pool)
                solution.order2routeMap[order.order_id] = target
                solution.total_cost = solution.total_cost - old_cost + new_cost
        else:
            # 没有找到任何插入点：对 batch 中每个订单强制开辟新路径
            # 这保证了修复完成后 unassignedOrders 一定为空
            stuck = True
            for o_idx in range(len(solution.unassignedOrders) - 1, -1, -1):
                order = solution.unassignedOrders[o_idx]
                if vehicle_pool:
                    bv, nd = _try_open_new_route(solution, order, vehicle_pool, dist_matrix_safe, customer_pool)
                    if bv:
                        solution.unassignedOrders.pop(o_idx)
                        new_r = Route(bv); new_r.nodes, new_r.orders = [0, order.customer_id, 0], [[order]]
                        calc_route_total_cost(new_r, dist_matrix_safe, customer_pool)
                        solution.routes.append(new_r)
                        r_idx = len(solution.routes) - 1
                        solution.order2routeMap[order.order_id] = r_idx
                        solution.vehiclesTimeTable.setdefault(bv.vehicle_id, []).append((new_r.times[0], new_r.times[-1]))
                        solution.total_cost += new_r.cost
                        stuck = False
            if stuck:
                break  # 车辆池真的耗尽了，才退出

def regret_repair(solution: Solution, dist_matrix, customer_pool, vehicle_pool=None, k_regret=2):
    global _new_route_cache
    _new_route_cache = {}
    dist_matrix_safe = np.nan_to_num(dist_matrix.astype(float))
    while solution.unassignedOrders:
        batch = solution.unassignedOrders[:50]
        best_order_info, max_regret = None, -1
        for o_idx, order in enumerate(batch):
            poss = []
            ins = _find_all_legal_insertions(solution, order, dist_matrix_safe, customer_pool)
            for r_idx, pos, is_merge, delta in ins: poss.append(('existing', r_idx, pos, is_merge, delta))
            if vehicle_pool:
                bv, nd = _try_open_new_route(solution, order, vehicle_pool, dist_matrix_safe, customer_pool)
                if bv: poss.append(('new', bv, 0, False, nd))
            if not poss: continue
            poss.sort(key=lambda x: x[4])
            regret = (poss[1][4] if len(poss) > 1 else 999999) - poss[0][4]
            if regret > max_regret: max_regret, best_order_info = regret, (o_idx, poss[0])
        if best_order_info:
            o_idx, info = best_order_info
            order = solution.unassignedOrders.pop(o_idx)
            itype, target, pos, is_merge, cost = info
            if itype == 'new':
                new_r = Route(target); new_r.nodes, new_r.orders = [0, order.customer_id, 0], [[order]]
                calc_route_total_cost(new_r, dist_matrix_safe, customer_pool)
                solution.routes.append(new_r)
                r_idx = len(solution.routes) - 1
                solution.order2routeMap[order.order_id] = r_idx
                v_id = new_r.vehicle.vehicle_id
                solution.vehiclesTimeTable.setdefault(v_id, []).append((new_r.times[0], new_r.times[-1]))
                solution.total_cost += new_r.cost
            else:
                route = solution.routes[target]
                old_cost = route.cost
                if is_merge:
                    route.orders[pos].append(order)
                else:
                    route.nodes.insert(pos + 1, order.customer_id)
                    route.orders.insert(pos, [order])
                new_cost = calc_route_total_cost(route, dist_matrix_safe, customer_pool)
                solution.order2routeMap[order.order_id] = target
                solution.total_cost = solution.total_cost - old_cost + new_cost
        else:
            # 没有找到任何合法插入：对每个卡住的订单强制开辟新路径
            stuck = True
            for o_idx in range(len(solution.unassignedOrders) - 1, -1, -1):
                order = solution.unassignedOrders[o_idx]
                if vehicle_pool:
                    bv, nd = _try_open_new_route(solution, order, vehicle_pool, dist_matrix_safe, customer_pool)
                    if bv:
                        solution.unassignedOrders.pop(o_idx)
                        new_r = Route(bv); new_r.nodes, new_r.orders = [0, order.customer_id, 0], [[order]]
                        calc_route_total_cost(new_r, dist_matrix_safe, customer_pool)
                        solution.routes.append(new_r)
                        r_idx = len(solution.routes) - 1
                        solution.order2routeMap[order.order_id] = r_idx
                        solution.vehiclesTimeTable.setdefault(bv.vehicle_id, []).append((new_r.times[0], new_r.times[-1]))
                        solution.total_cost += new_r.cost
                        stuck = False
            if stuck:
                break  # 车辆池真的耗尽，才退出
