use rune::{Context, Diagnostics, Source, Sources, Vm};
use std::time::Instant;
fn go() -> Result<(), String> {
 let args: Vec<_> = std::env::args().skip(1).collect();
 let mode = args.first().map(String::as_str).unwrap_or("floor");
 if mode == "registration" { registration();return Ok(()); }
 if mode == "floor" { return Ok(()); }
 if mode == "first-use" { return first_use(&args); }
 if mode == "empty-context" { std::hint::black_box(Context::new()); return Ok(()); }
 if mode == "contexts" {
  let stdio=args[1]=="true";let repeats=args[2].parse::<usize>().unwrap();
  for i in 0..repeats {
   let t=Instant::now();let context=Context::with_config(stdio).map_err(|e|format!("context: {e:?}"))?;
   let construct=t.elapsed().as_nanos();let t=Instant::now();drop(context);let drop=t.elapsed().as_nanos();
   eprintln!("CTX {i} {construct} {drop}");
  }
  return Ok(());
 }

 let began = Instant::now();
 let context = if mode == "context" || mode == "runtime" { Context::with_default_modules() } else { Context::with_config(true) }.map_err(|e|format!("context: {e:?}"))?;
 let constructed = began.elapsed().as_nanos();
 if mode == "context" { std::hint::black_box(context); return Ok(()); }
 let runtime = shared(context.runtime().map_err(|e|format!("runtime: {e:?}"))?);
 let runtime_ns = began.elapsed().as_nanos();
 if mode == "runtime" { std::hint::black_box(runtime); return Ok(()); }
 let source = std::fs::read_to_string(&args[1]).map_err(|e|format!("read: {e:?}"))?;
 let mut sources = Sources::new();
 sources.insert(Source::memory(&source).map_err(|e|format!("source: {e:?}"))?).map_err(|e|format!("insert: {e:?}"))?;
 let mut diagnostics=Diagnostics::new();
 let unit = rune::prepare(&mut sources).with_context(&context).with_diagnostics(&mut diagnostics).build().map_err(|e|format!("compile: {e:?}; diagnostics={diagnostics:?}"))?;
 let compiled = began.elapsed().as_nanos();
 if mode == "compile" { std::hint::black_box(unit); return Ok(()); }
 let unit=shared(unit);
 let repeats=if mode == "reuse" {20} else {1};
 let mut total_ns=0u128;
 let budget=args.get(2).map(|s|s.parse::<usize>().unwrap()).unwrap_or(1_000_000_000);
 let mut reused=Vm::new(runtime.clone(),unit.clone());
 for _ in 0..repeats {
  let mut fresh=Vm::new(runtime.clone(),unit.clone());
  let vm=if mode=="reuse" { &mut reused } else { &mut fresh };
  let t=Instant::now();
  let value = if mode == "async" {
   futures::executor::block_on(rune::runtime::budget::with(budget, async {
    async_result(vm.execute(["main"], ((),)).map_err(|e|format!("execute: {e:?}"))?.async_complete().await).map_err(|e|format!("vm: {e:?}"))
   }))
  } else {
   rune::runtime::budget::with(budget, || vm.call(["main"], ((),))).call().map_err(|e|format!("vm: {e:?}"))
  }?;
  total_ns+=t.elapsed().as_nanos();
  std::hint::black_box(value);
 }
 if mode=="phases" || mode=="reuse" { eprintln!("PHASES {constructed} {runtime_ns} {compiled} {total_ns} {repeats}"); }
 Ok(())
}
// rnx 0179: one cold full-capability first use. Fresh Context::with_config(stdio), compile, run the async main to
// COMPLETION, require the i64 result 42, then print the fixed marker. Anything else is a nonzero exit.
fn first_use(args: &[String]) -> Result<(), String> {
 if args.len() != 3 { return Err(format!("first-use: expected <true|false> <script>, got {} arguments", args.len() - 1)); }
 let stdio = match args[1].as_str() { "true" => true, "false" => false, other => return Err(format!("first-use: stdio must be true or false, got {other:?}")) };
 let context = Context::with_config(stdio).map_err(|e|format!("context: {e:?}"))?;
 let runtime = shared(context.runtime().map_err(|e|format!("runtime: {e:?}"))?);
 let source = std::fs::read_to_string(&args[2]).map_err(|e|format!("read: {e:?}"))?;
 let mut sources = Sources::new();
 sources.insert(Source::memory(&source).map_err(|e|format!("source: {e:?}"))?).map_err(|e|format!("insert: {e:?}"))?;
 let mut diagnostics=Diagnostics::new();
 let unit = shared(rune::prepare(&mut sources).with_context(&context).with_diagnostics(&mut diagnostics).build().map_err(|e|format!("compile: {e:?}; diagnostics={diagnostics:?}"))?);
 let mut vm=Vm::new(runtime,unit);
 let value = futures::executor::block_on(rune::runtime::budget::with(1_000_000_000, async {
  async_result(vm.execute(["main"], ((),)).map_err(|e|format!("execute: {e:?}"))?.async_complete().await).map_err(|e|format!("vm: {e:?}"))
 }))?;
 let answer: i64 = rune::from_value(value).map_err(|e|format!("result: {e:?}"))?;
 if answer != 42 { return Err(format!("first-use: result {answer}, expected 42")); }
 println!("FIRST-USE {answer}");
 Ok(())
}
fn main() {
 #[cfg(feature="counter")] { eprintln!("READY");let mut line=String::new();std::io::stdin().read_line(&mut line).unwrap();assert_eq!(line.trim(),"go"); }
 alloc_track::reset();let result=go();let a=alloc_track::snapshot();
 #[cfg(feature="allocation")] eprintln!("ALLOC {a:?}");
 #[cfg(not(feature="allocation"))] std::hint::black_box(a);
 #[cfg(feature="counter")] { eprintln!("DONE");let mut line=String::new();std::io::stdin().read_line(&mut line).unwrap();assert_eq!(line.trim(),"stop"); }
 if let Err(e)=result { eprintln!("{e}");std::process::exit(1); }
}
