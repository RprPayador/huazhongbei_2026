import random
import copy
import numpy as np
from ALNS_tools import Solution
from VRTPW_class import *

# --- 全局矩阵缓存 ---
_DM_SAFE = None

def _init_dm_if_needed(dm):
    global _DM_SAFE
    if _DM_SAFE is None and dm is not None:
        _DM_SAFE = np.nan_to_num(dm.astype(float))
    return _DM_SAFE

def _get_nearest_routes(order, solution, k=30):
    if not solution.routes: return []
    cid = order.customer_id
    dists = []
    for i, r in enumerate(solution.routes):
        if not r.nodes or len(r.nodes) < 2: continue
        rep_node = r.nodes[1]
        dists.append((i, _DM_SAFE[cid, rep_node], r.vehicle.type_id))
    dists.sort(key=lambda x: x[1])
    
    # 选出距离最近的 K 条
    targets = [solution.routes[x[0]] for x in dists[:k]]
    target_set = set(targets)
    
    # 关键修复：无条件把所有“新能源车”加入候选！
    # 防止绿区订单被周围的燃油车包围而找不到合法的车，导致疯狂开新车
    for x in dists:
        if x[2] in [4, 5]:
            r = solution.routes[x[0]]
            if r not in target_set:
                targets.append(r)
                target_set.add(r)
    return targets

def _rebuild_maps_and_costs(solution: Solution, dist_matrix, customer_pool):
    dm = _init_dm_if_needed(dist_matrix)
    # 彻底清理空路径
    solution.routes = [r for r in solution.routes if len(r.orders) > 0 and len(r.nodes) >= 2]
    solution.order2routeMap.clear()
    solution.vehiclesTimeTable.clear()
    for r_idx, route in enumerate(solution.routes):
        for sublist in route.orders:
            for order in sublist: solution.order2routeMap[order.order_id] = r_idx
        calc_route_total_cost(route, dm, customer_pool)
        v_id = route.vehicle.vehicle_id
        solution.vehiclesTimeTable.setdefault(v_id, [])
        if len(route.times) >= 2: solution.vehiclesTimeTable[v_id].append((route.times[0], route.times[-1]))
    solution.total_cost = sum(r.cost for r in solution.routes)

def _remove_specific_orders(solution: Solution, order_ids, dist_matrix, customer_pool):
    for oid in order_ids:
        if oid not in solution.order2routeMap: continue
        r_idx = solution.order2routeMap[oid]; route = solution.routes[r_idx]
        found = False
        for s_idx, sub in enumerate(route.orders):
            for i, o in enumerate(sub):
                if o.order_id == oid:
                    solution.unassignedOrders.append(sub.pop(i))
                    if not sub: 
                        route.orders.pop(s_idx)
                        route.nodes.pop(s_idx + 1)
                    found = True; break
            if found: break
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

# --- 破坏算子 ---
def random_order_removal(solution, n_remove, dist_matrix, customer_pool):
    _init_dm_if_needed(dist_matrix)
    if not solution.order2routeMap: return
    ids = random.sample(list(solution.order2routeMap.keys()), min(n_remove, len(solution.order2routeMap)))
    _remove_specific_orders(solution, ids, dist_matrix, customer_pool)

def worst_order_removal(solution, n_remove, dist_matrix, customer_pool):
    _init_dm_if_needed(dist_matrix)
    if not solution.order2routeMap: return
    ids = list(solution.order2routeMap.keys())
    sample = random.sample(ids, min(100, len(ids)))
    contributions = []
    for oid in sample: contributions.append((oid, solution.routes[solution.order2routeMap[oid]].cost))
    contributions.sort(key=lambda x: x[1], reverse=True)
    _remove_specific_orders(solution, [x[0] for x in contributions[:n_remove]], dist_matrix, customer_pool)

def shaw_order_removal(solution, n_remove, dist_matrix, customer_pool):
    _init_dm_if_needed(dist_matrix)
    if not solution.order2routeMap: return
    ids = list(solution.order2routeMap.keys())
    _remove_specific_orders(solution, ids[:n_remove], dist_matrix, customer_pool)

def route_removal(solution, n_remove_routes, dist_matrix, customer_pool):
    _init_dm_if_needed(dist_matrix)
    if not solution.routes: return
    targets = random.sample(solution.routes, min(n_remove_routes, len(solution.routes)))
    for r in targets:
        for sub in r.orders:
            for o in sub: solution.unassignedOrders.append(o)
        solution.routes.remove(r)
    _rebuild_maps_and_costs(solution, dist_matrix, customer_pool)

def policy_violation_removal(solution, customer_pool, dist_matrix=None):
    dm = _init_dm_if_needed(dist_matrix)
    to_remove = []
    for r in solution.routes:
        if r.vehicle.type_id in [1, 2, 3]: 
            for i, node_id in enumerate(r.nodes[1:-1]):
                cust = customer_pool[node_id]
                # 安全检查 times 长度
                if i+1 >= len(r.times): continue
                arrival = r.times[i+1]
                if 480 <= arrival <= 960 and (cust.x**2 + cust.y**2)**0.5 <= 10:
                    for o in r.orders[i]: to_remove.append(o.order_id)
    if to_remove:
        print(f" [P2] 发现 {len(to_remove)} 个违规订单，强制剔除...")
        _remove_specific_orders(solution, to_remove, dm, customer_pool)
    else: print(" [P2] 初始解已满足限行政策。")

