use futures_util::TryStreamExt;
use rnx::rune::Module;
use std::time::Duration;
use tokio_postgres::NoTls;

fn trace(event: &str, tasks: usize) {
    use std::io::Write;
    if let Ok(path) = std::env::var("RNX_PG_PROBE_TRACE") {
        let sockets = std::fs::read_dir("/proc/self/fd")
            .unwrap()
            .filter_map(Result::ok)
            .filter_map(|e| std::fs::read_link(e.path()).ok())
            .filter(|p| p.to_string_lossy().starts_with("socket:["))
            .count();
        writeln!(
            std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .unwrap(),
            "{event} {tasks} {sockets}"
        )
        .unwrap();
    }
}
struct Lifetime(tokio::runtime::Handle);
impl Drop for Lifetime {
    fn drop(&mut self) {
        trace("dropped", self.0.metrics().num_alive_tasks());
    }
}

// All resources are fields/local values of this one future. No spawn, no
// cleanup loop, no private rnx runtime hook.
async fn query(url: String, seconds: f64, timeout_ms: u64, refuse: bool) -> Result<i64, String> {
    let _lifetime = Lifetime(tokio::runtime::Handle::current());
    let work = async {
        let mut config: tokio_postgres::Config = url
            .parse()
            .map_err(|e: tokio_postgres::Error| e.to_string())?;
        config.options(format!("-c statement_timeout={timeout_ms}"));
        let (client, connection) = config.connect(NoTls).await.map_err(|e| e.to_string())?;
        trace(
            "connected",
            tokio::runtime::Handle::current()
                .metrics()
                .num_alive_tasks(),
        );
        let statement = async {
            let statement = client
                .prepare("SELECT 42::bigint AS n FROM pg_sleep($1)")
                .await
                .map_err(|e| e.to_string())?;
            let rows = client
                .query_raw(
                    &statement,
                    [&seconds as &(dyn tokio_postgres::types::ToSql + Sync)],
                )
                .await
                .map_err(|e| e.to_string())?;
            tokio::pin!(rows);
            let mut answer = 0;
            while let Some(row) = rows.try_next().await.map_err(|e| e.to_string())? {
                if refuse {
                    return Err("prototype conversion refusal".into());
                }
                answer = row.try_get(0).map_err(|e| e.to_string())?;
            }
            Ok(answer)
        };
        tokio::pin!(statement);
        tokio::pin!(connection);
        tokio::select! {
            result = &mut statement => result,
            result = &mut connection => Err(format!("connection ended: {result:?}")),
        }
    };
    tokio::time::timeout(Duration::from_millis(timeout_ms), work)
        .await
        .map_err(|_| "prototype deadline".to_owned())?
}
fn build(module: &mut Module) -> Result<Vec<(String, &'static str)>, String> {
    module
        .function("query", query)
        .build()
        .map_err(|e| e.to_string())?;
    Ok(vec![("pg_probe::query".into(), "ownership prototype only")])
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with("pg_probe", build))
}
