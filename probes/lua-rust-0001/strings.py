t=[]
for i in range(1,20001): t.append("item:"+str(i))
s="|".join(t)
print(len(s))
print(s[:19])
print(s[-21:])
