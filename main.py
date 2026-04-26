import pandas as pd
import numpy as np
import os
from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from RVPTW_ALNS import ALNS_Solver

def time_to_minutes(time_str):
    """将时间字符串 (如 '8:30') 转换为分钟数"""
    if pd.isna(time_str): return 0
    if isinstance(time_str, str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    return 0

def init_data(base_dir):
    print("正在初始化数据...")
    
    # 1. 读取客户和时间窗信息并合并
    df_coords = pd.read_excel(os.path.join(base_dir, '客户坐标信息.xlsx'))
    df_tw = pd.read_excel(os.path.join(base_dir, '时间窗.xlsx'))
    
    # 合并坐标和时间窗 (Left join，因为中心点 ID 0 可能没在时间窗表里)
    df_customer_info = pd.merge(df_coords, df_tw, left_on='ID', right_on='客户编号', how='left')
    
    customer_pool = {}
    for _, row in df_customer_info.iterrows():
        cid = int(row['ID'])
        # 转换为分钟元组 (开始, 结束)
        tw = (time_to_minutes(row['开始时间']), time_to_minutes(row['结束时间']))
        # 配送中心默认全天可用
        if cid == 0: tw = (0, 1440)
        
        customer_pool[cid] = Customer(cid, row['X (km)'], row['Y (km)'], tw)

    # 2. 读取订单信息
    df_orders = pd.read_excel(os.path.join(base_dir, '订单信息.xlsx'))
    order_pool = []
    for _, row in df_orders.iterrows():
        weight = row['重量']
        volume = row['体积']
        if pd.isna(weight) or pd.isna(volume):
            print(f"警告: 订单 {row['订单编号']} 含有NaN值，跳过")
            continue
        order = Order(
            id=int(row['订单编号']),
            customer_id=int(row['目标客户编号']),
            weight=float(weight),
            volume=float(volume)
        )
        order_pool.append(order)

    # 3. 读取距离矩阵
    df_dist = pd.read_excel(os.path.join(base_dir, '距离矩阵.xlsx'))
    # 转换为 Numpy 矩阵，方便后续计算
    dist_matrix = df_dist.drop(columns=['客户']).values

    # 4. 初始化车辆池 (独立函数调用)
    vehicle_pool = init_vehicles()

    print(f"初始化完成：")
    print(f"- 客户数: {len(customer_pool)}")
    print(f"- 订单数: {len(order_pool)}")
    print(f"- 车辆总数: {len(vehicle_pool)}")
    print(f"- 距离矩阵维度: {dist_matrix.shape}")
    
    return customer_pool, order_pool, vehicle_pool, dist_matrix

def init_vehicles():
    """根据题目要求初始化 185 辆车，每一辆车都是一个独立的实例"""
    vehicle_pool = []
    
    # 车型配置: (载重kg, 容积m3, 数量)
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
            # 实例化每一辆车，只传入类定义的参数
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

if __name__ == "__main__":
    BASE_DIR = r'.\A题：城市绿色物流配送调度\附件'
    customers, orders, vehicles, distances = init_data(BASE_DIR)

    # --- 构建初始解 ---
    print("\n正在构建初始解...")
    solution = Solution()
    solution.initSolution(vehicles, customers, orders, distances)
    print(f"初始解构建完成：")
    print(f"  总路径数:    {len(solution.routes)}")
    print(f"  已分配订单: {len(solution.order2routeMap)}")
    print(f"  未分配订单: {len(solution.unassignedOrders)}")
    print(f"  初始总费用: {solution.total_cost:.2f}")

    # --- 启动 ALNS 优化 ---
    print("\n开始 ALNS 优化迭代...")
    solver = ALNS_Solver(solution, distances, customers, vehicles)
    best_solution = solver.solve(max_iter=1000, update_period=50)

    # --- 输出最终结果 ---
    print("\n========== 最终优化结果 ==========")
    print(f"  最优总费用:   {best_solution.total_cost:.2f}")
    print(f"  总路径数:     {len(best_solution.routes)}")
    print(f"  已分配订单:  {len(best_solution.order2routeMap)}")
    print(f"  未分配订单:  {len(best_solution.unassignedOrders)}")

    ev_count = sum(1 for r in best_solution.routes if r.vehicle.type_id in [4, 5])
    fv_count = len(best_solution.routes) - ev_count
    print(f"  新能源车使用: {ev_count} 趟")
    print(f"  燃油车使用:   {fv_count} 趟")
    print("==================================")
