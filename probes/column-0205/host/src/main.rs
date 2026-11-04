use rnx::column::{
	Chunk, ColumnSlice, ColumnType, ColumnValues, ExecutorLimits, Input, Kernel, Limits, Mode,
	Options,
};
use std::{hint::black_box, time::Instant};
unsafe extern "C" {
	fn step_cycles_open() -> i32;
	fn step_begin(fd: i32);
	fn step_end(fd: i32, out: *mut u64);
	fn step_close(fd: i32);
}
fn main() {
	let args: Vec<_> = std::env::args().collect();
	assert_eq!(args.len(), 3, "MODE ROWS");
	let mode = match args[1].as_str() {
		"auto" => Mode::Auto,
		"portable" => Mode::Portable,
		"reference" => Mode::Reference,
		_ => panic!("mode"),
	};
	let n: usize = args[2].parse().unwrap();
	assert!(n > 0);
	let data: Vec<_> = (0..n).map(|i| (i % 1009) as i64 - 500).collect();
	let chunks = [Chunk {
		values: ColumnSlice::I64(&data),
		validity: None,
	}];
	let inputs = [Input {
		ty: ColumnType::I64,
		chunks: &chunks,
	}];
	let prep_start = Instant::now();
	let mut kernel = Kernel::prepare(
		"pub fn map(x) { x + 1 }",
		"map",
		&[ColumnType::I64],
		ColumnType::I64,
		Limits {
			bytes: isize::MAX as usize,
			..Limits::default()
		},
	)
	.unwrap();
	let prepare_ns = prep_start.elapsed().as_nanos();
	let charge = kernel.row_charge().unwrap();
	let work = charge.checked_mul(n).unwrap();
	let mut samples = Vec::new();
	for call in 0..2 {
		let fd = unsafe { step_cycles_open() };
		let mut pmu = [0u64; 3];
		let start = Instant::now();
		unsafe { step_begin(fd) };
		let output = kernel
			.map(
				black_box(&inputs),
				Options {
					work,
					mode,
					executor_limits: ExecutorLimits::default(),
					adapter_bytes: 0,
				},
				|| false,
			)
			.unwrap();
		unsafe { step_end(fd, pmu.as_mut_ptr()) };
		let elapsed_ns = start.elapsed().as_nanos();
		unsafe { step_close(fd) };
		assert_eq!(output.remaining_work, 0);
		assert!(output.validity.is_none());
		assert_eq!(output.len, n);
		let ColumnValues::I64(values) = &output.values else {
			panic!("output type")
		};
		assert_eq!(values.len(), n);
		let mut checksum = 0u64;
		for (got, input) in values.iter().zip(&data) {
			assert_eq!(*got, input + 1);
			checksum = checksum.wrapping_mul(31).wrapping_add(*got as u64);
		}
		let observed = kernel.last_path();
		assert!(observed.completed);
		assert_eq!(observed.valid_rows, n);
		assert_eq!(observed.replays, 0);
		assert_eq!(observed.attempts, usize::from(mode != Mode::Reference));
		samples.push(format!("{{\"call\":{call},\"elapsed_ns\":{elapsed_ns},\"cycles_raw\":{},\"pmu_enabled\":{},\"pmu_running\":{},\"path\":\"{:?}\",\"output_capacity_bytes\":{},\"checksum\":{checksum}}}",pmu[0],pmu[1],pmu[2],observed.path,values.capacity()*8));
	}
	println!(
		"{{\"status\":\"PASS\",\"scope\":\"Rust host map: output allocation included; no Arrow wrapper; input and full validation excluded\",\"mode\":\"{}\",\"rows\":{n},\"prepare_ns\":{prepare_ns},\"row_charge\":{charge},\"retained_bytes\":{},\"samples\":[{}]}}",
		args[1],
		kernel.retained_bytes(),
		samples.join(",")
	);
}
