mod alloc_track { include!("../../alloc_track.rs"); }
include!("registration.rs");
use std::sync::Arc;
fn shared<T>(value: T) -> Arc<T> { Arc::new(value) }
fn async_result(v: rune::runtime::VmResult<rune::runtime::Value>) -> Result<rune::runtime::Value,rune::runtime::VmError> { v.into_result() }
include!("../../harness.rs");
