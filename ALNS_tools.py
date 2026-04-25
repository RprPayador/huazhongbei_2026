'''ALNS(自适应大邻域搜索)算法模块'''

from VRTPW_class import *

class Solution:
    '''解法类'''
    def __init__(self):
        self.routes : list[Route] = [] # 所有路径列表
        self.vehiclesTimeTable : dict[int, list] = {} # 车辆时间表, key是车辆编号, value是车辆的时间表
        self.order2routeMap : dict[int, int] = {} # 订单到路径的映射, key是订单编号, value是routes的索引值
        self.unassignedOrders : list[Order] = [] # 未分配的订单列表

    def initSolution(self):
        '''初始化解法函数：生成初始解'''
        pass