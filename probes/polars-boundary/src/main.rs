//! Gate-one probe, not an adapter. Fixed fixture schema and observation helpers.
use p::{IntoLazy, NamedFrom, SerReader};
use polars::prelude as p;
use rnx::rune::{self, runtime::Vec as RuneVec};
use std::{fs::File, sync::Arc};
mod engine;

#[derive(rune::Any)]
#[rune(item = ::polars)]
struct DataFrame(p::DataFrame);
#[derive(rune::Any)]
#[rune(item = ::polars)]
struct LazyFrame(p::LazyFrame);
#[derive(rune::Any)]
#[rune(item = ::polars)]
struct LazyGroupBy(p::LazyGroupBy);
#[derive(rune::Any)]
#[rune(item = ::polars)]
struct Expr(p::Expr);
fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}
fn expressions(v: &RuneVec) -> Result<Vec<p::Expr>, String> {
    v.iter()
        .map(|v| v.borrow_ref::<Expr>().map(|e| e.0.clone()).map_err(err))
        .collect()
}
#[rune::function(instance)]
fn lazy(frame: &DataFrame) -> LazyFrame {
    LazyFrame(frame.0.clone().lazy())
}
#[rune::function(instance)]
fn filter(plan: &LazyFrame, expr: &Expr) -> LazyFrame {
    LazyFrame(plan.0.clone().filter(expr.0.clone()))
}
#[rune::function(instance)]
fn group_by(plan: &LazyFrame, keys: &RuneVec) -> Result<LazyGroupBy, String> {
    Ok(LazyGroupBy(plan.0.clone().group_by(expressions(keys)?)))
}
#[rune::function(instance)]
fn agg(group: &LazyGroupBy, values: &RuneVec) -> Result<LazyFrame, String> {
    Ok(LazyFrame(group.0.clone().agg(expressions(values)?)))
}
#[rune::function(instance)]
fn collect(plan: &LazyFrame) -> Result<DataFrame, String> {
    let plan = plan.0.clone();
    engine::run(move || plan.collect().map_err(err))?.map(DataFrame)
}
#[rune::function(instance)]
fn gt(expr: &Expr, rhs: &Expr) -> Expr {
    Expr(expr.0.clone().gt(rhs.0.clone()))
}
#[rune::function(instance)]
fn add(expr: &Expr, rhs: &Expr) -> Expr {
    Expr(expr.0.clone() + rhs.0.clone())
}
#[rune::function(instance, protocol = ADD)]
fn add_protocol(expr: &Expr, rhs: &Expr) -> Expr {
    Expr(expr.0.clone() + rhs.0.clone())
}
#[rune::function(instance)]
fn sum(expr: &Expr) -> Expr {
    Expr(expr.0.clone().sum())
}
#[rune::function(instance)]
fn alias(expr: &Expr, name: &str) -> Expr {
    Expr(expr.0.clone().alias(name))
}
// Fixed shape observer: never formats a whole native table. Tests use small cells.
#[rune::function(instance)]
fn observed(frame: &DataFrame) -> Result<Vec<(String, i64)>, String> {
    let mut rows = vec![];
    let k = frame.0.column("k").map_err(err)?.str().map_err(err)?;
    let v = frame.0.column("v").map_err(err)?.i64().map_err(err)?;
    for i in 0..frame.0.height().min(10) {
        rows.push((
            k.get(i).unwrap_or("<null>").chars().take(80).collect(),
            v.get(i).unwrap_or(i64::MIN),
        ));
    }
    rows.sort();
    Ok(rows)
}
fn fixture() -> Result<DataFrame, String> {
    engine::run(fixture_frame)?.map(DataFrame)
}
fn fixture_frame() -> Result<p::DataFrame, String> {
    p::DataFrame::new(
        3,
        vec![
            p::Series::new("k".into(), ["a", "a", "🦀"]).into(),
            p::Series::new("v".into(), [1i64, 2, 3]).into(),
        ],
    )
    .map_err(err)
}
fn csv(path: &str, mode: &str) -> Result<Vec<String>, String> {
    let path = path.to_owned();
    let mode = mode.to_owned();
    engine::run(move || csv_engine(&path, &mode))?
}
fn csv_engine(path: &str, mode: &str) -> Result<Vec<String>, String> {
    let schema = Arc::new(p::Schema::from_iter([
        ("k".into(), p::DataType::String),
        ("v".into(), p::DataType::Int64),
    ]));
    let options = p::CsvReadOptions::default().with_has_header(true);
    let options = match mode {
        "schema" => options.with_schema(Some(schema)),
        "dtypes" => options
            .with_infer_schema_length(Some(0))
            .with_dtype_overwrite(Some(Arc::new(vec![
                p::DataType::String,
                p::DataType::Int64,
            ]))),
        "header" => options
            .with_infer_schema_length(Some(0))
            .with_n_rows(Some(0)),
        "raw-header" => options
            .with_has_header(false)
            .with_infer_schema_length(Some(0))
            .with_n_rows(Some(1)),
        _ => return Err("unknown mode".into()),
    };
    let frame = options
        .into_reader_with_file_handle(File::open(path).map_err(err)?)
        .finish()
        .map_err(err)?;
    if mode == "raw-header" {
        return frame
            .columns()
            .iter()
            .map(|c| {
                c.str()
                    .map_err(err)?
                    .get(0)
                    .map(str::to_owned)
                    .ok_or("null header".into())
            })
            .collect();
    }
    Ok(frame
        .get_column_names()
        .iter()
        .map(|s| s.to_string())
        .collect())
}
// Test-only observation helpers in this source-only probe.
fn nested() -> Result<(usize, usize), String> {
    engine::run(|| {
        let inner = engine::run(|| fixture_frame()?.lazy().collect().map_err(err))??;
        let outer = fixture_frame()?.lazy().collect().map_err(err)?;
        Ok((inner.height(), outer.height()))
    })?
}
fn overlap() -> Result<(usize, usize), String> {
    let barrier = std::sync::Barrier::new(2);
    std::thread::scope(|scope| {
        let job = || {
            engine::run(|| {
                barrier.wait(); // Both engine workers must be alive at once.
                fixture_frame()?
                    .lazy()
                    .collect()
                    .map(|f| f.height())
                    .map_err(err)
            })?
        };
        let a = scope.spawn(job);
        let b = scope.spawn(job);
        Ok((a.join().unwrap()?, b.join().unwrap()?))
    })
}
fn build(m: &mut rune::Module) -> Result<Vec<(String, &'static str)>, String> {
    m.ty::<DataFrame>().map_err(err)?;
    m.ty::<LazyFrame>().map_err(err)?;
    m.ty::<LazyGroupBy>().map_err(err)?;
    m.ty::<Expr>().map_err(err)?;
    m.function("fixture", fixture).build().map_err(err)?;
    m.function("csv", csv).build().map_err(err)?;
    m.function("engine_counts", engine::counts)
        .build()
        .map_err(err)?;
    m.function("nested", nested).build().map_err(err)?;
    m.function("overlap", overlap).build().map_err(err)?;
    m.function("engine_error", || {
        engine::run(|| Err::<(), String>("expected engine error".into()))?
    })
    .build()
    .map_err(err)?;
    m.function("col", |name: &str| Expr(p::col(name)))
        .build()
        .map_err(err)?;
    m.function("lit", |v: i64| Expr(p::lit(v)))
        .build()
        .map_err(err)?;
    m.function_meta(lazy).map_err(err)?;
    m.function_meta(filter).map_err(err)?;
    m.function_meta(group_by).map_err(err)?;
    m.function_meta(agg).map_err(err)?;
    m.function_meta(collect).map_err(err)?;
    m.function_meta(gt).map_err(err)?;
    m.function_meta(add).map_err(err)?;
    m.function_meta(add_protocol).map_err(err)?;
    m.function_meta(sum).map_err(err)?;
    m.function_meta(alias).map_err(err)?;
    m.function_meta(observed).map_err(err)?;
    Ok(vec![])
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with("polars", build))
}
