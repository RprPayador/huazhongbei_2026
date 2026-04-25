'''ALNS(自适应大邻域搜索)算法模块'''

from VRTPW_class import *

class Solution:
    '''解法类'''
    def __init__(self):
        self.routes : list[Route] = [] # 所有路径列表
        self.orders : list[Order] = [] # 所有订单列表,下标是订单编号
        self.customers : list[Customer] = [] # 所有客户列表，下标是客户编号
        self.vehiclesNum = [60, 50, 50, 10, 15] # 车辆数量
        self.distanceMat : list[list[float]] = [] # 距离矩阵二维数组

    def preprocessData(self):
        '''数据预处理函数：从文件读取数据集'''
        pass

    def initSolution(self):
        '''初始化解法函数：生成初始解'''
        pass