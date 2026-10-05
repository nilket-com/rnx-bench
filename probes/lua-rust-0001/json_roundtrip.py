import json
print(json.loads(json.dumps({"answer":42}))["answer"])
