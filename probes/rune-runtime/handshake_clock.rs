//! Diagnostic copy of rustc-42 clock: only the pre-clock READY/GO boundary is added.
use std::io::{Read, Write};
use std::process::Command;
use std::time::Instant;
#[repr(C)]
struct Timespec { sec: i64, nsec: i64 }
unsafe extern "C" { fn clock_gettime(clock: i32, ts: *mut Timespec) -> i32; }
fn monotonic_ns() -> i128 {
    let mut ts = Timespec { sec: 0, nsec: 0 };
    assert_eq!(unsafe { clock_gettime(1, &mut ts) }, 0);
    i128::from(ts.sec) * 1_000_000_000 + i128::from(ts.nsec)
}
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let count: usize = args[0].parse().expect("command count");
    assert!((1..=2).contains(&count));
    let mut commands = Vec::new();
    let mut at = 1;
    for _ in 0..count {
        let len: usize = args[at].parse().expect("argument count");
        at += 1;
        assert!(len > 0);
        let argv = &args[at..at + len];
        let mut command = Command::new(&argv[0]);
        command.args(&argv[1..]);
        commands.push(command);
        at += len;
    }
    assert_eq!(at, args.len());
    let mut outputs = Vec::with_capacity(count);
    println!("READY");
    std::io::stdout().flush().unwrap();
    let mut go = [0];
    std::io::stdin().read_exact(&mut go).unwrap();
    assert_eq!(go, [b'G']);
    let start = monotonic_ns();
    let began = Instant::now();
    for command in &mut commands {
        outputs.push(command.output().expect("spawn command"));
    }
    let elapsed = began.elapsed().as_nanos();
    let end = monotonic_ns();
    println!("{elapsed}");
    for output in outputs {
        println!("{}", output.status.code().expect("command terminated by signal"));
        for bytes in [output.stdout, output.stderr] {
            let hex: String = bytes.iter().map(|b| format!("{b:02x}")).collect();
            println!("{hex}");
        }
    }
    eprintln!("STAMP {start} {end}");
}
