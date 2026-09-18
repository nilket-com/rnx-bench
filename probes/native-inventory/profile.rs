//! Probe-only clocks, accumulated in memory and emitted once before exec.
use std::{cell::RefCell,collections::BTreeMap,time::Instant};
#[derive(Default,serde::Serialize)]
struct Data { ns:BTreeMap<String,u64>, calls:BTreeMap<String,u64> }
thread_local! { static DATA:RefCell<Data>=RefCell::new(Data::default()); static OWNER:RefCell<Option<String>>=const {RefCell::new(None)}; }
fn enabled()->bool { static ON:std::sync::OnceLock<bool>=std::sync::OnceLock::new(); *ON.get_or_init(||std::env::var_os("RNX_INVENTORY_CLOCKS").is_some()) }
pub fn start()->Option<Instant> {enabled().then(Instant::now)}
pub fn record(key:&str,t:Option<Instant>){if let Some(t)=t {add(key,t.elapsed().as_nanos() as u64)}}
fn add(key:&str,n:u64){DATA.with(|d|{let mut d=d.borrow_mut();*d.ns.entry(key.into()).or_default()+=n;*d.calls.entry(key.into()).or_default()+=1;})}
pub fn tree_record(phase:&str,t:Option<Instant>){if let Some(t)=t {OWNER.with(|o|{if let Some(root)=o.borrow().as_ref(){add(&format!("tree|{root}|{phase}"),t.elapsed().as_nanos() as u64)}})}}
pub struct Owner {previous:Option<String>,root:String,t:Option<Instant>}
pub fn owner(root:&std::path::Path)->Owner{let t=start();let root=root.to_string_lossy().into_owned();let previous=OWNER.with(|o|o.replace(Some(root.clone())));Owner{previous,root,t}}
impl Drop for Owner {fn drop(&mut self){record(&format!("tree|{}|total",self.root),self.t);OWNER.with(|o|o.replace(self.previous.take()));}}
pub struct Span{key:String,t:Option<Instant>}
pub fn span(key:String)->Span {Span{key,t:start()}}
impl Drop for Span {fn drop(&mut self){record(&self.key,self.t)}}
#[allow(dead_code)] // The private library target has no exec boundary.
pub fn emit(){if enabled(){DATA.with(|d|eprintln!("INVENTORY_PROFILE {}",serde_json::to_string(&*d.borrow()).unwrap()));}}
