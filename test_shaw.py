from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from operators import shaw_order_removal

def test_shaw():
    print("\n=== 开始 Shaw Removal (相似度移除) 验证 ===")
    
    # 1. 初始化数据
    v = Vehicle(type_id=1, id=1, capacity_weight=100, capacity_volume=100, start_cost=400)
    customer_pool = {
        1: Customer(id=1, x=10, y=10, timeWindow=[480, 520]), # 种子
        2: Customer(id=2, x=12, y=12, timeWindow=[490, 530]), # 相似邻居
        3: Customer(id=3, x=100, y=100, timeWindow=[1000, 1100]) # 远方路人
    }
    # 构造距离矩阵
    dist_matrix = [
        [0, 10, 12, 100],
        [10, 0, 2, 90],  # 1-2 很近
        [12, 2, 0, 88],
        [100, 90, 88, 0]
    ]
    
    # 2. 构造 Solution
    sol = Solution()
    route = Route(v)
    route.nodes = [0, 1, 2, 3, 0]
    
    o101 = Order(id=101, customer_id=1, weight=10, volume=5)
    o102 = Order(id=102, customer_id=2, weight=10, volume=5)
    o103 = Order(id=103, customer_id=3, weight=10, volume=5)
    
    route.orders = [[o101], [o102], [o103]]
    sol.routes = [route]
    sol.order2routeMap = {101: 0, 102: 0, 103: 0}
    
    # 3. 执行算子 (移除 2 个，期望移除 101 和 102)
    # 我们通过 random.seed 确保选中 101 作为种子 (或者多试几次)
    import random
    random.seed(1) # 选一个种子确保逻辑命中
    
    print("[执行] 调用 shaw_order_removal 移除 2 个订单...")
    shaw_order_removal(sol, 2, dist_matrix, customer_pool)
    
    # 4. 验证
    removed_ids = [o.order_id for o in sol.unassignedOrders]
    print(f"被移除的订单 IDs: {removed_ids}")
    print(f"剩余节点: {sol.routes[0].nodes if sol.routes else '路径已空'}")
    
    if 101 in removed_ids and 102 in removed_ids:
        print("\n[OK] 成功识别并移除了时空关联度最高的邻居点。")
    else:
        print("\n[FAIL] 算子未能正确识别邻居点。")

if __name__ == "__main__":
    test_shaw()
