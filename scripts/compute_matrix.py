"""Small independent ports; complex AWFY and shared-row ports stay unavailable."""

PYTHON = '''def fib(n):
	return n if n < 2 else fib(n - 1) + fib(n - 2)

def kernel(seed):
	if NAME == "fib":
		return fib(20 + seed % 2)
	if NAME == "loops":
		total = seed
		for i in range(10000):
			total = (total + i % 97) % 1000000007
		return total
	if NAME == "numeric_calls":
		def step(x, y):
			return (x * 17 + y * 31) % 1000003
		for i in range(10000):
			seed = step(seed, i)
		return seed
	values = []
	for i in range(SIZE):
		values.append((i + seed) % 3 == 0 if BOOL else (i + seed) % 97)
	total = 0
	for _ in range(8):
		subtotal = 0
		for value in values:
			if BOOL:
				if value:
					subtotal += 1
			else:
				subtotal += value
		total = (total + subtotal) % 1000000007
	return total

checksum = 0
for i in range(ROUNDS):
	checksum = (checksum + kernel(i % 97 + 1)) % 1000000007
print(checksum)
'''

JAVASCRIPT = '''function fib(n) {
	return n < 2 ? n : fib(n - 1) + fib(n - 2);
}
function step(x, y) { return (x * 17 + y * 31) % 1000003; }
function kernel(seed) {
	if (NAME === "fib") return fib(20 + seed % 2);
	if (NAME === "loops") {
		let total = seed;
		for (let i = 0; i < 10000; ++i) total = (total + i % 97) % 1000000007;
		return total;
	}
	if (NAME === "numeric_calls") {
		for (let i = 0; i < 10000; ++i) seed = step(seed, i);
		return seed;
	}
	const values = [];
	for (let i = 0; i < SIZE; ++i) values.push(BOOL ? (i + seed) % 3 === 0 : (i + seed) % 97);
	let total = 0;
	for (let repeat = 0; repeat < 8; ++repeat) {
		let subtotal = 0;
		for (const value of values) {
			if (BOOL) { if (value) ++subtotal; }
			else subtotal += value;
		}
		total = (total + subtotal) % 1000000007;
	}
	return total;
}
let checksum = 0;
for (let i = 0; i < ROUNDS; ++i) checksum = (checksum + kernel(i % 97 + 1)) % 1000000007;
console.log(checksum);
'''


def port(name, language, rounds):
	if name in ("awfy_sieve", "awfy_permute", "shared_rows"):
		return None
	assert name in ("fib", "loops", "numeric_calls", "vec_iter_i64", "vec_iter_bool",
					"vec_append_million_i64", "vec_append_million_bool")
	size = 1000000 if "million" in name else 10000
	boolean = name.endswith("bool")
	if language == "python":
		return f'NAME={name!r}\nSIZE={size}\nBOOL={boolean!r}\nROUNDS={rounds}\n' + PYTHON
	assert language == "javascript"
	return (f'const NAME={name!r}, SIZE={size}, BOOL={str(boolean).lower()}, ROUNDS={rounds};\n'
			+ JAVASCRIPT)
