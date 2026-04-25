class Test:
    def __init__(self):
        self.a = 1

def func(l):
    l[1].a = 2
    return l
l=[Test(),Test(),Test()]
class Test2:
    def __init__(self,l):
        self.l=l
    def fun(self):
        self.l[0].a = 2
        return self.l
    
T2 = Test2(l)
l2=func(T2.fun())
l2[2].a=2
print()