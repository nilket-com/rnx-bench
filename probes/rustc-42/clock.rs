//! Benchmark clock only. Driver startup is outside the measured interval.
use std::process::Command;
use std::time::Instant;

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
	let began = Instant::now();
	for command in &mut commands {
		outputs.push(command.output().expect("spawn command"));
	}
	let elapsed = began.elapsed().as_nanos();
	println!("{elapsed}");
	for output in outputs {
		println!("{}", output.status.code().expect("command terminated by signal"));
		for bytes in [output.stdout, output.stderr] {
			let hex: String = bytes.iter().map(|b| format!("{b:02x}")).collect();
			println!("{hex}");
		}
	}
}
