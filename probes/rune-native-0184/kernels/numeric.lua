local function main(x)
	local n = 0
	local total = 0
	while n < x do total = total + n % 17; n = n + 1 end
	return total
end
return main
