import random
import copy
import numpy as np
from ALNS_tools import Solution
from VRTPW_class import *

def _rebuild_maps_and_costs(solution: Solution, dist_matrix, customer_pool):
    solution.routes = [r for r in solution.routes if len(r.orders) > 0]
    solution.order2routeMap.clear()
    solution.vehiclesTimeTable.clear()
    total_cost_val = 0
    for r_idx, route in enumerate(solution.routes):
        for sublist in route.orders:
            for order in sublist: solution.order2routeMap[order.order_id] = r_idx
        calc_route_total_cost(route, dist_matrix, customer_pool)
        total_cost_val += route.cost
        v_id = route.vehicle.vehicle_id
        if v_id not in solution.vehiclesTimeTable: solution.vehiclesTimeTable[v_id] = []
        if len(route.times) >= 2: solution.vehiclesTimeTable[v_id].append((route.times[0], route.times[-1]))
    solution.total_cost = total_cost_val

def _remove_specific_orders(solution: Solution, order_ids, dist_matrix, customer_pool):
    for oid in order_ids:
        if oid not in solution.order2routeMap: continue
        r_idx = solution.order2routeMap[oid]; route = solution.routes[r_idx]
        found = False
        for s_idx, sub in enumerate(route.orders):
            for i, o in enumerate(sub):
                if o.order_id == oid:
                    solution.unassignedOrders.append(sub.pop(i))
                    if not sub: route.orders.pop(s_idx); route.nodes.pop(s_idx + 1)
                    found = True; break
            if found: break
        solution.order2routeMap.pop(oid)
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

# --- 破坏算子 ---
def random_order_removal(solution, n_remove, dist_matrix, customer_pool):
    ids = list(solution.order2routeMap.keys())
    if not ids: return
    _remove_specific_orders(solution, random.sample(ids, min(n_remove, len(ids))), dist_matrix, customer_pool)

def worst_order_removal(solution, n_remove, dist_matrix, customer_pool):
    ids = list(solution.order2routeMap.keys())
    if not ids: return
    sample = random.sample(ids, min(200, len(ids)))
    costs = []
    for oid in sample:
        r = solution.routes[solution.order2routeMap[oid]]
        old_c = r.cost
        # 简单估算：移除该订单后的距离变化
        costs.append((oid, old_c)) # 简化版 Worst
    costs.sort(key=lambda x: x[1], reverse=True)
    _remove_specific_orders(solution, [x[0] for x in costs[:n_remove]], dist_matrix, customer_pool)

def shaw_order_removal(solution, n_remove, dist_matrix, customer_pool):
    ids = list(solution.order2routeMap.keys())
    if not ids: return
    seed = random.choice(ids)
    _remove_specific_orders(solution, [seed] + ids[:n_remove-1], dist_matrix, customer_pool)

def route_removal(solution, n_routes, dist_matrix, customer_pool):
    if not solution.routes: return
    for r in random.sample(solution.routes, min(n_routes, len(solution.routes))):
        for sub in r.orders:
            for o in sub: solution.unassignedOrders.append(o)
        solution.routes.remove(r)
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

# --- 修复核心 ---

def _is_time_table_safe(solution, old_route, new_route, is_new=False):
    v_id = new_route.vehicle.vehicle_id
    all_t = solution.vehiclesTimeTable.get(v_id, [])
    if is_new or not old_route or len(old_route.times) < 2: other = all_t
    else:
        curr = (old_route.times[0], old_route.times[-1])
        other = [t for t in all_t if t != curr]
    if len(new_route.times) < 2: return True
    ns, ne = new_route.times[0], new_route.times[-1]
    for (s, e) in other:
        if not (ne <= s or ns >= e): return False
    return True

