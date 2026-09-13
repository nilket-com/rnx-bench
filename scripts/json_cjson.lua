package.cpath = os.getenv("HOME") .. (jit and "/opt/cjsonjit.so;" or "/opt/cjson54.so;") .. package.cpath
local json = require("cjson")
local s
for x = 0, 9999 do s = json.encode({ a = { x, 2, 3 }, b = "hello" }) end
print(s)
