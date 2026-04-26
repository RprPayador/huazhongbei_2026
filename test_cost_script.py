import sys
import os

# 确保能导入同级目录下的类
from VRTPW_class import Vehicle, Customer, Order, Route, calc_route_total_cost

def run_test():
    # 1. 构造车辆 (0型燃油车, ID 1, 载重100, 容积100, 启动费400)
    v = Vehicle(type_id=0, id=1, capacity_weight=100, capacity_volume=100, start_cost=400)
    
    # 2. 构造客户池 (ID 1, 2 是客户)
    # 客户1: 坐标(10,10), 时间窗 [500, 600] (即 8:20 - 10:00)
    # 客户2: 坐标(20,20), 时间窗 [700, 800] (故意设晚一点测试等待)
    customer_pool = {
        1: Customer(id=1, x=10, y=10, timeWindow=[500, 600]),
        2: Customer(id=2, x=20, y=20, timeWindow=[700, 800])
    }
    
    # 3. 构造订单
    order1 = Order(id=101, customer_id=1, weight=20, volume=10)
    order2 = Order(id=102, customer_id=2, weight=30, volume=15)
    
    # 4. 构造路径
    route = Route(v)
    route.nodes = [0, 1, 2, 0]
    route.orders = [order1, order2]
    
    # 5. 构造距离矩阵 (简易对称矩阵)
    # 索引 0:中心, 1:客户1, 2:客户2
    dist_matrix = [
        [0.0, 10.0, 20.0], 
        [10.0, 0.0, 5.0],  
        [20.0, 5.0, 0.0]   
    ]
    
    # 6. 调用计算函数
    print("--- 开始测试费用计算 ---")
    try:
        cost = calc_route_total_cost(route, dist_matrix, customer_pool)
        
        # 7. 输出结果检查
        print(f"车辆类型: {'燃油车' if v.type_id==0 else '新能源'}")
        print(f"路径序列: {route.nodes}")
        print(f"到达各节点时刻: {[round(t, 2) for t in route.times]}")
        print(f"最终计算总花费: {cost:.2f} 元")
        
        if cost > 400:
            print("\n[OK] 测试成功：代码可运行且计算结果合理。")
        else:
            print("\n[ERR] 测试异常：结果不应低于启动费。")
            
    except Exception as e:
        print(f"\n[FATAL] 运行报错: {e}")

if __name__ == "__main__":
    run_test()