# --- 极速判定与增量计算 ---
def _is_time_table_safe(solution, vehicle_id, start_t, end_t, old_task=None):
    tasks = solution.vehiclesTimeTable.get(vehicle_id, [])
    for (s, e) in tasks:
        if old_task and s == old_task[0]: continue
        if not (end_t <= s or start_t >= e): return False
    return True

def _get_ins_options(solution, order, cp, vp, is_p2=False):
    o_w, cid = order.demand_weight, order.customer_id
    options = []
    target_routes = _get_nearest_routes(order, solution, k=30)
    for route in target_routes:
        if sum(sum(o.demand_weight for o in s) for s in route.orders) + o_w > route.vehicle.capacity_weight: continue
        r_idx = solution.routes.index(route); v_type = route.vehicle.type_id; is_gas = v_type in [1, 2, 3]
        for i in range(len(route.nodes) - 1):
            # 使用轻量级模拟对象，精确捕获所有时间窗惩罚
            mock_route = Route(route.vehicle)
            mock_route.nodes = route.nodes[:i+1] + [cid] + route.nodes[i+1:]
            mock_route.orders = route.orders[:i] + [[order]] + route.orders[i:]
            calc_route_total_cost(mock_route, _DM_SAFE, cp)
            
            p2_fail = False
            if is_p2 and is_gas:
                for k, node_id in enumerate(mock_route.nodes[1:-1]):
                    if 480 <= mock_route.times[k+1] <= 960 and (cp[node_id].x**2 + cp[node_id].y**2)**0.5 <= 10:
                        p2_fail = True; break
            if p2_fail: continue
            
            if _is_time_table_safe(solution, route.vehicle.vehicle_id, mock_route.times[0], mock_route.times[-1], (route.times[0], route.times[-1])):
                options.append(('existing', r_idx, i, mock_route.cost - route.cost))
    
    if vp:
        used = {r.vehicle.vehicle_id for r in solution.routes}
        tried_types = set()
        for v in vp:
            if v.type_id in tried_types or v.vehicle_id in used: continue
            if o_w <= v.capacity_weight:
                tried_types.add(v.type_id)
                mock_route = Route(v)
                mock_route.nodes = [0, cid, 0]
                mock_route.orders = [[order]]
                calc_route_total_cost(mock_route, _DM_SAFE, cp)
                
                p2_fail = False
                if is_p2 and v.type_id in [1,2,3]:
                    if 480 <= mock_route.times[1] <= 960 and (cp[cid].x**2 + cp[cid].y**2)**0.5 <= 10:
                        p2_fail = True
                if not p2_fail:
                    # 对于新车，直接使用它产生的总费用（包含启动费）
                    options.append(('new', v, 0, mock_route.cost))
    options.sort(key=lambda x: x[3]); return options

def greedy_repair(solution, dm, cp, vp=None, is_p2=False, temp=None):
    _init_dm_if_needed(dm)
    while solution.unassignedOrders:
        order = solution.unassignedOrders.pop(0)
        opts = _get_ins_options(solution, order, cp, vp, is_p2)
        if opts:
            best = opts[0]
            if best[0] == 'new':
                v = best[1]; nr = Route(v); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]
                calc_route_total_cost(nr, _DM_SAFE, cp); solution.routes.append(nr)
            else:
                r = solution.routes[best[1]]; r.nodes.insert(best[2] + 1, order.customer_id); r.orders.insert(best[2], [order])
                # 关键：由于进行了插入，需要立即更新 times 以防后续订单插入时越界
                calc_route_total_cost(r, _DM_SAFE, cp)
        else:
            v = next((v for v in vp if order.demand_weight <= v.capacity_weight and (not is_p2 or v.type_id in [4,5])), vp[0])
            nr = Route(v); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]
            calc_route_total_cost(nr, _DM_SAFE, cp); solution.routes.append(nr)
    _rebuild_maps_and_costs(solution, _DM_SAFE, cp)

def regret_repair(solution, dm, cp, vp=None, is_p2=False, temp=None):
    _init_dm_if_needed(dm)
    while solution.unassignedOrders:
        sample = random.sample(range(len(solution.unassignedOrders)), min(15, len(solution.unassignedOrders)))
        best_regret, best_idx, best_opt = -1, -1, None
        for idx in sample:
            opts = _get_ins_options(solution, solution.unassignedOrders[idx], cp, vp, is_p2)
            if not opts: continue
            regret = (opts[1][3] - opts[0][3]) if len(opts) > 1 else 3000
            if regret > best_regret: best_regret, best_idx, best_opt = regret, idx, opts[0]
        if best_idx != -1:
            order = solution.unassignedOrders.pop(best_idx); opt = best_opt
            if opt[0] == 'new':
                v = opt[1]; nr = Route(v); nr.nodes, nr.orders = [0, order.customer_id, 0], [[order]]
                calc_route_total_cost(nr, _DM_SAFE, cp); solution.routes.append(nr)
            else:
                r = solution.routes[opt[1]]; r.nodes.insert(opt[2] + 1, order.customer_id); r.orders.insert(opt[2], [order])
                calc_route_total_cost(r, _DM_SAFE, cp)
        else: greedy_repair(solution, _DM_SAFE, cp, vp, is_p2); break
    _rebuild_maps_and_costs(solution, _DM_SAFE, cp)

def greedy_repair_p2(solution, dm, cp, vp): greedy_repair(solution, dm, cp, vp, is_p2=True)
def regret_repair_p2(solution, dm, cp, vp): regret_repair(solution, dm, cp, vp, is_p2=True)
