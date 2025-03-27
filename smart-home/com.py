import time
import random

def one(x):
    if x>0:
        return 1
    return 0
def equ(x,y):
    return (1-one(x-y))*(1-one(y-x))    
def Сom(x):
    for t in range(x):
        com="П"*(1-one((t%3)))+"К"*(1-one(2-(t%3)))+"T"*one(1-(1-one((t%3)))-(1-one(2-(t%3))))
        print(com,end="\r")
        time.sleep(1)

def train(g1,g2,g3,m1,m2,m3,x=65,v=10):
    M=[m1,m2,m3]
    G=[g1,g2,g3]
    i=0
    m=M[i]
    for t in range(x):
        semofor=1*(1-one((G[i]-m+M[i])))+0*(1-(1-one((m-M[i])))*(1-one((M[i]-m))))*one((G[i]-m+M[i]))
        semofor_text="Закрыт"*semofor+"Открыт"*(1-semofor)
        vagon_text="Cтоять"*(1-semofor)+"Ехать"*(semofor)
        print(m,semofor_text,"\t",vagon_text)
        
        i+=1*semofor
        m=M[i]*semofor+(m+v)*(1-semofor)
        # time.sleep(1)
        
def rand(number):
    digits = list(str(number))
    sdvig=int(len(digits)/4)
    a=digits[:sdvig]
    a=a+(digits[len(digits)-sdvig:])
    b=digits[sdvig:len(digits)-sdvig]
    s=a+b
    s1=b+a
    print(int(''.join(s))*int(''.join(s1))/10**(2*len(digits)-1))


def romantic():
    Np=[]
    for i in range(0,100):
       
        is_life=0
        N=0
        while(is_life<5):
            r=random.randint(-1,1)
            if r==0:
                r=1
            is_life+=r
            N+=1
        else:
            Np.append(N)

    print(sum(Np)/len(Np))

try:    
    train(200,100,300,20,10,30)
except:
    print("Кончились вагоны")


# import numpy as np
# import math
# import random
# import sympy
# import matplotlib.pyplot as plt

# def generator_gap(x):
#     return (-1/x)*math.log(random.uniform(0,1))




# def service(requests,number_queue):
#     table={
#         "запросы": requests,
#         "канал 1": [],
#         "канал 2": [],
#         "обслуженно": [],
#         "отказ": []
#     }
#     for i in range(number_queue):
#         table[f"очередь {i+1}"] = []

#     choice_col=list(table.keys())[2:0:-1]

#     choice_queue=list(table.keys())[5:]
#     choice_queue
#     print(choice_queue)
#     for req in requests:
#         is_suself=False
#         for kanal in choice_col:            
#             if not table[kanal]:
#                 table[kanal].append(round(generator_gap(kanal_mu[kanal]),3))
#                 table['обслуженно'].append((table[kanal][-1],table["запросы"].index(req)))
#                 is_suself=True
#                 break
#             elif table[kanal][-1]<=req:
#                 table[kanal].append(round(table[kanal][-1]+generator_gap(kanal_mu[kanal]),3))
#                 table['обслуженно'].append((table[kanal][-1],table["запросы"].index(req)))
#                 is_suself=True
#                 break

                
#         if is_suself:
#             continue
#         near_time=min(table["канал 1"][-1],table["канал 2"][-1])
#         near_kanal="канал 2" if table["канал 2"][-1]==near_time else "канал 1"
        
#         if table[f"очередь {number_queue}"]:
#             if table[f"очередь {number_queue}"][-1]>=req:
#                 table['отказ'].append((req,table["запросы"].index(req)))
#                 is_suself=True
#                 continue
        
#         near_queue=number_queue
#         for i in range(number_queue-1,-1,-1):
#             if table[f"очередь {i+1}"]:
#                 if table[f"очередь {i+1}"][-1]<=req:
#                     near_queue=i
#                 else:
#                     break
#             else:
#                 near_queue=i+1
                         
#         enum=[near_kanal]+choice_queue[:near_queue]
#         enum.reverse()
#         for i in range(1,len(enum)):
#             if not table[enum[i-1]]:
#                 table[enum[i-1]].append(req)
#                 table[enum[i-1]].append(table[enum[i]][-1])
#             elif table[enum[i-1]][-1]>req:
#                 table[enum[i-1]].append(req)
#                 table[enum[i-1]].append(table[enum[i]][-1])
        
#         table[near_kanal].append(round(near_time+generator_gap(kanal_mu[near_kanal]),3))
#         table['обслуженно'].append((table[near_kanal][-1],table["запросы"].index(req)))
                    

#     return table   

# lamd=10
# mu_1=2
# mu_2=8
# kanal_mu={
#     "канал 1": mu_1,
#     "канал 2": mu_2
# }
Сom(30)