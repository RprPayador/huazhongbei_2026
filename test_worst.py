from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from operators import random_order_removal, worst_order_removal

def test_worst_removal():
    print("\n=== 开始最差移除算子验证 ===")
    
    # 1. 初始化基础数据
    v = Vehicle(type_id=1, id=1, capacity_weight=100, capacity_volume=100, start_cost=400)
    # 客户1：很近很顺路
    # 客户2：非常远，贡献巨大成本
    customer_pool = {
        1: Customer(id=1, x=10, y=10, timeWindow=[480, 1000]),
        2: Customer(id=2, x=500, y=500, timeWindow=[480, 500]) # 很远且时间紧
    }
    # 距离矩阵：0-1=10km, 1-2=500km, 2-0=500km
    dist_matrix = [
        [0, 10, 500],
        [10, 0, 500],
        [500, 500, 0]
    ]
    
    # 2. 构造 Solution
    sol = Solution()
    route = Route(v)
    route.nodes = [0, 1, 2, 0]
    
    o101 = Order(id=101, customer_id=1, weight=10, volume=5)
    o102 = Order(id=102, customer_id=2, weight=10, volume=5)
    
    route.orders = [[o101], [o102]]
    sol.routes = [route]
    sol.order2routeMap = {101: 0, 102: 0}
    
    # 先算一下初始费用
    from VRTPW_class import calc_route_total_cost
    calc_route_total_cost(route, dist_matrix, customer_pool)
    print(f"初始总费用: {route.cost:.2f}")

    # 3. 执行最差移除 (移除 1 个)
    print("\n[执行] 调用 worst_order_removal 移除 1 个订单...")
    worst_order_removal(sol, 1, dist_matrix, customer_pool)
    
    # 4. 验证结果
    removed_id = sol.unassignedOrders[0].order_id
    print(f"被移除的订单 ID: {removed_id}")
    print(f"剩余节点: {sol.routes[0].nodes if sol.routes else '路径已空'}")
    
    if removed_id == 102:
        print("\n[OK] 成功识别并移除了贡献成本最大的订单 (102)。")
    else:
        print("\n[FAIL] 算子选错了目标。")

if __name__ == "__main__":
    test_worst_removal()
