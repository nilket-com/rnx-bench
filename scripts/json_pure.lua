package.path = os.getenv("HOME") .. "/opt/?.lua;" .. package.path
local json = require("json")
local s
for x = 0, 9999 do s = json.encode({ a = { x, 2, 3 }, b = "hello" }) end
print(s)
