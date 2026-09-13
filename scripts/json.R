library(jsonlite)
s <- ""
for (x in 0:9999) s <- toJSON(list(a = c(x, 2, 3), b = "hello"), auto_unbox = TRUE)
cat(s, "\n", sep = "")
