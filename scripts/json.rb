require "json"
s = ""
10000.times { |x| s = JSON.generate({ "a" => [x, 2, 3], "b" => "hello" }) }
puts s
