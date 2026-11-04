//! Disposable codegen experiment. Not the production native loader or audit.
mod jit;
use jit::Kernel;
use polars_core::prelude::*;
use serde_json::json;
use std::{
	alloc::{GlobalAlloc, Layout, System},
	hint::black_box,
	path::Path,
	sync::atomic::{AtomicBool, AtomicU64, Ordering},
	time::Instant,
};
static TRACK: AtomicBool = AtomicBool::new(false);
static ALLOC: AtomicU64 = AtomicU64::new(0);
static REALLOC: AtomicU64 = AtomicU64::new(0);
static BYTES: AtomicU64 = AtomicU64::new(0);
struct Alloc;
unsafe impl GlobalAlloc for Alloc {
	unsafe fn alloc(&self, l: Layout) -> *mut u8 {
		if TRACK.load(Ordering::Relaxed) {
			ALLOC.fetch_add(1, Ordering::Relaxed);
			BYTES.fetch_add(l.size() as u64, Ordering::Relaxed);
		}
		System.alloc(l)
	}
	unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
		System.dealloc(p, l)
	}
	unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
		if TRACK.load(Ordering::Relaxed) {
			REALLOC.fetch_add(1, Ordering::Relaxed);
			BYTES.fetch_add(n as u64, Ordering::Relaxed);
		}
		System.realloc(p, l, n)
	}
}
#[global_allocator]
static ALLOCATOR: Alloc = Alloc;
fn reset_alloc() {
	ALLOC.store(0, Ordering::Relaxed);
	REALLOC.store(0, Ordering::Relaxed);
	BYTES.store(0, Ordering::Relaxed);
}
fn counters() -> serde_json::Value {
	json!({"alloc":ALLOC.load(Ordering::Relaxed),"realloc":REALLOC.load(Ordering::Relaxed),"requested_bytes":BYTES.load(Ordering::Relaxed)})
}

