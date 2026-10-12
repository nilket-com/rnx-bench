-- P2 first-probe repeat harness for LuaJIT, v3 (derived from the P0 harness
-- 0184-p0-impl1/harness/repeat-input.lua, which keeps gap1's math.type port verbatim).
-- usage: repeat-input-v3.lua KERNEL.lua K INPUTS.txt PHASES.txt|- [transcript|markers]
--
-- Changes from the P0 harness:
--   1. PHASES "-" writes no phases file (validation runs record no timing).
--   2. "transcript" (validation only, never timed) prints each invocation's result on its
--      own line before the checksum line.
--   3. "markers" (diagnostic only, never timed) writes "INVOCATION i" to stderr before each
--      call, so a -jv / -jdump log shows in which invocation each trace was recorded.
--      LuaJIT's trace compilation is otherwise not separately observable: "first" is the
--      literal first invocation, including whatever tracing happens during it.
-- Timing mode is otherwise identical: prepare once (loadfile + one chunk call), read the
-- first K inputs, call main(x) K times, fold each result into the checksum, print ONE line.
local path, k, inputs, phases, mode = arg[1], tonumber(arg[2]), arg[3], arg[4], arg[5]
assert(path and k and k >= 1 and k == math.floor(k), "usage: repeat-input-v3.lua KERNEL.lua K INPUTS PHASES|- [transcript|markers]")
assert(inputs and phases, "usage: repeat-input-v3.lua KERNEL.lua K INPUTS PHASES|- [transcript|markers]")
assert(mode == nil or mode == "transcript" or mode == "markers", "mode: transcript or markers")

local now = function() return "na" end
local ok, ffi = pcall(require, "ffi")
if ok then
	ffi.cdef[[
		typedef struct { long tv_sec; long tv_nsec; } p0_timespec;
		int clock_gettime(int clk, p0_timespec *ts);
	]]
	local ts = ffi.new("p0_timespec")
	now = function()
		ffi.C.clock_gettime(1, ts) -- CLOCK_MONOTONIC
		return string.format("%d", tonumber(ts.tv_sec) * 1000000000 + tonumber(ts.tv_nsec))
	end
end
local t_start = now()

local xs = {}
local f = assert(io.open(inputs, "r"))
for line in f:lines() do
	if #xs == k then break end
	xs[#xs + 1] = assert(tonumber(line))
end
f:close()
assert(#xs == k, "not enough inputs")

local chunk = assert(loadfile(path))
local main = chunk()
assert(type(main) == "function", "kernel must return main")
local t_ready = now()

local checksum = 0
local r, t_first
if mode == nil then
	-- Timing mode: exactly the P0 harness's loop.
	r = main(xs[1])
	checksum = (checksum * 31 + r) % 1000000007
	t_first = now()
	for i = 2, k do
		r = main(xs[i])
		checksum = (checksum * 31 + r) % 1000000007
	end
else
	-- Validation and diagnostic modes only; never timed.
	for i = 1, k do
		if mode == "markers" then io.stderr:write(string.format("INVOCATION %d\n", i)) end
		r = main(xs[i])
		checksum = (checksum * 31 + r) % 1000000007
		if mode == "transcript" then io.write(string.format("%d\n", r)) end
		if i == 1 then t_first = now() end
	end
end
local t_done = now()

if phases ~= "-" then
	local p = assert(io.open(phases, "w"))
	p:write(string.format("start %s\nready %s\nfirst %s\ndone %s\n", t_start, t_ready, t_first, t_done))
	p:close()
end
print(string.format("CHECKSUM %d invocations=%d", checksum, k))
