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


def overwrite_inline():
	return 3 * 999999


def overwrite_mixed():
	return 2 * sum(range(300000))


EXPECTED.update({"overwrite_inline": overwrite_inline(), "overwrite_mixed": overwrite_mixed(),
	"overwrite_deep": "1 2 1", "overwrite_alias": "0 5 4 4"})


# rnx 0175 range controls and the manual-next control (independent Python oracles).
EXPECTED.update({"range_signed": sum(range(0, 1000000)), "range_negative": sum(range(-500000, 500000)),
	"range_while": sum(range(0, 1000000)), "manual_next": f"Some(0) Some(1) Some(2) None {sum(range(100000))}"})
