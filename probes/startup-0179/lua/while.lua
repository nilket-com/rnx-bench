local s = 0
local i = 1
while i <= 1000000 do s = (s + i) % 1000003; i = i + 1 end
print(s)
