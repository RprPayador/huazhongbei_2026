from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from operators import greedy_repair, regret_repair, _rebuild_maps_and_costs

def test_repair_operators():
    print("\n=== 开始修复算子验证 ===")
    
    # 1. 基础环境
    v = Vehicle(type_id=1, id=1, capacity_weight=200, capacity_volume=200, start_cost=400)
    customer_pool = {
        1: Customer(id=1, x=10, y=0, timeWindow=[480, 1000]),
        2: Customer(id=2, x=0, y=10, timeWindow=[480, 1000])
    }
    dist_matrix = [
        [0, 10, 10],
        [10, 0, 14],
        [10, 14, 0]
    ]
    
    # 2. 构造初始解：路径中只有客户 1
    sol = Solution()
    route = Route(v)
    route.nodes = [0, 1, 0]
    o101 = Order(id=101, customer_id=1, weight=50, volume=10)
    route.orders = [[o101]]
    sol.routes = [route]
    _rebuild_maps_and_costs(sol, dist_matrix, customer_pool)
    
    # 3. 准备未分配订单
    # 订单 102：也是客户 1 的 (期望触发合并)
    # 订单 201：客户 2 的 (期望触发新增点位)
    o102 = Order(id=102, customer_id=1, weight=50, volume=10)
    o201 = Order(id=201, customer_id=2, weight=50, volume=10)
    sol.unassignedOrders = [o102, o201]
    
    print(f"初始状态：未分配订单数={len(sol.unassignedOrders)}, 路径节点={route.nodes}")
    
    # 4. 执行贪婪修复
    print("\n[执行] 调用 greedy_repair...")
    greedy_repair(sol, dist_matrix, customer_pool)
    
    # 5. 验证结果
    print(f"修复后：未分配订单数={len(sol.unassignedOrders)}")
    print(f"修复后路径节点: {route.nodes}")
    print(f"客户 1 的订单数: {len(route.orders[0]) if len(route.orders)>0 else 0}")
    
    if len(route.nodes) == 4 and len(route.orders[0]) == 2:
        print("\n[OK] 修复算子成功执行了“合并插入”和“新增点位”。")
    else:
        print("\n[FAIL] 插入逻辑有误。")

if __name__ == "__main__":
    test_repair_operators()