def _get_best_ins(solution, order, dist_matrix, customer_pool, vehicle_pool):
    o_w, o_v, cid = order.demand_weight, order.demand_volume, order.customer_id
    cands = []
    # 限制搜索范围提升性能
    for r_idx, route in enumerate(solution.routes):
        # 载重检查
        if sum(sum(o.demand_weight for o in s) for s in route.orders) + o_w > route.vehicle.capacity_weight: continue
        # 仅尝试插入现有节点后或作为新节点
        for i in range(len(route.nodes)-1):
            nr = copy.copy(route); nr.nodes = route.nodes[:i+1] + [cid] + route.nodes[i+1:]; nr.orders = route.orders[:i] + [[order]] + route.orders[i:]
            calc_route_total_cost(nr, dist_matrix, customer_pool)
            if _is_time_table_safe(solution, route, nr): cands.append((nr.cost - route.cost, r_idx, i))
    
    if vehicle_pool:
        # 只尝试尚未被使用的车辆
        used_vids = {r.vehicle.vehicle_id for r in solution.routes}
        free_vehicles = [v for v in vehicle_pool if v.vehicle_id not in used_vids]
        if free_vehicles:
            types = {v.type_id: v for v in free_vehicles}.values()
            for v in types:
                if o_w <= v.capacity_weight:
                    nr = Route(v); nr.nodes, nr.orders = [0, cid, 0], [[order]]
                    cost = calc_route_total_cost(nr, dist_matrix, customer_pool)
                    cands.append((cost, -1, v))
    cands.sort(key=lambda x: x[0])
    return cands[:2]

def greedy_repair(solution, dist_matrix, customer_pool, vehicle_pool=None, temp=0):
    dm = np.nan_to_num(dist_matrix.astype(float))
    while solution.unassignedOrders:
        order = solution.unassignedOrders.pop(0)
        opts = _get_best_ins(solution, order, dm, customer_pool, vehicle_pool)
        if not opts:
            # 最终兜底：强行找个空车
            used = {r.vehicle.vehicle_id for r in solution.routes}
            v = next((v for v in vehicle_pool if v.vehicle_id not in used and order.demand_weight <= v.capacity_weight), None)
            if v:
                nr = Route(v); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]
                solution.routes.append(nr)
            continue
        best = opts[0]
        if r_idx := best[1] == -1:
            nr = Route(best[2]); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]; solution.routes.append(nr)
        else:
            r = solution.routes[best[1]]; r.nodes.insert(best[2]+1, order.customer_id); r.orders.insert(best[2], [order])
    _rebuild_maps_and_costs(solution, dm, customer_pool)

def regret_repair(solution, dist_matrix, customer_pool, vehicle_pool=None, temp=0):
    dm = np.nan_to_num(dist_matrix.astype(float))
    while solution.unassignedOrders:
        # 限制后悔值计算的样本数以提升速度
        sample_size = min(30, len(solution.unassignedOrders))
        indices = random.sample(range(len(solution.unassignedOrders)), sample_size)
        best_regret, best_order_idx, best_opt = -1, -1, None
        for idx in indices:
            opts = _get_best_ins(solution, solution.unassignedOrders[idx], dm, customer_pool, vehicle_pool)
            regret = (opts[1][0] - opts[0][0]) if len(opts)>1 else (1000 if opts else -1)
            if regret > best_regret: best_regret, best_order_idx, best_opt = regret, idx, (opts[0] if opts else None)
        
        if best_order_idx == -1: break
        order = solution.unassignedOrders.pop(best_order_idx)
        if not best_opt: continue
        if best_opt[1] == -1:
            nr = Route(best_opt[2]); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]; solution.routes.append(nr)
        else:
            r = solution.routes[best_opt[1]]; r.nodes.insert(best_opt[2]+1, order.customer_id); r.orders.insert(best_opt[2], [order])
    _rebuild_maps_and_costs(solution, dm, customer_pool)

def greedy_repair_p2(solution, dist_matrix, customer_pool, vehicle_pool):
    greedy_repair(solution, dist_matrix, customer_pool, vehicle_pool, 0)
