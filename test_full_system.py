import sys
import os
import numpy as np

# 导入你的业务逻辑
from main import init_data
from ALNS_tools import Solution
from operators import (
    random_order_removal, worst_order_removal, shaw_order_removal, 
    route_removal, greedy_repair, regret_repair, _rebuild_maps_and_costs
)

def run_real_data_test():
    print("=== 开始【真实数据】全系统算子压力测试 ===")
    
    # 1. 加载真实数据 (根据 main.py 中的路径)
    BASE_DIR = r'.\A题：城市绿色物流配送调度\附件'
    try:
        customers, orders, vehicles, distances = init_data(BASE_DIR)
    except Exception as e:
        print(f"数据加载失败，请检查路径是否正确: {e}")
        return
    
    # 2. 生成初始解
    print("\n[第一步] 正在生成初始解...")
    sol = Solution()
    sol.initSolution(vehicles, customers, orders, distances)
    
    # 3. 同步状态 (计费与时间表重构)
    _rebuild_maps_and_costs(sol, distances, customers)
    
    initial_cost = sol.total_cost
    print(f"初始解状态：路径数={len(sol.routes)}, 总费用={initial_cost:.2f}, 未分配订单={len(sol.unassignedOrders)}")

    if not sol.routes:
        print("警告：初始解未生成任何路径，测试终止。")
        return

    # --- 迭代测试过程 ---
    
    # --- 算子轮询测试 ---
    operators_to_test = [
        ("随机移除", random_order_removal),
        ("最差移除", worst_order_removal),
        ("Shaw移除", shaw_order_removal),
        ("路径移除", route_removal)
    ]

    for op_name, op_func in operators_to_test:
        print(f"\n>>> 正在测试算子组合: [{op_name}] + [Greedy Repair]")
        
        # 记录本次测试前的状态
        pre_cost = sol.total_cost
        pre_unassigned = len(sol.unassignedOrders)

        # 1. 执行破坏
        if op_name == "路径移除":
            op_func(sol, 2, distances, customers)
        else:
            op_func(sol, 15, distances, customers)
        
        print(f"   破坏后: 未分配订单={len(sol.unassignedOrders)}")

        # 2. 执行修复 (贪婪修复)
        greedy_repair(sol, distances, customers, vehicle_pool=vehicles)
        
        # 3. 输出结果
        post_cost = sol.total_cost
        post_unassigned = len(sol.unassignedOrders)
        print(f"   修复后: 未分配订单={post_unassigned}, 总费用={post_cost:.2f}")
        print(f"   效果: 费用变动 {post_cost - pre_cost:.2f}, 订单缺口变动 {post_unassigned - pre_unassigned}")

    print("\n=== 所有算子组合冒烟测试完成 ===")

if __name__ == "__main__":
    run_real_data_test()
