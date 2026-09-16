use crate::{compile, execute, runtime, sockets};
use rune::Vm;
use serde_json::json;
use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::{mpsc, oneshot};
use tokio_postgres::{Client, NoTls};

const SOURCE: &str = r#"
pub async fn main(mode) {
    if mode == 4 { return probe::count().await?; }
    probe::write().await?;
    if mode == 3 { probe::long_query().await?; }
    else { probe::pause().await; }
    if mode == 0 { panic("handler failed"); }
    if mode == 1 { loop {} }
    if mode == 2 { probe::forever().await; }
    42
}
"#;
async fn connect(url: &str, name: &str) -> (Arc<Client>, tokio::task::JoinHandle<()>) {
    let mut cfg: tokio_postgres::Config = url.parse().unwrap();
    cfg.application_name(name)
        .options("-c statement_timeout=800");
    let (client, connection) = cfg.connect(NoTls).await.unwrap();
    let driver = tokio::spawn(async move {
        connection.await.unwrap();
    });
    (Arc::new(client), driver)
}
async fn lock_value(client: &Client) -> Result<i64, tokio_postgres::Error> {
    client.batch_execute("BEGIN").await.unwrap();
    let result = client
        .query_one("SELECT n FROM pool_probe WHERE id=1 FOR UPDATE NOWAIT", &[])
        .await
        .map(|r| r.get(0));
    client.batch_execute("ROLLBACK").await.unwrap();
    result
}
fn module(client: Arc<Client>, inserted: mpsc::Sender<()>) -> rune::Module {
    let mut m = rune::Module::with_crate("probe").unwrap();
    let c = client.clone();
    m.function("write", move || {
        let (c, inserted) = (c.clone(), inserted.clone());
        async move {
            c.batch_execute(
                "UPDATE pool_probe SET n=1 WHERE id=1; INSERT INTO pool_audit VALUES (1)",
            )
            .await
            .map_err(|e| e.to_string())?;
            inserted.send(()).await.unwrap();
            Ok::<_, String>(())
        }
    })
    .build()
    .unwrap();
    let c = client.clone();
    m.function("long_query", move || {
        let c = c.clone();
        async move {
            c.simple_query("SELECT pg_sleep(120)")
                .await
                .map(|_| ())
                .map_err(|e| e.to_string())
        }
    })
    .build()
    .unwrap();
    m.function("count", move || {
        let c = client.clone();
        async move {
            c.query_one("SELECT count(*) FROM pool_audit", &[])
                .await
                .map(|r| r.get::<_, i64>(0))
                .map_err(|e| e.to_string())
        }
    })
    .build()
    .unwrap();
    m.function("pause", || async {
        tokio::time::sleep(Duration::from_millis(100)).await
    })
    .build()
    .unwrap();
    m.function("forever", || async {
        tokio::time::sleep(Duration::from_secs(120)).await
    })
    .build()
    .unwrap();
    m
}

