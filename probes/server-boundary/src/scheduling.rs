use crate::{compile, execute, runtime};
use rune::Vm;
use serde_json::json;
use std::{
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};

const BUDGET: usize = 10_000_000;
const SOURCE: &str = r#"
pub async fn main(mode) {
    probe::started(mode);
    if mode == 0 { probe::sleep().await; }
    if mode == 1 { loop {} }
    42
}
"#;
struct Job {
    id: usize,
    mode: i64,
    submitted: Instant,
}
struct Done {
    id: usize,
    elapsed_ms: f64,
    result: Result<String, String>,
}

pub fn run() {
    for (model, workers, slow, saturation) in [
        ("shared-await", 1, 0, false),
        ("shared-cpu", 1, 1, false),
        ("two-workers-await", 2, 0, false),
        ("two-workers-cpu", 2, 1, false),
        ("two-workers-saturated", 2, 1, true),
    ] {
        for sample in 0..7 {
            let (done_tx, done_rx) = mpsc::channel::<Done>();
            let (start_tx, start_rx) = mpsc::channel();
            let (ready_tx, ready_rx) = mpsc::channel();
            let mut senders = Vec::new();
            let mut threads = Vec::new();
            for _ in 0..workers {
                let (tx, mut rx) = tokio::sync::mpsc::channel::<Job>(4);
                senders.push(tx);
                let (done_tx, start_tx, ready_tx) =
                    (done_tx.clone(), start_tx.clone(), ready_tx.clone());
                threads.push(thread::spawn(move || {
                    let mut module = rune::Module::with_crate("probe").unwrap();
                    module
                        .function("started", move |mode: i64| {
                            start_tx.send(mode).unwrap();
                        })
                        .build()
                        .unwrap();
                    module
                        .function("sleep", || async {
                            tokio::time::sleep(Duration::from_millis(250)).await
                        })
                        .build()
                        .unwrap();
                    let (context, unit) = compile(module, SOURCE);
                    let rt = runtime();
                    let local = tokio::task::LocalSet::new();
                    ready_tx.send(()).unwrap();
                    local.block_on(&rt, async {
                        let mut tasks = Vec::new();
                        while let Some(job) = rx.recv().await {
                            let (context, unit, done_tx) =
                                (context.clone(), unit.clone(), done_tx.clone());
                            tasks.push(tokio::task::spawn_local(async move {
                                let mut vm = Vm::new(context, unit);
                                let result = execute(&mut vm, job.mode, BUDGET).await;
                                done_tx
                                    .send(Done {
                                        id: job.id,
                                        elapsed_ms: job.submitted.elapsed().as_secs_f64() * 1000.,
                                        result,
                                    })
                                    .unwrap();
                            }));
                        }
                        for task in tasks {
                            task.await.unwrap();
                        }
                    });
                }));
            }
            for _ in 0..workers {
                ready_rx.recv_timeout(Duration::from_secs(10)).unwrap();
            }
            let nslow = if saturation { 2 } else { 1 };
            for (i, sender) in senders.iter().enumerate().take(nslow) {
                sender
                    .blocking_send(Job {
                        id: i,
                        mode: slow,
                        submitted: Instant::now(),
                    })
                    .unwrap();
            }
            // Independent coordinator observes actual VM entry, then submits
            // the healthy request even while an executor cannot poll its queue.
            for _ in 0..nslow {
                assert_eq!(start_rx.recv_timeout(Duration::from_secs(5)).unwrap(), slow);
            }
            let target = if workers == 2 && !saturation { 1 } else { 0 };
            senders[target]
                .blocking_send(Job {
                    id: 2,
                    mode: 2,
                    submitted: Instant::now(),
                })
                .unwrap();
            let mut observed = Vec::new();
            for _ in 0..=nslow {
                let done = done_rx.recv_timeout(Duration::from_secs(10)).unwrap();
                if done.id == 2 || slow == 0 {
                    assert!(done.result.is_ok(), "{:?}", done.result);
                } else {
                    assert!(
                        done.result.as_ref().unwrap_err().contains("limited"),
                        "{:?}",
                        done.result
                    );
                }
                observed
                    .push(json!({"id":done.id,"latency_ms":done.elapsed_ms,"result":done.result}));
            }
            if slow == 0 || (workers == 2 && !saturation) {
                assert_eq!(
                    observed[0]["id"], 2,
                    "healthy request must finish first: {observed:?}"
                );
            }
            drop(senders);
            for thread in threads {
                thread.join().unwrap();
            }
            println!(
                "{}",
                json!({"model":model,"sample":sample,"budget":BUDGET,"sleep_ms":250,"observations":observed})
            );
        }
    }
}
