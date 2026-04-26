from VRTPW_class import Vehicle, Customer, Order, Route
from ALNS_tools import Solution
from operators import random_order_removal

def test_removal_logic():
    print("=== 开始算子逻辑验证 ===")
    
    # 1. 初始化基础数据
    v = Vehicle(type_id=1, id=1, capacity_weight=100, capacity_volume=100, start_cost=400)
    customer_pool = {
        1: Customer(id=1, x=10, y=10, timeWindow=[500, 600]),
        2: Customer(id=2, x=20, y=20, timeWindow=[600, 700])
    }
    dist_matrix = [[0, 10, 20], [10, 0, 5], [20, 5, 0]]
    
    # 2. 构造 Solution 和路径 (嵌套结构)
    sol = Solution()
    route = Route(v)
    route.nodes = [0, 1, 2, 0]
    
    o101 = Order(id=101, customer_id=1, weight=10, volume=5)
    o102 = Order(id=102, customer_id=2, weight=10, volume=5)
    o103 = Order(id=103, customer_id=2, weight=10, volume=5)
    
    # 注意这里是嵌套列表：[[客户1的订单], [客户2的订单]]
    route.orders = [[o101], [o102, o103]]
    sol.routes = [route]
    sol.order2routeMap = {101: 0, 102: 0, 103: 0}
    
    print(f"初始状态：Nodes={route.nodes}, Orders长度={[len(s) for s in route.orders]}")
    
    # 3. 测试场景 A：移除 102 (客户2 还有 103，点位不应坍塌)
    print("\n[测试A] 移除订单 102 (客户2仍有剩余订单):")
    # 我们通过修改 n_remove 和 random.sample 的性质来模拟指定移除
    # 这里直接调用算子，由于是随机的，我们可能需要多试几次或者 hack 一下逻辑
    # 为了精准测试，我们直接传 n_remove=1 并祈祷或手动指定
    import random
    random.seed(42) # 固定随机种子以确保选中 102 (取决于 Python 版本，如果没中我们看日志)
    
    random_order_removal(sol, 1, dist_matrix, customer_pool)
    
    print(f"执行后 Nodes: {route.nodes}")
    print(f"执行后 Orders分布: {[len(s) for s in route.orders]}")
    print(f"未分配池大小: {len(sol.unassignedOrders)}")
    
    # 4. 测试场景 B：移除 101 (客户1 唯一的订单，点位应该坍塌)
    print("\n[测试B] 移除订单 101 (客户1唯一订单，应触发坍塌):")
    # 此时剩下的订单 ID 为 [101, 103] (假设刚才移除了102)
    random_order_removal(sol, 1, dist_matrix, customer_pool)
    
    print(f"执行后 Nodes: {route.nodes}")
    print(f"执行后 Orders分布: {[len(s) for s in route.orders]}")
    
    print("\n=== 验证结束 ===")

if __name__ == "__main__":
    test_removal_logic()
