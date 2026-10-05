//! Diagnostic-only collector. Never enabled in primary engines.
#![allow(missing_docs)] // Scratch telemetry fields, not a production API.
use std::cell::RefCell;
use std::vec::Vec;
use std::time::Instant;
#[derive(Clone, Debug)]
pub struct Row {
    pub module: &'static str,
    pub phase: &'static str,
    pub ns: u128,
    pub calls: [u64; 3],
    pub allocation: Option<[u64; 5]>,
}
struct State {
    enabled: bool,
    module: &'static str,
    rows: Vec<Row>,
    hits: [u64; 3],
    allocation: Option<fn() -> [usize; 4]>,
}
std::thread_local! {
    static STATE: RefCell<State> = RefCell::new(State {
        enabled: false, module: "", rows: Vec::new(), hits: [0; 3], allocation: None,
    });
}
pub fn reset(enabled: bool, allocation: Option<fn() -> [usize; 4]>) {
    STATE.with(|state| {
        let mut s = state.borrow_mut();
        s.rows.clear();
        if s.rows.capacity() < 8192 { s.rows.reserve(8192); }
        s.enabled = enabled;
        s.module = "";
        s.hits = [0; 3];
        s.allocation = allocation;
    });
}
pub fn set_module(module: &'static str) { STATE.with(|s| s.borrow_mut().module = module); }
pub fn hit(index: usize) {
    STATE.with(|s| { let mut s=s.borrow_mut(); if s.enabled { s.hits[index] += 1; } });
}
pub struct Mark {
    start: Option<Instant>, module: &'static str, phase: &'static str,
    hits: [u64; 3], allocation: Option<[usize; 4]>,
}
pub fn mark(phase: &'static str) -> Mark {
    STATE.with(|s| {
        let s = s.borrow();
        Mark {
            start: s.enabled.then(Instant::now), module: s.module, phase,
            hits: s.hits, allocation: if s.enabled { s.allocation.map(|f| f()) } else { None },
        }
    })
}
impl Drop for Mark {
    fn drop(&mut self) {
        let Some(t)=self.start else { return; };
        let ns=t.elapsed().as_nanos();
        STATE.with(|s| {
            let mut s=s.borrow_mut();
            let hits=std::array::from_fn(|i|s.hits[i]-self.hits[i]);
            let allocation=self.allocation.map(|before| {
                let after=(s.allocation.unwrap())();
                [ (after[0]-before[0]) as u64, (after[1]-before[1]) as u64,
                  before[2] as u64, after[2] as u64, after[3] as u64 ]
            });
            assert!(s.rows.len()<s.rows.capacity(),"collector capacity exceeded");
            s.rows.push(Row {module:self.module,phase:self.phase,ns,calls:hits,allocation});
        });
    }
}
pub fn rows() -> Vec<Row> { STATE.with(|s|s.borrow().rows.clone()) }
