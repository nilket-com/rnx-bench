use std::{cell::RefCell,time::Instant};
thread_local! {static DATA:RefCell<Vec<(&'static str,f64)>>=const{RefCell::new(Vec::new())};}
pub fn measure<T>(name:&'static str,f:impl FnOnce()->T)->T {let t=Instant::now();let result=f();DATA.with(|d|d.borrow_mut().push((name,t.elapsed().as_secs_f64()*1000.0)));result}
pub fn emit(){DATA.with(|d|eprintln!("PROFILE {}",serde_json::to_string(&*d.borrow()).unwrap()));}
pub fn record(name:&'static str,t:Instant){DATA.with(|d|d.borrow_mut().push((name,t.elapsed().as_secs_f64()*1000.0)));}
