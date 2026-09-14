mod transport;
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Write},
    time::Duration,
};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args[1] == "sleep" {
        std::fs::write(&args[2], std::process::id().to_string())?;
        std::thread::sleep(Duration::from_secs(3));
        return Ok(());
    }
    let (read, mut write) =
        transport::open(args[1].parse()?, args[2].parse()?, args[3] == "isolated")?;
    writeln!(
        write,
        "{}",
        json!({"type":"ready", "isolated":args[3]=="isolated"})
    )?;
    write.flush()?;
    let mut read = BufReader::new(read);
    let mut line = String::new();
    loop {
        line.clear();
        if read.read_line(&mut line)? == 0 {
            break;
        }
        let v: Value = serde_json::from_str(&line)?;
        if v["op"] == "isolation" {
            // Real rnx process::run creates the sleeping descendant. The helper
            // itself deliberately inherits controls if the negative control did.
            let source = format!(
                "process::run({}, [\"sleep\", {}], #{{}})?",
                serde_json::to_string(&std::env::current_exe()?.to_string_lossy())?,
                v["ready_file"]
            );
            let child = std::process::Command::new(v["rnx"].as_str().unwrap())
                .args(["eval", &source])
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()?;
            writeln!(write, "{}", json!({"type":"spawned", "pid":child.id()}))?;
            write.flush()?;
            // Parent waits for the grandchild's ready file before asking exit.
            line.clear();
            read.read_line(&mut line)?;
            return Ok(());
        }
        let id = v["id"].as_u64().unwrap();
        let nonce = v["nonce"].as_str().unwrap();
        if v["op"] == "shutdown" {
            return Ok(());
        }
        if v["op"] == "late" {
            std::thread::spawn(|| {
                std::thread::sleep(Duration::from_millis(250));
                let mut out = std::io::stdout().lock();
                out.write_all(b"OLD-WRITER").unwrap();
                out.flush().unwrap();
            });
        }
        if v["op"] == "hold" {
            std::thread::sleep(Duration::from_millis(500));
        }
        if v["op"] == "emit" {
            let a = std::thread::spawn(|| {
                let mut out = std::io::stdout().lock();
                for _ in 0..400 {
                    out.write_all(&[0xff; 8192]).unwrap();
                }
                out.write_all(b"no newline\0\x1eRNX-WORKER-1:1:stdout:old\x1f")
                    .unwrap();
            });
            let b = std::thread::spawn(|| {
                let mut err = std::io::stderr().lock();
                for _ in 0..400 {
                    err.write_all(&[0xfe; 8192]).unwrap();
                }
                err.write_all(b"stderr tail").unwrap();
            });
            a.join().unwrap();
            b.join().unwrap();
        }
        for stream in ["stdout", "stderr"] {
            let mut target: Box<dyn Write> = if stream == "stdout" {
                Box::new(std::io::stdout().lock())
            } else {
                Box::new(std::io::stderr().lock())
            };
            target.flush()?;
            // Force one-byte writes: receiver must not depend on write boundaries.
            for byte in format!("\x1eRNX-WORKER-1:{id}:{stream}:{nonce}\x1f").bytes() {
                target.write_all(&[byte])?;
            }
            target.flush()?;
        }
        writeln!(write, "{}", json!({"type":"settled", "id":id}))?;
        write.flush()?;
        line.clear();
        read.read_line(&mut line)?;
        assert_eq!(
            serde_json::from_str::<Value>(&line)?,
            json!({"op":"ack", "id":id})
        );
    }
    Ok(())
}
