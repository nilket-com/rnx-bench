let s = "";
for (let x = 0; x < 10000; x++) s = JSON.stringify({ a: [x, 2, 3], b: "hello" });
console.log(s);
