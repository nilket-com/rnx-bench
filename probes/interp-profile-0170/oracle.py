"""Independent expected outputs for the 0170 kernels (the 0168 fixtures keep their own oracles)."""
def while_():
	s = 0
	for i in range(1, 1000001):
		s = (s + i) % 1000003
	return s
def compare():
	return sum(1 for i in range(1000000) if (i * 7) % 13 < 6)
def calls():
	return 1000000
def vector():
	v = [i % 97 for i in range(100000)]
	return 10 * sum(v)
EXPECTED = {"while": while_(), "compare": compare(), "calls": calls(), "vector": vector()}
if __name__ == "__main__":
	for k, v in EXPECTED.items():
		print(k, v)
