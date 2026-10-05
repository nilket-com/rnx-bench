local names={'string','table','math','io','os','utf8','coroutine'}
local values={string,table,math,io,os,utf8,coroutine}
for i,name in ipairs(names) do print(name..':'..type(values[i])) end
print('require:'..type(require))
for _,name in ipairs({'json','cjson','dkjson'}) do
 local ok,value=pcall(function() return require(name) end)
 print(name..':'..(ok and type(value) or 'unavailable'))
end