extern "C" {
	fn step_cycles_open() -> i32;
	fn step_begin(fd: i32);
	fn step_end(fd: i32, out: *mut u64);
	fn step_close(fd: i32);
}
#[inline(never)]
fn rust_i64(op: &str, x: &[i64], y: &[i64], out: &mut [i64]) -> usize {
	assert_eq!(x.len(), y.len());
	assert_eq!(x.len(), out.len());
	match op {
		"wrapadd" => {
			for (i, v) in out.iter_mut().enumerate() {
				*v = x[i].wrapping_add(1);
			}
		}
		"i64add" => {
			for (i, v) in out.iter_mut().enumerate() {
				if let Some(a) = x[i].checked_add(1) {
					*v = a
				} else {
					return i;
				}
			}
		}
		"axpy" => {
			for (i, v) in out.iter_mut().enumerate() {
				if let Some(a) = x[i].checked_mul(2).and_then(|a| a.checked_add(y[i])) {
					*v = a
				} else {
					return i;
				}
			}
		}
		_ => panic!("op"),
	}
	x.len()
}
#[inline(never)]
fn rust_f64(x: &[f64], out: &mut [f64]) {
	assert_eq!(x.len(), out.len());
	for (i, v) in out.iter_mut().enumerate() {
		*v = x[i] + 1.0;
	}
}
#[inline(never)]
fn rust_bool(x: &[u8], out: &mut [u8]) {
	assert_eq!(x.len(), out.len());
	for (i, v) in out.iter_mut().enumerate() {
		*v = !x[i];
	}
}
fn self_test() {
	for lanes in [1, 2] {
		for op in ["i64add", "wrapadd", "axpy"] {
			let k = Kernel::compile(op, lanes, None).unwrap();
			for n in [0, 1, 2, 3, 15, 16, 17, 257] {
				let mut x: Vec<_> = (0..n).map(|i| i as i64 - 17).collect();
				let mut y = vec![13; n];
				for fault in 0..=n {
					for val in [i64::MIN, i64::MAX, i64::MIN / 2 - 1, i64::MAX / 2 + 1, 0] {
						if fault < n {
							x[fault] = val;
							y[fault] = if val == 0 { i64::MAX } else { 13 };
						}
						let mut expected = vec![0x5511; n];
						let mut guarded = vec![0x5511; n + 2];
						let actual = &mut guarded[1..n + 1];
						let e = rust_i64(op, &x, &y, &mut expected);
						let a = k.i64(&x, &y, actual);
						assert_eq!(a, e, "{op}/{lanes}/n{n}/row{fault}/{val}");
						// Vector fault replays from its start and must return the first bad row.
						assert_eq!(&actual[..a], &expected[..e]);
						if a < n {
							assert_eq!(actual[a], 0x5511);
						}
						assert_eq!(guarded[0], 0x5511);
						assert_eq!(guarded[n + 1], 0x5511);
						if fault < n {
							x[fault] = fault as i64 - 17;
							y[fault] = 13;
						}
					}
				}
			}
		}
		let k = Kernel::compile("f64add", lanes, None).unwrap();
		let values = [
			0.0,
			-0.0,
			f64::INFINITY,
			f64::NEG_INFINITY,
			f64::NAN,
			1.5,
			-1.5,
			1e100,
		];
		for n in 0..=values.len() {
			let mut guarded = vec![91.25; n + 2];
			let out = &mut guarded[1..n + 1];
			assert_eq!(k.f64(&values[..n], out), n);
			for (i, v) in out.iter().enumerate() {
				let e = values[i] + 1.0;
				if e.is_nan() {
					assert!(v.is_nan())
				} else {
					assert_eq!(v.to_bits(), e.to_bits());
				}
			}
			assert_eq!(guarded[0], 91.25);
			assert_eq!(guarded[n + 1], 91.25);
		}
		let k = Kernel::compile("boolnot", lanes, None).unwrap();
		for n in [0, 1, 2, 15, 16, 17, 257] {
			let x: Vec<_> = (0..n).map(|i| i as u8).collect();
			let mut guarded = vec![0x5a; n + 2];
			let o = &mut guarded[1..n + 1];
			assert_eq!(k.packed(&x, o), n);
			for (i, v) in o.iter().enumerate() {
				assert_eq!(*v, !x[i]);
			}
			assert_eq!(guarded[0], 0x5a);
			assert_eq!(guarded[n + 1], 0x5a);
		}
	}
	println!(
		"{}",
		json!({"status":"PASS","scope":"lanes1/2; empty, tail, overflow at every row, MIN/MAX, scalar replay position, IEEE specials and packed Bool"})
	);
}
fn main() {
	let a: Vec<_> = std::env::args().collect();
	if a.len() == 2 && a[1] == "self-test" {
		self_test();
		return;
	}
	assert!(a.len() == 7, "BACKEND OP ROWS LANES REPEATS ARTIFACT_DIR|-");
	let backend = &a[1];
	let op = &a[2];
	let n: usize = a[3].parse().unwrap();
	let lanes = a[4].parse().unwrap();
	let repeat: usize = a[5].parse().unwrap();
	let artifact = (a[6] != "-").then(|| Path::new(&a[6]));
	let build = Instant::now();
	let kernel = if backend == "jit" {
		Some(Kernel::compile(op, lanes, artifact).unwrap())
	} else {
		None
	};
	let compile_ns = build.elapsed().as_nanos();
	let fd = unsafe { step_cycles_open() };
	let mut pmu = [0u64; 3];
	let mut checksum = 0u64;
	let measured_ns;
	let warm_alloc;
	match op.as_str() {
		"i64add" | "wrapadd" | "axpy" => {
			let x: Vec<i64> = (0..n).map(|i| (i % 1009) as i64 - 500).collect();
			let y: Vec<i64> = (0..n).map(|i| (i % 997) as i64 - 300).collect();
			let mut output = vec![0; n];
			let px = Int64Chunked::from_slice("x".into(), &x);
			let py = Int64Chunked::from_slice("y".into(), &y);
			let mut po = None;
			let mut run = || match backend.as_str() {
				"jit" => assert_eq!(
					kernel.as_ref().unwrap().i64(
						black_box(&x),
						black_box(&y),
						black_box(&mut output)
					),
					n
				),
				"rust" => assert_eq!(
					rust_i64(op, black_box(&x), black_box(&y), black_box(&mut output)),
					n
				),
				"polars" => {
					po = Some(if op == "axpy" {
						&(&px * 2i64) + &py
					} else {
						&px + 1i64
					});
					black_box(&po);
				}
				_ => panic!("backend"),
			};
			run();
			reset_alloc();
			TRACK.store(true, Ordering::Relaxed);
			run();
			TRACK.store(false, Ordering::Relaxed);
			warm_alloc = counters();
			let start = Instant::now();
			unsafe { step_begin(fd) };
			for _ in 0..repeat {
				run();
			}
			unsafe { step_end(fd, pmu.as_mut_ptr()) };
			measured_ns = start.elapsed().as_nanos();
			for i in 0..n {
				let v = if let Some(p) = &po {
					p.get(i).unwrap()
				} else {
					output[i]
				};
				let expected = if op == "axpy" {
					x[i] * 2 + y[i]
				} else {
					x[i] + 1
				};
				assert_eq!(v, expected);
				checksum = checksum.wrapping_mul(31).wrapping_add(v as u64);
			}
		}
		"f64add" => {
			let x: Vec<f64> = (0..n).map(|i| ((i % 1009) as f64 - 500.0) * 0.25).collect();
			let mut output = vec![0.0; n];
			let px = Float64Chunked::from_slice("x".into(), &x);
			let mut po = None;
			let mut run = || match backend.as_str() {
				"jit" => assert_eq!(
					kernel
						.as_ref()
						.unwrap()
						.f64(black_box(&x), black_box(&mut output)),
					n
				),
				"rust" => rust_f64(black_box(&x), black_box(&mut output)),
				"polars" => {
					po = Some(&px + 1.0);
					black_box(&po);
				}
				_ => panic!("backend"),
			};
			run();
			reset_alloc();
			TRACK.store(true, Ordering::Relaxed);
			run();
			TRACK.store(false, Ordering::Relaxed);
			warm_alloc = counters();
			let start = Instant::now();
			unsafe { step_begin(fd) };
			for _ in 0..repeat {
				run();
			}
			unsafe { step_end(fd, pmu.as_mut_ptr()) };
			measured_ns = start.elapsed().as_nanos();
			for i in 0..n {
				let v = if let Some(p) = &po {
					p.get(i).unwrap()
				} else {
					output[i]
				};
				assert_eq!(v, x[i] + 1.0);
				checksum = checksum.wrapping_mul(31).wrapping_add(v.to_bits());
			}
		}
		"boolnot" => {
			let bytes = n.div_ceil(8);
			let x: Vec<u8> = (0..bytes).map(|i| (i % 251) as u8).collect();
			let mut output = vec![0; bytes];
			let px = BooleanChunked::from_iter_values(
				"x".into(),
				(0..n).map(|i| ((x[i / 8] >> (i % 8)) & 1) != 0),
			);
			let mut po = None;
			let mut run = || match backend.as_str() {
				"jit" => assert_eq!(
					kernel
						.as_ref()
						.unwrap()
						.packed(black_box(&x), black_box(&mut output)),
					bytes
				),
				"rust" => rust_bool(black_box(&x), black_box(&mut output)),
				"polars" => {
					po = Some(!&px);
					black_box(&po);
				}
				_ => panic!("backend"),
			};
			run();
			reset_alloc();
			TRACK.store(true, Ordering::Relaxed);
			run();
			TRACK.store(false, Ordering::Relaxed);
			warm_alloc = counters();
			let start = Instant::now();
			unsafe { step_begin(fd) };
			for _ in 0..repeat {
				run();
			}
			unsafe { step_end(fd, pmu.as_mut_ptr()) };
			measured_ns = start.elapsed().as_nanos();
			for i in 0..n {
				let v = if let Some(p) = &po {
					p.get(i).unwrap()
				} else {
					((output[i / 8] >> (i % 8)) & 1) != 0
				};
				assert_eq!(v, ((x[i / 8] >> (i % 8)) & 1) == 0);
				checksum = checksum.wrapping_mul(31).wrapping_add(u64::from(v));
			}
		}
		_ => panic!("op"),
	}
	unsafe { step_close(fd) };
	println!(
		"{}",
		json!({"status":"PASS","backend":backend,"op":op,"rows":n,"lanes":lanes,"repeat":repeat,"checksum":checksum,"compile_ns":compile_ns,"warm_alloc":warm_alloc,"measured_ns":measured_ns,"cycles":if fd>=0&&pmu[1]==pmu[2]&&pmu[1]>0{Some(pmu[0])}else{None},"pmu_enabled":pmu[1],"pmu_running":pmu[2],"jit_bytes":kernel.as_ref().map(|k|k.bytes),"jit_address":kernel.as_ref().map(|k|k.address),"scope":"nonnull borrowed numeric slices/byte-aligned packed Bool; preallocated Rust/JIT output; eager Polars allocates output; checked arithmetic except wrapadd and Polars wrapping"})
	);
}
