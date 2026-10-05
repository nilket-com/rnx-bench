mod alloc_track { include!("../../alloc_track.rs"); }
use rune::{Context, Diagnostics, Source, Sources, Vm};
use rune::registration_profile as profile;
use rune::sync::Arc;
use serde_json::json;
use std::time::Instant;
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let enabled = args[0] == "enabled";
    let stdio = args[1] == "true";
    let repeats: usize = args[2].parse().unwrap();
    for i in 0..repeats {
        profile::reset(enabled, if cfg!(feature="allocation") { Some(alloc_track::snapshot) } else { None });
        alloc_track::reset();
        let baseline = alloc_track::snapshot();
        let t=Instant::now();
        let context=Context::with_config(stdio).unwrap();
        let construct=t.elapsed().as_nanos();
        let allocated=alloc_track::snapshot();
        let inventory=if i==0 {Some(context.registration_inventory())} else {None};
        if let Some(file)=args.get(3) {
            let source=std::fs::read_to_string(file).unwrap();
            let mut sources=Sources::new();sources.insert(Source::memory(source).unwrap()).unwrap();
            let mut diagnostics=Diagnostics::new();
            let unit=rune::prepare(&mut sources).with_context(&context).with_diagnostics(&mut diagnostics).build().unwrap();
            let mut vm=Vm::new(Arc::try_new(context.runtime().unwrap()).unwrap(),Arc::try_new(unit).unwrap());
            let value=rune::runtime::budget::with(1_000_000_000,||vm.call(["main"],((),))).call().unwrap();
            std::hint::black_box(value);
        }
        let t=Instant::now();drop(context);let drop=t.elapsed().as_nanos();
        let rows=profile::rows().iter().map(|r|json!({"module":r.module,"phase":r.phase,"ns":r.ns,"events":r.calls,"allocation":r.allocation})).collect::<Vec<_>>();
        eprintln!("{}",json!({"iteration":i,"enabled":enabled,"stdio":stdio,"construct_ns":construct,"drop_ns":drop,"baseline_allocation":baseline,"after_construct_allocation":allocated,"inventory":inventory,"rows":rows}));
    }
}
