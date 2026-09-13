import json
s = ""
for x in range(10000): s = json.dumps({"a": [x, 2, 3], "b": "hello"}, separators=(",", ":"))
print(s)
