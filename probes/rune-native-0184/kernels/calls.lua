local function add(a, b) return a + b end
local function main(x)
	local total = 0
	for i = 0, x - 1 do total = add(total, i) end
	return total
end
return main
