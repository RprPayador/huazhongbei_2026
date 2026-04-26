"""
解导出模块：将 Solution 对象序列化为结构化 txt 文件，供绘图脚本独立读取。

格式说明：
  [META]        全局摘要信息
  [CUSTOMER]    所有客户坐标和时间窗
  [ROUTE_N]     第 N 条路径的完整信息
  [UNASSIGNED]  未分配订单列表

用法：
    from save_solution import save_solution, load_solution_txt
    save_solution(best_solution, customer_pool, path='solution_output.txt')
    data = load_solution_txt('solution_output.txt')
"""

import os


# ─────────────────────────────────────────────
#  保存
# ─────────────────────────────────────────────

def save_solution(solution, customer_pool, path='solution_output.txt'):
    """
    将 Solution 对象写入 txt 文件。

    :param solution:      Solution 对象
    :param customer_pool: dict {cid: Customer}
    :param path:          输出文件路径
    """
    lines = []

    # ── [META] ──────────────────────────────
    lines.append('[META]')
    lines.append(f'total_cost={solution.total_cost:.4f}')
    lines.append(f'num_routes={len(solution.routes)}')
    lines.append(f'num_assigned={len(solution.order2routeMap)}')
    lines.append(f'num_unassigned={len(solution.unassignedOrders)}')
    lines.append('')

    # ── [CUSTOMER] ──────────────────────────
    lines.append('[CUSTOMER]')
    lines.append('# cid,x,y,tw_start,tw_end')
    for cid, cust in sorted(customer_pool.items()):
        tw = cust.timewindow if hasattr(cust, 'timewindow') else (0, 1440)
        lines.append(f'{cid},{cust.x:.4f},{cust.y:.4f},{tw[0]:.1f},{tw[1]:.1f}')
    lines.append('')

    # ── [ROUTE_N] ───────────────────────────
    for r_idx, route in enumerate(solution.routes):
        v = route.vehicle
        lines.append(f'[ROUTE_{r_idx}]')
        lines.append(f'vehicle_id={v.vehicle_id}')
        lines.append(f'vehicle_type={v.type_id}')
        lines.append(f'capacity_weight={v.capacity_weight}')
        lines.append(f'capacity_volume={v.capacity_volume}')
        lines.append(f'start_cost={v.start_cost}')
        lines.append(f'route_cost={route.cost:.4f}')

        # nodes: 逗号分隔
        lines.append('nodes=' + ','.join(str(n) for n in route.nodes))

        # times: 逗号分隔（保留两位小数）
        times_str = ','.join(f'{t:.2f}' for t in route.times) if route.times else ''
        lines.append(f'times={times_str}')

        # orders_per_stop: 每个客户停靠点的订单列表
        # 格式：stop_0=oid1:w1:v1|oid2:w2:v2,...
        for stop_idx, sublist in enumerate(route.orders):
            order_parts = [f'{o.order_id}:{o.demand_weight:.2f}:{o.demand_volume:.4f}'
                           for o in sublist]
            lines.append(f'stop_{stop_idx}=' + '|'.join(order_parts))

        lines.append('')

    # ── [UNASSIGNED] ────────────────────────
    lines.append('[UNASSIGNED]')
    lines.append('# order_id,customer_id,weight,volume')
    for order in solution.unassignedOrders:
        lines.append(f'{order.order_id},{order.customer_id},{order.demand_weight:.2f},{order.demand_volume:.4f}')
    lines.append('')

    # 写文件
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'[保存成功] 解已写入: {os.path.abspath(path)}')
    print(f'  路径数: {len(solution.routes)}  |  总费用: {solution.total_cost:.2f}'
          f'  |  未分配: {len(solution.unassignedOrders)}')


# ─────────────────────────────────────────────
#  读取（供绘图脚本使用）
# ─────────────────────────────────────────────

def load_solution_txt(path='solution_output.txt'):
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()

    data = {'meta': {}, 'customers': {}, 'routes': [], 'unassigned': []}
    section = None
    current_route = None

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue

        if line == '[META]': section = 'meta'; continue
        if line == '[CUSTOMER]': section = 'customer'; continue
        if line == '[UNASSIGNED]': section = 'unassigned'; continue
        if line.startswith('[ROUTE_'):
            if current_route: data['routes'].append(current_route)
            current_route = {'stops': [], 'nodes': [], 'times': []}
            section = 'route'; continue

        if section == 'meta' and '=' in line:
            k, v = line.split('=', 1)
            try: data['meta'][k] = float(v) if '.' in v else int(v)
            except: data['meta'][k] = v
        elif section == 'customer':
            p = line.split(',')
            if len(p) >= 5:
                cid = int(float(p[0]))
                data['customers'][cid] = {'x': float(p[1]), 'y': float(p[2]), 'tw': (float(p[3]), float(p[4]))}
        elif section == 'route' and current_route is not None:
            if '=' in line:
                k, v = line.split('=', 1)
                if k == 'nodes': current_route['nodes'] = [int(float(n)) for n in v.split(',') if n]
                elif k == 'times': current_route['times'] = [float(t) for t in v.split(',') if t]
                elif k.startswith('stop_'):
                    orders = []
                    for part in v.split('|'):
                        if not part: continue
                        o_p = part.split(':')
                        if len(o_p) == 3:
                            orders.append({'order_id': int(float(o_p[0])), 'weight': float(o_p[1]), 'volume': float(o_p[2])})
                    current_route['stops'].append(orders)
                else:
                    try: current_route[k] = float(v) if '.' in v else int(v)
                    except: current_route[k] = v
        elif section == 'unassigned':
            p = line.split(',')
            if len(p) == 4:
                data['unassigned'].append({'order_id': int(float(p[0])), 'customer_id': int(float(p[1])), 'weight': float(p[2]), 'volume': float(p[3])})

    if current_route: data['routes'].append(current_route)
    return data


# ─────────────────────────────────────────────
#  独立测试入口
# ─────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from main import init_data
    from ALNS_tools import Solution

    BASE_DIR = r'.\A题：城市绿色物流配送调度\附件'
    customers, orders, vehicles, distances = init_data(BASE_DIR)

    sol = Solution()
    sol.initSolution(vehicles, customers, orders, distances)

    out_path = 'solution_output.txt'
    save_solution(sol, customers, path=out_path)

    # 验证读取
    d = load_solution_txt(out_path)
    print(f'\n[读取验证]')
    print(f"  META: {d['meta']}")
    print(f"  客户数: {len(d['customers'])}")
    print(f"  路径数: {len(d['routes'])}")
    print(f"  未分配: {len(d['unassigned'])}")
    if d['routes']:
        r0 = d['routes'][0]
        print(f"  第0条路径: 车辆={r0.get('vehicle_id')}, 节点={r0.get('nodes')}")
