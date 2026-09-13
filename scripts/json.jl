using JSON
s = ""
for x in 0:9999
    global s = JSON.json(Dict("a" => [x, 2, 3], "b" => "hello"))
end
println(s)
