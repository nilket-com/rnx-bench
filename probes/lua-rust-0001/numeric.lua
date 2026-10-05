local s=0
for i=1,1000000 do s=(s+i)%1000003 end
print(s)
