# Polars in an rnx session, line by line

Start: `rnx`, then `:dep polars`, answer `y`. First time compiles Polars (~2 min);
after that a new session attaches in seconds. Statements end with `;`,
expressions without `;` print their value — and a frame prints as its bounded
preview (ten rows, eight columns, long cells cut), so you mostly just type its
name. `frame.preview()?` gives the same text as an ordinary string when you
want to keep it, compare it or print it yourself. Files land in your working
directory.

## 1. Make a small CSV and load it

```rune
fs::write_new("sales.csv", "region,item,qty,price\nwest,apple,3,1.5\nwest,pear,1,2.0\neast,apple,5,1.5\neast,plum,2,3.0\nnorth,apple,4,1.5\n")?;
let sales = polars::read_csv("sales.csv", [("region","string"),("item","string"),("qty","i64"),("price","f64")])?;
sales
```

Column types: `string`, `i64`, `f64`, `bool`.

## 2. Filter

```rune
let big = sales.lazy().filter(polars::col("qty").gt(polars::lit(2)?)).collect()?;
big
```

## 3. Group, aggregate, sort

```rune
let by_region = sales.lazy().group_by([polars::col("region")])?.agg([polars::col("qty").sum().alias("units")])?.sort(["region"])?.collect()?;
by_region
```

## 4. Arithmetic on columns

```rune
let bumped = sales.lazy().group_by([polars::col("item")])?.agg([(polars::col("qty") + polars::lit(10)?).sum().alias("qty_plus_10")])?.sort(["item"])?.collect()?;
bumped
```

## 5. A mistake is a value, and the frame survives it

```rune
let oops = sales.lazy().filter(polars::col("missing").gt(polars::lit(1)?)).collect();
oops.is_err()
match oops { Ok(_) => "unexpected", Err(e) => e }
sales
```

A lazy plan stays a plan until you collect it: `sales.lazy()` prints
`<::polars::LazyFrame>`, and so does a plan that would fail — nothing runs
just because you looked at it. A frame inside a vector or a `Result` also
prints as its type; `sales.lazy().collect()` (no `?`) shows
`Ok(<::polars::DataFrame>)`.

## 6. Parquet round trip

```rune
by_region.write_parquet_new("sales.parquet")?;
let back = polars::read_parquet("sales.parquet")?;
back.preview()? == by_region.preview()?
```

## 7. Print it yourself

```rune
println!("{sales}")
format!("{sales}").len()
let text = sales.preview()?;
```

`println!("{sales}")` and `format!("{sales}")` use the same preview, and
`preview()?` is that text as a value you can bind, compare or write to a file.

## 8. Look around

```rune
:vars
:reset
polars::lit(1)?
```

`:vars` lists the bindings with their types (frames are not previewed there).

`:reset` drops your bindings but keeps Polars loaded. `:quit` ends the session;
the printed "Reopen this scratch session" command brings the same executable back
without rebuilding.

Surface today: `polars::read_csv(path, schema)`, `polars::read_parquet(path)`,
`polars::col(name)`, `polars::lit(value)?`; on a frame `.lazy()`, `.preview()?`,
`.write_parquet_new(path)?`; on a lazy plan `.filter(expr)`, `.group_by([exprs])?`,
`.agg([exprs])?`, `.sort([names])?`, `.collect()?`; on an expression `.gt(expr)`,
`+`, `.sum()`, `.alias(name)`.
