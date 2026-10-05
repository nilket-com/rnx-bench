#[cfg(feature = "allocation")]
mod counted {
 use std::alloc::{GlobalAlloc,Layout,System};
 use std::sync::atomic::{AtomicUsize,Ordering::Relaxed};
 pub struct Alloc;
 static LIVE:AtomicUsize=AtomicUsize::new(0);
 static PEAK:AtomicUsize=AtomicUsize::new(0);
 static CALLS:AtomicUsize=AtomicUsize::new(0);
 static BYTES:AtomicUsize=AtomicUsize::new(0);
 fn added(n:usize) { let now=LIVE.fetch_add(n,Relaxed)+n;PEAK.fetch_max(now,Relaxed);CALLS.fetch_add(1,Relaxed);BYTES.fetch_add(n,Relaxed); }
 unsafe impl GlobalAlloc for Alloc {
  unsafe fn alloc(&self,l:Layout)->*mut u8 { let p=unsafe{System.alloc(l)};if !p.is_null(){added(l.size());}p }
  unsafe fn alloc_zeroed(&self,l:Layout)->*mut u8 { let p=unsafe{System.alloc_zeroed(l)};if !p.is_null(){added(l.size());}p }
  unsafe fn dealloc(&self,p:*mut u8,l:Layout) { LIVE.fetch_sub(l.size(),Relaxed);unsafe{System.dealloc(p,l)}; }
  unsafe fn realloc(&self,p:*mut u8,l:Layout,n:usize)->*mut u8 { let q=unsafe{System.realloc(p,l,n)};if !q.is_null(){LIVE.fetch_sub(l.size(),Relaxed);added(n);}q }
 }
 #[global_allocator]static A:Alloc=Alloc;
 pub fn reset() { CALLS.store(0,Relaxed);BYTES.store(0,Relaxed);PEAK.store(LIVE.load(Relaxed),Relaxed); }
 pub fn snapshot()->[usize;4] { [CALLS.load(Relaxed),BYTES.load(Relaxed),LIVE.load(Relaxed),PEAK.load(Relaxed)] }
}
#[cfg(feature = "allocation")]pub use counted::{reset,snapshot};
#[cfg(not(feature = "allocation"))]pub fn reset(){}
#[cfg(not(feature = "allocation"))]pub fn snapshot()->[usize;4]{[0;4]}
