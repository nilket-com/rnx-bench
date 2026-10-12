local function add(rows, key, value)
	for _, row in ipairs(rows) do
		if row[1] == key then
			row[2] = row[2] + value
			return
		end
	end
	rows[#rows + 1] = { key, value }
end
-- Rune's `clone` on a vector is a shallow copy: elements stay shared.
local function clone(rows)
	local copy = {}
	for i = 1, #rows do copy[i] = rows[i] end
	return copy
end
local function main(x)
	local rows = {}
	add(rows, "a", x % 7)
	add(rows, "b", x % 11)
	add(rows, "a", x % 13)
	local copy = clone(rows)
	local alias = copy[1]
	alias[2] = alias[2] + 1
	copy[#copy + 1] = { "c", x % 17 }
	return rows[1][2] * 1000000 + rows[2][2] * 10000 + copy[3][2] * 100 + #rows * 10 + #copy
end
return main
