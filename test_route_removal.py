from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from operators import route_removal

def test_route_removal():
    print("\n=== 开始 Route Removal (路径移除) 验证 ===")
    
    # 1. 准备数据
    v1 = Vehicle(type_id=1, id=1, capacity_weight=100, capacity_volume=100, start_cost=400)
    v2 = Vehicle(type_id=1, id=2, capacity_weight=100, capacity_volume=100, start_cost=400)
    customer_pool = {1: Customer(id=1, x=10, y=10, timeWindow=[480, 600])}
    dist_matrix = [[0, 10], [10, 0]]
    
    # 2. 构造包含 2 条路径的 Solution
    sol = Solution()
    
    r1 = Route(v1)
    r1.nodes = [0, 1, 0]
    o101 = Order(id=101, customer_id=1, weight=10, volume=5)
    r1.orders = [[o101]]
    
    r2 = Route(v2)
    r2.nodes = [0, 1, 0]
    o201 = Order(id=201, customer_id=1, weight=10, volume=5)
    r2.orders = [[o201]]
    
    sol.routes = [r1, r2]
    sol.order2routeMap = {101: 0, 201: 1} # 初始映射
    
    print(f"初始状态：路径数={len(sol.routes)}, 订单201所在的路径索引={sol.order2routeMap[201]}")
    
    # 3. 执行路径移除 (移除 1 条)
    # 我们希望模拟移除第一条(r1)，这样 r2 的索引会从 1 变成 0
    import random
    random.seed(1) # 选一个种子确保移除逻辑
    
    print("[执行] 调用 route_removal 移除 1 条路径...")
    route_removal(sol, 1, dist_matrix, customer_pool)
    
    # 4. 验证
    print(f"执行后：路径数={len(sol.routes)}")
    print(f"未分配池订单数: {len(sol.unassignedOrders)}")
    
    # 检查剩下的订单索引是否正确更新了
    if 201 in sol.order2routeMap:
        new_idx = sol.order2routeMap[201]
        print(f"订单 201 现在所在的路径索引: {new_idx}")
        if new_idx == 0:
            print("\n[OK] 索引重刷成功，剩余路径已前移。")
        else:
            print("\n[FAIL] 索引未正确同步。")
    elif 101 in sol.order2routeMap:
        print("\n[OK] 移除了路径2，路径1保留。")

if __name__ == "__main__":
    test_route_removal()
