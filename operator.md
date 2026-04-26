# 破坏算子最终实施计划：随机订单移除 (适配嵌套列表)

本计划基于 `ALNS_tools.py` 现有的 `Solution` 类及 `Route.orders` 的嵌套列表结构进行开发。

## 关键设计：点位坍塌逻辑

IMPORTANT

**嵌套列表移除**：当从 `route.orders[i]` 中移除最后一个订单时，不仅要删除该订单，还要删除整个子列表 `route.orders[i]` 以及对应的客户节点 `route.nodes[i+1]`。

---

## 拟定变更内容

### 1. 算子逻辑实现 [operator.py]

#### [NEW] operator.py

**详细实现逻辑：**

1. **样本准备**：
    - 获取 `solution.order2routeMap` 中所有的订单 ID。
    - 随机抽取 `n_remove` 个 ID。
2. **执行移除循环**：
    - 根据订单 ID 找到 `route_idx`。
    - 在 `solution.routes[route_idx].orders`（嵌套列表）中搜索该订单。
    - **移除操作**：
        - 从所属子列表中 `remove` 该订单。
        - 如果该子列表变为空：
            - `del route.orders[sub_idx]`
            - `del route.nodes[sub_idx + 1]`（跳过索引 0 的配送中心）。
    - **状态同步**：
        - 将订单对象加入 `solution.unassignedOrders`。
        - 从 `solution.order2routeMap` 中删除该 ID 映射。
3. **全局索引维护**：
    - 如果有路径因为订单全被删空而导致 `len(route.orders) == 0`：
        - 从 `solution.routes` 中移除该路径。
        - **重新构建 `order2routeMap`**：确保剩余所有订单对应的 `route_idx` 依然指向正确的 `routes` 列表位置。
4. **费用刷新**：
    - 对所有被修改过的 `Route` 实例调用 `calc_route_total_cost`。


# 实施计划：时空相似度移除算子 (Shaw Removal)

本计划旨在实现 Shaw 提出的相似度移除算子，通过移除在时间和空间上“强相关”的订单簇，为修复算子创造大规模重组的机会。

## 关联度函数定义

IMPORTANT

**$R(i, j)$ 计算公式**： $R(i, j) = \alpha \cdot d_{ij} + \beta \cdot |T_i - T_j| + \gamma \cdot |D_i - D_j|$ 其中：

- $d_{ij}$：客户 $i$ 与 $j$ 之间的距离。
- $T_i, T_j$：时间窗中点 $(Start + End) / 2$。
- $D_i, D_j$：订单需求重量之差。
- $\alpha, \beta, \gamma$ 为权重（初步设定：$\alpha=1.0, \beta=0.5, \gamma=0.1$）。

---

## 拟定变更内容

### 1. 算子实现 [operators.py]

#### [MODIFY] operators.py

**新增 `shaw_order_removal` 函数：**

1. **种子选择**：从 `solution.order2routeMap` 中随机抽取一个订单作为 `seed_oid`。
2. **计算全员关联度**：
    - 获取种子订单的客户坐标、时间窗和载重。
    - 对 `solution` 中剩余的所有已分配订单：
        - 计算其相对于种子订单的地理距离（查表）。
        - 计算时间窗中点差距。
        - 计算需求量差距。
        - 汇总得到关联度得分。
3. **选择并移除**：
    - 按得分从小到大排序。
    - 选取最相似的前 `n_remove` 个订单。
    - 调用 `_remove_specific_orders` 执行正式移除及索引维护。

---

## 验证计划

### 自动化测试 [test_shaw_removal.py]

1. **构造测试场景**：
    - 设置一个种子客户点。
    - 周边 5km 处有一个“邻居”客户。
    - 远处 100km 处有一个“远房”客户。
2. **执行算子**：
    - 设置 `n_remove = 1`。
    - 验证：种子是选中的情况下，算子是否优先移除 5km 处的邻居。
3. **时间窗验证**：
    - 如果两个点位置一样，但一个要求 08:00 送，另一个要求 20:00 送，验证算子是否能识别出它们其实不相似。

---

**计划已就绪。如果批准，我立刻开始编写代码。**


# 路径移除

收到，最后一个破坏算子：**路径移除 (Route Removal)**。

这个算子非常简单粗暴，但极具破坏力。它不是针对单个订单，而是直接“干掉”整条路线，让这辆车的所有订单全部重排。这在解决某辆车路径极度不合理时非常有效。

### Route Removal 逻辑：

1. **随机选车**：从当前 `solution.routes` 中随机挑选 $n$ 条路径。
2. **全员撤单**：
    - 遍历选中的每条路径。
    - 将路径上所有的订单（嵌套列表里的所有 Order 对象）全部取出，扔进 `solution.unassignedOrders`。
3. **物理清空**：
    - 直接从 `solution.routes` 列表中删掉这些路径。
4. **同步索引**：
    - 调用我们写好的 `_rebuild_maps_and_costs`，它会自动重刷 `order2routeMap`，并把剩下的车重新排好索引。

---

### 实施计划书 (V7)：

#### [MODIFY] 

![](vscode-file://vscode-app/c:/Users/18392/AppData/Local/Programs/Antigravity/resources/app/extensions/theme-symbols/src/icons/files/python.svg)

operators.py

**新增 `route_removal` 函数：**

- **输入**：`solution`, `n_routes_to_remove`。
- **逻辑**：
    - `random.sample` 选出目标路径。
    - 提取订单到未分配池。
    - `solution.routes.remove(route)`。
    - 刷新全局状态。

**这个算子逻辑很直观，如果没问题，回复“开始”我立刻实现。**