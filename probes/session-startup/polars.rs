use rnx::rune;
fn log(s: &str) {
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(std::env::var("STARTUP_EVENTS").unwrap())
        .unwrap();
    writeln!(f, "{} {s}", std::process::id()).unwrap();
}
pub fn build(m: &mut rune::Module) -> Result<Vec<(String, &'static str)>, String> {
    let probe = std::env::var("RNX_INTERNAL_STARTUP_FD").ok();
    log(if probe.is_some() {
        "probe builder"
    } else {
        "session builder"
    });
    m.function("answer", || 73i64)
        .build()
        .map_err(|e| e.to_string())?;
    if let Some(raw) = probe {
        let fd = raw.parse::<i32>().unwrap();
        match std::env::var("STARTUP_MODE").unwrap_or_default().as_str() {
            "error" => return Err("probe builder error".into()),
            "panic" => panic!("probe builder panic"),
            "abort" => std::process::abort(),
            "block" => std::thread::sleep(std::time::Duration::from_secs(120)),
            "flood" => {
                use std::io::Write;
                let mut out = std::io::stdout().lock();
                loop {
                    out.write_all(&[b'x'; 8192]).unwrap();
                }
            }
            "spoof" => {
                print!("\0\0\0\x09\x01\x06\x01\0\0\0\x0242");
                std::process::exit(0)
            }
            "malformed" | "truncated" => {
                use std::io::Write;
                use std::os::fd::FromRawFd;
                let mut socket = std::mem::ManuallyDrop::new(unsafe {
                    std::os::unix::net::UnixStream::from_raw_fd(fd)
                });
                socket
                    .write_all(if std::env::var("STARTUP_MODE").unwrap() == "malformed" {
                        &[255, 255, 255, 255]
                    } else {
                        &[0, 0]
                    })
                    .unwrap();
                if std::env::var("STARTUP_MODE").unwrap() == "truncated" {
                    std::process::exit(0);
                }
            }
            "seal" => {
                let script = format!(
                    "import os;\ntry: os.fstat({fd})\nexcept OSError: raise SystemExit(0)\nraise SystemExit(91)"
                );
                assert!(
                    std::process::Command::new("/usr/bin/python3")
                        .arg("-c")
                        .arg(script)
                        .status()
                        .unwrap()
                        .success()
                );
                log("sealed descriptor");
            }
            _ => (),
        }
    }
    Ok(vec![])
}
