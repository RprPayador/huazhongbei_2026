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
        self.removal_op_names = ["Rand", "Wrst", "Shaw", "Rout"]
        self.removal_weights = np.ones(len(self.removal_ops))
        self.removal_scores = np.zeros(len(self.removal_ops))
        self.removal_counts = np.zeros(len(self.removal_ops))
        
        # 修复算子配置
        self.repair_ops = [greedy_repair, regret_repair]
        self.repair_op_names = ["Gred", "Regr"]
        self.repair_weights = np.ones(len(self.repair_ops))
        self.repair_scores = np.zeros(len(self.repair_ops))
        self.repair_counts = np.zeros(len(self.repair_ops))
        
        # ALNS 超参数
        self.rho = 0.15 
        self.theta1 = 30 # 提高发现全局最优的权重
        self.theta2 = 15 
        self.theta3 = 10  
        
        # 【参数提速优化】：
        # 1. 提高初始温度，适应 10w 级的费用
        self.T = 800.0 
        # 2. 加快降温速度，让搜索更聚焦
        self.c = 0.992 
        self.min_T = 0.1
        
    def _select_operator(self, weights):
        prob = weights / np.sum(weights)
        return np.random.choice(len(weights), p=prob)

    def solve(self, max_iter=500, update_period=50):
        print(f"开始 ALNS 提速优化，初始费用: {self.current_sol.total_cost:.2f}\n")
        start_time = time.time()
        
        for i in range(max_iter):
            temp_sol = copy.deepcopy(self.current_sol)
            r_idx = self._select_operator(self.removal_weights)
            p_idx = self._select_operator(self.repair_weights)
            
            # 对于 2000+ 规模的问题，一次移除 40-100 个订单（约 2%-5%）
            # 配合 Regret 算子，这是效率和精度的平衡点
            n_remove = random.randint(40, 100)
            
            if self.removal_ops[r_idx] == route_removal:
                # 路径移除：一次移除 2-4 条路径
                self.removal_ops[r_idx](temp_sol, random.randint(2, 4), self.dist_matrix, self.customer_pool)
            else:
                self.removal_ops[r_idx](temp_sol, n_remove, self.dist_matrix, self.customer_pool)
            
            # 修复
            self.repair_ops[p_idx](temp_sol, self.dist_matrix, self.customer_pool, self.vehicle_pool, temp=self.T)
            
            new_cost = temp_sol.total_cost
            old_cost = self.current_sol.total_cost
            delta = new_cost - old_cost
            
            score_type = 0 
            status = "Reject"
            new_unassigned = len(temp_sol.unassignedOrders)
            best_unassigned = len(self.best_sol.unassignedOrders)
            
            # 由于修复算子现在保证送完，new_unassigned 理论上永远是 0
            if new_cost < self.best_sol.total_cost - 1e-3:
                self.best_sol = copy.deepcopy(temp_sol)
                self.current_sol = temp_sol
                score_type = 1
                status = "BEST  "
            elif new_cost < old_cost - 1e-3:
                self.current_sol = temp_sol
                score_type = 2
                status = "Accept"
            else:
                p = np.exp(-delta / max(1e-5, self.T))
                if random.random() < p:
                    self.current_sol = temp_sol
                    score_type = 3
                    status = "SA_Acc"
            
            if i % 1 == 0: # 每一代输出
                print(f"Iter {i:4d} | Cost={new_cost:9.2f} | Best={self.best_sol.total_cost:9.2f} | Routes={len(temp_sol.routes):3d} | Ops=({self.removal_op_names[r_idx]}+{self.repair_op_names[p_idx]}) | Status={status} | T={self.T:7.2f}")

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
            if i > 0 and i % update_period == 0:
                self._update_weights()
                
            self.T = max(self.min_T, self.T * self.c)
            
        end_time = time.time()
        print(f"\n提速优化结束! 耗时: {end_time - start_time:.2f}s")
        print(f"最终最优费用: {self.best_sol.total_cost:.2f}")
        return self.best_sol

    def _update_weights(self):
        for i in range(len(self.removal_weights)):
            if self.removal_counts[i] > 0:
                avg_score = self.removal_scores[i] / self.removal_counts[i]
                self.removal_weights[i] = self.removal_weights[i] * (1 - self.rho) + self.rho * avg_score
                self.removal_scores[i], self.removal_counts[i] = 0, 0
        for i in range(len(self.repair_weights)):
            if self.repair_counts[i] > 0:
                avg_score = self.repair_scores[i] / self.repair_counts[i]
                self.repair_weights[i] = self.repair_weights[i] * (1 - self.rho) + self.rho * avg_score
                self.repair_scores[i], self.repair_counts[i] = 0, 0

class ALNS_Solver_P2:
    '''问题 2 求解器同步提速参数'''
    def __init__(self, initial_sol, dist_matrix, customer_pool, vehicle_pool):
        self.current_sol = initial_sol
        self.best_sol = copy.deepcopy(initial_sol)
        self.dist_matrix = dist_matrix
        self.customer_pool = customer_pool
        self.vehicle_pool = vehicle_pool
        self.removal_weights = [1.0, 1.0, 1.0, 1.0]
        self.repair_weights = [1.0, 1.0]
        self.removal_op_names = ["Rand", "Wrst", "Shaw", "Rout"]
        self.T = 800.0
        self.c = 0.99
        
    def _select_operator(self, weights):
        total = sum(weights)
        r = random.uniform(0, total)
        curr = 0
        for i, w in enumerate(weights):
            curr += w
            if r <= curr: return i
        return 0

    def solve(self, max_iter=100):
        from operators import (
            random_order_removal, worst_order_removal, shaw_order_removal, route_removal,
            policy_violation_removal, greedy_repair_p2, regret_repair_p2, _rebuild_maps_and_costs
        )
        import copy, random
        print(f"开始 P2 ALNS 提速优化，初始费用: {self.current_sol.total_cost:.2f}\n")
        for i in range(max_iter):
            temp_sol = copy.deepcopy(self.current_sol)
            if i == 0:
                policy_violation_removal(temp_sol, self.customer_pool)
                greedy_repair_p2(temp_sol, self.dist_matrix, self.customer_pool, self.vehicle_pool)
                r_name = "Policy"
            else:
                r_idx = self._select_operator(self.removal_weights)
                removal_ops = [random_order_removal, worst_order_removal, shaw_order_removal, route_removal]
                r_name = self.removal_op_names[r_idx]
                n_remove = random.randint(100, 250)
                if removal_ops[r_idx] == route_removal:
                    removal_ops[r_idx](temp_sol, 4, self.dist_matrix, self.customer_pool)
                else:
                    removal_ops[r_idx](temp_sol, n_remove, self.dist_matrix, self.customer_pool)
                greedy_repair_p2(temp_sol, self.dist_matrix, self.customer_pool, self.vehicle_pool)

            _rebuild_maps_and_costs(temp_sol, self.dist_matrix, self.customer_pool)
            new_cost = temp_sol.total_cost
            if new_cost < self.best_sol.total_cost - 1e-3:
                self.best_sol, self.current_sol = copy.deepcopy(temp_sol), temp_sol
                status = "BEST  "
            else:
                delta = new_cost - self.current_sol.total_cost
                if delta < 0 or random.random() < np.exp(-delta / self.T):
                    self.current_sol = temp_sol
                    status = "SA_Acc"
                else: status = "Reject"

            print(f"Iter {i:4d} | Cost={new_cost:9.2f} | Best={self.best_sol.total_cost:9.2f} | Routes={len(temp_sol.routes):3d} | Op={r_name} | Status={status}")
            self.T *= self.c
        return self.best_sol
