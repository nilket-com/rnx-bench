local t={}
for i=1,20000 do t[i]="item:"..i end
local s=table.concat(t,"|")
print(#s)
print(string.sub(s,1,19))
print(string.sub(s,-21))
