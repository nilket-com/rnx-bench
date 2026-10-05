//! Resident observer: an immutable command plan, fresh process and unchanged interval per entry.
use std::process::Command;
use std::time::Instant;
fn decode(s: &str) -> String {
    assert!(s.len() % 2 == 0);
    let bytes: Vec<_> = (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2], 16).unwrap()).collect();
    String::from_utf8(bytes).unwrap()
}
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    assert_eq!(args.len(), 1);
    let plan = std::fs::read_to_string(&args[0]).unwrap();
    let mut lines = plan.lines();
    let count: usize = lines.next().unwrap().parse().unwrap();
    assert!((1..=5000).contains(&count));
    let mut commands = Vec::with_capacity(count);
    for _ in 0..count {
        let n: usize = lines.next().unwrap().parse().unwrap();
        assert!((1..=64).contains(&n));
        let encoded: Vec<_> = (0..n).map(|_| lines.next().unwrap().to_owned()).collect();
        let argv: Vec<_> = encoded.iter().map(|s| decode(s)).collect();
        let mut cmd = Command::new(&argv[0]);
        cmd.args(&argv[1..]);
        commands.push((cmd, encoded));
    }
    assert!(lines.next().is_none());
    let mut records = Vec::with_capacity(count);
    for (mut cmd, encoded) in commands {
        let began = Instant::now();
        let output = cmd.output().expect("spawn target");
        let elapsed = began.elapsed().as_nanos();
        records.push((elapsed, output, encoded));
    }
    for (index, (elapsed, output, encoded)) in records.into_iter().enumerate() {
        println!("EXEC {index}");
        println!("{}", encoded.join(" "));
        println!("{elapsed}");
        println!("{}", output.status.code().expect("target terminated by signal"));
        for bytes in [output.stdout, output.stderr] {
            let hex: String = bytes.iter().map(|b| format!("{b:02x}")).collect();
            println!("{hex}");
        }
    }
}