// Prototype-private single-slot pool actor. The actor owns the client, driver,
// transaction boundary and admission queue. No lease is returned on VM drop;
// a failed VM leads to an awaited ROLLBACK before admitting the next borrower.
// The two rendezvous are observation hooks, not proposed production APIs.
async fn case(url: &str, mode: i64) {
    let baseline = sockets();
    let (monitor, monitor_driver) = connect(url, "server-probe-monitor").await;
    let (client, driver) = connect(url, "server-probe-owner").await;
    let pid: i32 = client
        .query_one("SELECT pg_backend_pid()", &[])
        .await
        .unwrap()
        .get(0);
    let (insert_tx, mut insert_rx) = mpsc::channel(1);
    let (request_tx, mut request_rx) = mpsc::channel(2);
    let (failed_tx, failed_rx) = oneshot::channel();
    let (cleanup_tx, cleanup_rx) = oneshot::channel();
    let (rolled_tx, rolled_rx) = oneshot::channel();
    let (release_tx, release_rx) = oneshot::channel();
    let (stop_tx, stop_rx) = oneshot::channel::<()>();
    let started = Instant::now();
    let owner = tokio::task::spawn_local(async move {
        let (ctx, unit) = compile(module(client.clone(), insert_tx), SOURCE);
        assert_eq!(request_rx.recv().await, Some(mode));
        client.batch_execute("BEGIN").await.unwrap();
        let result = {
            let mut vm = Vm::new(ctx.clone(), unit.clone());
            tokio::select! {
                r = execute(&mut vm, mode, 1_000_000) => r,
                _ = tokio::time::sleep(Duration::from_millis(250)), if mode == 2 => Err("handler deadline".into()),
                _ = stop_rx, if mode == 3 => Err("server shutdown".into()),
            }
        }; // The VM and its native pending query are dropped before rollback.
        assert!(result.is_err(), "{result:?}");
        failed_tx.send(result).unwrap();
        cleanup_rx.await.unwrap();
        let cleanup_start = Instant::now();
        client.batch_execute("ROLLBACK").await.unwrap();
        let cleanup_ms = cleanup_start.elapsed().as_secs_f64() * 1000.;
        rolled_tx.send(cleanup_ms).unwrap();
        release_rx.await.unwrap();
        let next = if mode != 3 {
            assert_eq!(request_rx.recv().await, Some(4));
            let second_pid: i32 = client
                .query_one("SELECT pg_backend_pid()", &[])
                .await
                .unwrap()
                .get(0);
            assert_eq!(pid, second_pid);
            let mut vm = Vm::new(ctx.clone(), unit.clone());
            let value = execute(&mut vm, 4, 1_000_000).await.unwrap();
            Some((second_pid, value))
        } else {
            None
        };
        drop(request_rx); // Stop admission before dropping the last clients.
        drop(unit);
        drop(ctx);
        drop(client);
        driver.await.unwrap(); // A dropped runtime is not the cleanup proof.
        next
    });
    request_tx.send(mode).await.unwrap();
    if mode != 3 {
        request_tx.send(4).await.unwrap();
    }
    insert_rx.recv().await.unwrap();
    let held_error = lock_value(&monitor).await.unwrap_err();
    assert_eq!(held_error.code().unwrap().code(), "55P03");
    let visible: i64 = monitor
        .query_one("SELECT count(*) FROM pool_audit", &[])
        .await
        .unwrap()
        .get(0);
    assert_eq!(visible, 0);
    let active_start = Instant::now();
    if mode == 3 {
        loop {
            let active: bool = monitor.query_one("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid=$1 AND state='active' AND query='SELECT pg_sleep(120)')", &[&pid]).await.unwrap().get(0);
            if active {
                break;
            }
            assert!(active_start.elapsed() < Duration::from_secs(5));
            tokio::time::sleep(Duration::from_millis(2)).await;
        }
        stop_tx.send(()).unwrap();
    } else {
        drop(stop_tx);
    }
    let failure = failed_rx.await.unwrap();
    let expected = match mode {
        0 => "Panicked: handler failed",
        1 => "Halted for unexpected reason `limited`",
        2 => "handler deadline",
        3 => "server shutdown",
        _ => unreachable!(),
    };
    assert_eq!(failure.as_ref().unwrap_err(), expected);
    let sockets_quarantined = sockets();
    assert_eq!(sockets_quarantined, baseline + 2);
    let driver_tasks_quarantined = tokio::runtime::Handle::current()
        .metrics()
        .num_alive_tasks();
    assert_eq!(driver_tasks_quarantined, 2);
    // The queued second request cannot borrow while cleanup is held here.
    assert_eq!(
        lock_value(&monitor)
            .await
            .unwrap_err()
            .code()
            .unwrap()
            .code(),
        "55P03"
    );
    let shutdown_start = Instant::now();
    cleanup_tx.send(()).unwrap();
    let cleanup_ms = rolled_rx.await.unwrap();
    // Independent connection proves lock release and rolled-back contents
    // before the owner is allowed to serve the queued borrower.
    assert_eq!(lock_value(&monitor).await.unwrap(), 0);
    let visible: i64 = monitor
        .query_one("SELECT count(*) FROM pool_audit", &[])
        .await
        .unwrap()
        .get(0);
    assert_eq!(visible, 0);
    release_tx.send(()).unwrap();
    drop(request_tx);
    let next = owner.await.unwrap();
    if let Some((_, ref value)) = next {
        assert_eq!(value, "0");
    }
    let owner_backends: i64 = monitor
        .query_one(
            "SELECT count(*) FROM pg_stat_activity WHERE application_name='server-probe-owner'",
            &[],
        )
        .await
        .unwrap()
        .get(0);
    // PostgreSQL may observe FIN just after the driver's completion. Poll it
    // separately; do not confuse socket ownership with backend lifetime.
    let mut remaining = owner_backends;
    while remaining != 0 {
        assert!(shutdown_start.elapsed() < Duration::from_secs(5));
        tokio::time::sleep(Duration::from_millis(2)).await;
        remaining = monitor
            .query_one(
                "SELECT count(*) FROM pg_stat_activity WHERE application_name='server-probe-owner'",
                &[],
            )
            .await
            .unwrap()
            .get(0);
    }
    drop(monitor);
    monitor_driver.await.unwrap();
    let after = sockets();
    let tasks = tokio::runtime::Handle::current()
        .metrics()
        .num_alive_tasks();
    assert_eq!(after, baseline);
    assert_eq!(tasks, 0);
    println!(
        "{}",
        json!({"case":mode,"failure":failure,"same_backend_reused":next.is_some(),"next":next,"locked_before_rollback_sqlstate":"55P03","visible_after_rollback":visible,"cleanup_ms":cleanup_ms,"shutdown_observation_ms":shutdown_start.elapsed().as_secs_f64()*1000.,"total_ms":started.elapsed().as_secs_f64()*1000.,"sockets_before":baseline,"sockets_quarantined":sockets_quarantined,"sockets_after":after,"tasks_after":tasks,"driver_tasks_quarantined":driver_tasks_quarantined,"backends_after":remaining})
    );
}
pub fn run(url: &str) {
    let rt = runtime();
    let local = tokio::task::LocalSet::new();
    local.block_on(&rt, async {
        for mode in 0..4 {
            tokio::time::timeout(Duration::from_secs(10), case(url, mode))
                .await
                .unwrap();
        }
    });
}
