//! Record 0163: a retained decomposition of setup, release, pinned externally by taskset.
use rnx::{Extensions, server::Program};
use std::time::Instant;
fn median(mut values: Vec<f64>) -> f64 {
	values.sort_by(f64::total_cmp);
	(values[149] + values[150]) / 2.
}
fn sample(mut f: impl FnMut()) -> f64 {
	for _ in 0..20 {
		f();
	}
	let mut values = Vec::new();
	for _ in 0..300 {
		let started = Instant::now();
		f();
		values.push(started.elapsed().as_secs_f64() * 1e6);
	}
	median(values)
}
fn main() {
	let p =
		Program::compile_source("<decomposition>", "pub fn main() {}", Extensions::none()).unwrap();
	let defaults = sample(|| {
		drop(rnx::rune::Context::with_default_modules().unwrap());
	});
	let context = rnx::rune::Context::with_default_modules().unwrap();
	let runtime = sample(|| {
		drop(context.runtime().unwrap());
	});
	let invocation = sample(|| {
		p.prepare_with(Extensions::none(), "main", vec![], 10000)
			.unwrap()
			.close()
			.unwrap();
	});
	let slot = sample(|| {
		drop(p.slot(Extensions::none()).unwrap());
	});
	println!(
		"{{\"samples\":300,\"warm\":20,\"defaults_build_drop_us\":{defaults},\"runtime_build_drop_us\":{runtime},\"prepare_close_us\":{invocation},\"slot_build_drop_us\":{slot}}}"
	);
}
