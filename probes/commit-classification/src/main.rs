use serde_json::json;
use std::time::Duration;
use tokio_postgres::{Client, NoTls};
struct Connection {
    client: Client,
    driver: tokio::task::JoinHandle<Result<(), tokio_postgres::Error>>,
    pid: i32,
}
impl Connection {
    async fn open(url: &str) -> Self {
        let (client, connection) = tokio_postgres::connect(url, NoTls).await.unwrap();
        let driver = tokio::spawn(connection);
        let pid = client
            .query_one("SELECT pg_backend_pid()", &[])
            .await
            .unwrap()
            .get(0);
        client
            .batch_execute("SET statement_timeout='8s'")
            .await
            .unwrap();
        Self {
            client,
            driver,
            pid,
        }
    }
    async fn close(self) {
        drop(self.client);
        tokio::time::timeout(Duration::from_secs(2), self.driver)
            .await
            .unwrap()
            .unwrap()
            .unwrap();
    }
}
async fn scalar(client: &Client, sql: &str) -> i64 {
    client.query_one(sql, &[]).await.unwrap().get(0)
}
async fn commands(client: &Client, sql: &str) {
    client.batch_execute(sql).await.unwrap();
}
// Only an ERROR reply to the single outstanding COMMIT can use this allowlist.
// FATAL/connection termination, other SQLSTATEs and non-server errors stay unknown.
fn classification(error: &tokio_postgres::Error) -> &'static str {
    match error.as_db_error() {
        Some(db)
            if db.parsed_severity() == Some(tokio_postgres::error::Severity::Error)
                && (db.code().code().starts_with("23")
                    || matches!(db.code().code(), "40001" | "40P01")) =>
        {
            "rejected"
        }
        _ => "ambiguous",
    }
}
async fn case(url: &str, mode: &str) {
    let observer = Connection::open(url).await;
    let victim = Connection::open(url).await;
    commands(&observer.client, "DROP SCHEMA IF EXISTS commit_probe CASCADE; CREATE SCHEMA commit_probe; SET search_path=commit_probe;
        CREATE TABLE parent(id int PRIMARY KEY);
        CREATE TABLE child(id int REFERENCES parent DEFERRABLE INITIALLY DEFERRED);
        CREATE TABLE audit(id text PRIMARY KEY);
        CREATE TABLE skew(id int PRIMARY KEY, n int); INSERT INTO skew VALUES(1,0),(2,0);
        CREATE TABLE dead(id int PRIMARY KEY);
        CREATE FUNCTION deferred_lock() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_advisory_xact_lock(222); RETURN NEW; END $$;
        CREATE CONSTRAINT TRIGGER lock_on_commit AFTER INSERT ON dead DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deferred_lock();").await;
    commands(&victim.client, "SET search_path=commit_probe").await;
    let other = Connection::open(url).await;
    commands(&other.client, "SET search_path=commit_probe").await;
    let pid = victim.pid;
    let waiting;
    if mode == "deferred" {
        commands(
            &victim.client,
            "BEGIN; INSERT INTO audit VALUES('victim'); INSERT INTO child VALUES(7)",
        )
        .await;
        waiting = Some(tokio::spawn(async move {
            other.close().await;
        }));
    } else if mode == "unclassified" {
        commands(&observer.client, "CREATE OR REPLACE FUNCTION deferred_lock() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION USING ERRCODE='40003', MESSAGE='fixture unknown completion'; END $$").await;
        commands(
            &victim.client,
            "BEGIN; INSERT INTO audit VALUES('victim'); INSERT INTO dead VALUES(1)",
        )
        .await;
        waiting = Some(tokio::spawn(async move {
            other.close().await;
        }));
    } else if mode == "serialization" {
        commands(&victim.client, "BEGIN ISOLATION LEVEL SERIALIZABLE").await;
        commands(&other.client, "BEGIN ISOLATION LEVEL SERIALIZABLE").await;
        assert_eq!(
            scalar(&victim.client, "SELECT sum(n)::bigint FROM skew").await,
            0
        );
        assert_eq!(
            scalar(&other.client, "SELECT sum(n)::bigint FROM skew").await,
            0
        );
        commands(
            &victim.client,
            "INSERT INTO audit VALUES('victim'); UPDATE skew SET n=1 WHERE id=2",
        )
        .await;
        commands(&other.client, "UPDATE skew SET n=1 WHERE id=1; COMMIT").await;
        waiting = Some(tokio::spawn(async move {
            other.close().await;
        }));
    } else if mode == "deadlock" {
        commands(&victim.client, "BEGIN; SET LOCAL deadlock_timeout='50ms'; SELECT pg_advisory_xact_lock(111); INSERT INTO audit VALUES('victim'); INSERT INTO dead VALUES(1)").await;
        commands(
            &other.client,
            "BEGIN; SET LOCAL deadlock_timeout='10s'; SELECT pg_advisory_xact_lock(222)",
        )
        .await;
        let other_pid = other.pid;
        // The conflicting statement is in progress before COMMIT starts its deferred trigger.
        waiting = Some(tokio::spawn(async move {
            commands(&other.client, "SELECT pg_advisory_xact_lock(111)").await;
            commands(&other.client, "ROLLBACK").await;
            other.close().await;
        }));
        tokio::time::timeout(Duration::from_secs(3), async {
            loop {
                let sql=format!("SELECT count(*) FROM pg_stat_activity WHERE pid={other_pid} AND wait_event='advisory'");
                if scalar(&observer.client,&sql).await == 1 { break; }
                tokio::time::sleep(Duration::from_millis(5)).await;
            }
        }).await.unwrap();
    } else {
        panic!("unknown case");
    }
    // No retry. Instrument the only COMMIT in the victim's path.
    let error = victim.client.batch_execute("COMMIT").await.unwrap_err();
    let db = error.as_db_error().unwrap();
    let expected = match mode {
        "deferred" => "23503",
        "serialization" => "40001",
        "unclassified" => "40003",
        _ => "40P01",
    };
    assert_eq!(db.code().code(), expected);
    let category = classification(&error);
    assert_eq!(
        category,
        if mode == "unclassified" {
            "ambiguous"
        } else {
            "rejected"
        }
    );
    let sqlstate = db.code().code().to_owned();
    let severity = db.severity().to_owned();
    // The backend must have ended its transaction, not merely hidden uncommitted rows.
    tokio::time::timeout(Duration::from_secs(2), async {
        loop {
            let sql=format!("SELECT count(*) FROM pg_stat_activity WHERE pid={pid} AND state='idle' AND xact_start IS NULL");
            if scalar(&observer.client, &sql).await == 1 { break; }
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
    }).await.unwrap();
    // Independent observer before disposal: failure is not inferred from socket closure.
    let audit = scalar(
        &observer.client,
        "SELECT count(*) FROM audit WHERE id='victim'",
    )
    .await;
    let child = scalar(&observer.client, "SELECT count(*) FROM child").await;
    let dead = scalar(&observer.client, "SELECT count(*) FROM dead").await;
    let victim_row = scalar(&observer.client, "SELECT n::bigint FROM skew WHERE id=2").await;
    assert_eq!((audit, child, dead, victim_row), (0, 0, 0, 0));
    victim.close().await;
    if let Some(waiting) = waiting {
        waiting.await.unwrap();
    }
    // Even a definitive rejection retires rather than assuming ReadyForQuery.
    let fresh = Connection::open(url).await;
    assert_ne!(pid, fresh.pid);
    assert_eq!(scalar(&fresh.client, "SELECT 1::bigint").await, 1);
    let replacement = fresh.pid;
    fresh.close().await;
    println!(
        "{}",
        json!({"case":mode,"category":category,"sqlstate":sqlstate,"severity":severity,"victim_pid":pid,"replacement_pid":replacement,"backend_idle_without_transaction":true,"observed_before_retirement":{"audit":audit,"child":child,"dead":dead,"victim_row":victim_row}})
    );
    observer.close().await;
}
#[tokio::main(flavor = "current_thread")]
async fn main() {
    let url = std::env::var("RNX_COMMIT_URL").unwrap();
    let mode = std::env::args().nth(1).unwrap();
    tokio::time::timeout(Duration::from_secs(20), case(&url, &mode))
        .await
        .unwrap();
}
