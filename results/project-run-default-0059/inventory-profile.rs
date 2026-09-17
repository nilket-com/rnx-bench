use std::{cell::RefCell,time::Instant};
thread_local!{static DATA:RefCell<Vec<(&'static str,f64)>>=const{RefCell::new(Vec::new())};}
pub fn record(n:&'static str,t:Instant){DATA.with(|d|d.borrow_mut().push((n,t.elapsed().as_secs_f64()*1000.0)));}
#[allow(dead_code)] pub fn emit(){DATA.with(|d|eprintln!("INVENTORY {}",serde_json::to_string(&*d.borrow()).unwrap()));}
