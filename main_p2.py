import pandas as pd
import numpy as np
import os
import copy
from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from RVPTW_ALNS import ALNS_Solver_P2
from save_solution import save_solution

def time_to_minutes(time_str):
    """将时间字符串 (如 '8:30') 转换为分钟数"""
    if pd.isna(time_str): return 0
    if isinstance(time_str, str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    return 0

def init_vehicles():
    """初始化 185 辆车"""
    vehicle_pool = []
    configs = [
        (3000, 13.5, 60), # type_id 1
        (1500, 10.8, 50), # type_id 2
        (1250, 6.5, 50),  # type_id 3
        (3000, 15, 10),   # type_id 4
        (1250, 8.5, 15)   # type_id 5
    ]
    vid = 0
    for type_idx, (weight, volume, count) in enumerate(configs, 1):
        for i in range(count):
            v = Vehicle(
                type_id=type_idx,
                id=vid,
                capacity_weight=weight,
                capacity_volume=volume,
                start_cost=400
            )
            vehicle_pool.append(v)
            vid += 1
    return vehicle_pool

def init_data(base_dir):
    print("正在初始化数据...")
    df_coords = pd.read_excel(os.path.join(base_dir, '客户坐标信息.xlsx'))
    df_tw = pd.read_excel(os.path.join(base_dir, '时间窗.xlsx'))
    df_customer_info = pd.merge(df_coords, df_tw, left_on='ID', right_on='客户编号', how='left')
    
    customer_pool = {}
    for _, row in df_customer_info.iterrows():
        cid = int(row['ID'])
        tw = (time_to_minutes(row['开始时间']), time_to_minutes(row['结束时间']))
        if cid == 0: tw = (0, 1440)
        customer_pool[cid] = Customer(cid, row['X (km)'], row['Y (km)'], tw)

    df_orders = pd.read_excel(os.path.join(base_dir, '订单信息.xlsx'))
    order_pool = []
    for _, row in df_orders.iterrows():
        weight, volume = row['重量'], row['体积']
        if pd.isna(weight) or pd.isna(volume):
            print(f"警告: 订单 {row['订单编号']} 含有NaN值，跳过")
            continue
        order_pool.append(Order(id=int(row['订单编号']), customer_id=int(row['目标客户编号']), weight=float(weight), volume=float(volume)))

    df_dist = pd.read_excel(os.path.join(base_dir, '距离矩阵.xlsx'))
    dist_matrix = df_dist.drop(columns=['客户']).values
    vehicle_pool = init_vehicles()
    
    print(f"初始化完成：\n- 客户数: {len(customer_pool)}\n- 订单数: {len(order_pool)}\n- 车辆总数: {len(vehicle_pool)}\n")
    return customer_pool, order_pool, vehicle_pool, dist_matrix

def solve_problem_2():
    print("\n" + "="*20 + " 问题 2：环保政策限行调度优化 " + "="*20)
    
    BASE_DIR = r'.\A题：城市绿色物流配送调度\附件'
    if not os.path.exists(BASE_DIR): BASE_DIR = '附件'

    # 1. 数据加载
    customers, orders, vehicles, distances = init_data(BASE_DIR)

    # 2. 构建初始解 (使用 Solution 类自带的初始化方法)
    print("正在构建初始解 (忽略限行策略)...")
    sol_p1 = Solution()
    sol_p1.initSolution(vehicles, customers, orders, distances)
    print(f"初始解构建完成：\n  总路径数:     {len(sol_p1.routes)}\n  初始总费用:   {sol_p1.total_cost:.2f}\n")

    # 3. 使用 P2 专用求解器进行优化
    print("开始 P2 ALNS 优化迭代 (强制限行约束)...")
    solver_p2 = ALNS_Solver_P2(sol_p1, distances, customers, vehicles)
    best_sol_p2 = solver_p2.solve(max_iter=150)

    # 4. 结果保存与分析
    print("\n" + "="*20 + " 优化结果分析 " + "="*20)
    print(f"P2 最优费用: {best_sol_p2.total_cost:.2f}")
    print(f"P2 未分配订单: {len(best_sol_p2.unassignedOrders)}")
    
    carbon_total = 0
    v_structure = {1:0, 2:0, 3:0, 4:0, 5:0}
    for r in best_sol_p2.routes:
        tid = r.vehicle.type_id
        v_structure[tid] += 1
        dist = sum(distances[r.nodes[i]][r.nodes[i+1]] for i in range(len(r.nodes)-1))
        if tid == 1: carbon_total += dist * 0.5
        elif tid == 2: carbon_total += dist * 0.6
        elif tid == 3: carbon_total += dist * 0.8

    print(f"车辆使用结构: {v_structure}")
    print(f"估算总碳排放: {carbon_total:.2f}")

    # 保存解
    save_solution(best_sol_p2, customers, "solution_output_p2.txt")
    print("\n结果已保存至 solution_output_p2.txt")

if __name__ == "__main__":
    solve_problem_2()
