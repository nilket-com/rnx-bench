mod alloc_track { include!("../../alloc_track.rs"); }
include!("registration.rs");
use rune::sync::Arc;
fn shared<T>(value: T) -> Arc<T> { Arc::try_new(value).unwrap() }
fn async_result(v: Result<rune::runtime::Value,rune::runtime::VmError>) -> Result<rune::runtime::Value,rune::runtime::VmError> { v }
include!("../../harness.rs");
