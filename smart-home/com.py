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

Сom(30)