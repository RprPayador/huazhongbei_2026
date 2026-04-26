import numpy as np
import copy
import time
import random
from ALNS_tools import Solution
from operators import *

class ALNS_Solver:
    def __init__(self, sol_initial, dist_matrix, customer_pool, vehicle_pool):
        self.current_sol = sol_initial
        self.best_sol = copy.deepcopy(sol_initial)
        self.dist_matrix = dist_matrix
        self.customer_pool = customer_pool
        self.vehicle_pool = vehicle_pool
        
        # 破坏算子配置
        self.removal_ops = [random_order_removal, worst_order_removal, shaw_order_removal, route_removal]
        self.removal_weights = np.ones(len(self.removal_ops))
        self.removal_scores = np.zeros(len(self.removal_ops))
        self.removal_counts = np.zeros(len(self.removal_ops))
        
        # 修复算子配置 (使用我们优化过的 greedy_repair 和 regret_repair)
        self.repair_ops = [greedy_repair, regret_repair]
        self.repair_weights = np.ones(len(self.repair_ops))
        self.repair_scores = np.zeros(len(self.repair_ops))
        self.repair_counts = np.zeros(len(self.repair_ops))
        
        # ALNS 超参数
        self.rho = 0.2          # 权重反应因子 (0-1)
        self.theta1 = 20        # 发现全局最优解的奖励
        self.theta2 = 12        # 发现更优当前解的奖励
        self.theta3 = 8         # 接受了较差解的奖励
        
        # 模拟退火控制参数
        self.T = 100.0          # 初始温度 (根据费用量级可调)
        self.c = 0.9995         # 冷却系数
        self.min_T = 0.1        # 最低温度
        
    def _select_operator(self, weights):
        '''轮盘赌选择算子'''
        prob = weights / np.sum(weights)
        return np.random.choice(len(weights), p=prob)

    def solve(self, max_iter=500, update_period=50):
        '''主求解循环'''
        print(f"开始 ALNS 优化，初始费用: {self.current_sol.total_cost:.2f}, 初始未分配: {len(self.current_sol.unassignedOrders)}")
        start_time = time.time()
        
        for i in range(max_iter):
            # 1. 深度备份当前解
            temp_sol = copy.deepcopy(self.current_sol)
            
            # 2. 轮盘赌选择算子
            r_idx = self._select_operator(self.removal_weights)
            p_idx = self._select_operator(self.repair_weights)
            
            # 3. 执行破坏 (随机决定移除规模 10~30 订单)
            n_remove = random.randint(10, 30)
            if self.removal_ops[r_idx] == route_removal:
                # 路径移除逻辑
                self.removal_ops[r_idx](temp_sol, random.randint(1, 2), self.dist_matrix, self.customer_pool)
            else:
                self.removal_ops[r_idx](temp_sol, n_remove, self.dist_matrix, self.customer_pool)
            
            # 4. 执行修复
            self.repair_ops[p_idx](temp_sol, self.dist_matrix, self.customer_pool, self.vehicle_pool)
            
            # 5. 计算收益并更新解
            new_cost = temp_sol.total_cost
            old_cost = self.current_sol.total_cost
            delta = new_cost - old_cost
            
            score_type = 0
            # 接受准则
            if new_cost < self.best_sol.total_cost - 1e-3:
                # 发现全局最优
                self.best_sol = copy.deepcopy(temp_sol)
                self.current_sol = temp_sol
                score_type = 1 # 奖励 theta1
                print(f"迭代 {i}: [NEW BEST] 费用 = {new_cost:.2f}, 未分配 = {len(temp_sol.unassignedOrders)}, T = {self.T:.2f}")
            elif new_cost < old_cost - 1e-3:
                # 优于当前解
                self.current_sol = temp_sol
                score_type = 2 # 奖励 theta2
            else:
                # 模拟退火概率接受较差解
                p = np.exp(-delta / max(1e-5, self.T))
                if random.random() < p:
                    self.current_sol = temp_sol
                    score_type = 3 # 奖励 theta3
            
            # 6. 更新算子得分
            if score_type == 1:
                self.removal_scores[r_idx] += self.theta1
                self.repair_scores[p_idx] += self.theta1
            elif score_type == 2:
                self.removal_scores[r_idx] += self.theta2
                self.repair_scores[p_idx] += self.theta2
            elif score_type == 3:
                self.removal_scores[r_idx] += self.theta3
                self.repair_scores[p_idx] += self.theta3
            
            self.removal_counts[r_idx] += 1
            self.repair_counts[p_idx] += 1
            
            # 7. 周期性更新算子权重
            if i > 0 and i % update_period == 0:
                self._update_weights()
            
            # 8. 降温
            self.T = max(self.min_T, self.T * self.c)
            
        end_time = time.time()
        print(f"\n优化结束! 耗时: {end_time - start_time:.2f}s")
        print(f"最终最优费用: {self.best_sol.total_cost:.2f}")
        print(f"最终未分配订单: {len(self.best_sol.unassignedOrders)}")
        return self.best_sol

    def _update_weights(self):
        '''根据表现更新权重'''
        for i in range(len(self.removal_weights)):
            if self.removal_counts[i] > 0:
                avg_score = self.removal_scores[i] / self.removal_counts[i]
                self.removal_weights[i] = self.removal_weights[i] * (1 - self.rho) + self.rho * avg_score
                self.removal_scores[i] = 0
                self.removal_counts[i] = 0
        
        for i in range(len(self.repair_weights)):
            if self.repair_counts[i] > 0:
                avg_score = self.repair_scores[i] / self.repair_counts[i]
                self.repair_weights[i] = self.repair_weights[i] * (1 - self.rho) + self.rho * avg_score
                self.repair_scores[i] = 0
                self.repair_counts[i] = 0
