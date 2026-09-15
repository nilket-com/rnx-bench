//! Compile-only stubs for unchanged dependencies of the real runner.
//! No execution, whole-root Windows build, or runtime compatibility claimed.
#![allow(dead_code)]
#[path = "../../../../rnx/src/program.rs"]
mod program;
#[path = "../../../../rnx/src/runner.rs"]
mod runner;
#[path = "../../../../rnx/src/declared.rs"]
mod declared;
#[path = "../../../../rnx/src/method.rs"]
mod method;
mod host { pub fn running_a_script() {} }
mod session { pub fn position(_: &str, _: usize) -> (usize, usize, String) { unimplemented!() } }
mod presentation {
    pub fn error(_: &str) -> String { unimplemented!() }
    pub fn caret(_: &str) -> String { unimplemented!() }
    pub fn stdout() -> bool { false }
}
mod format {
    use rune::runtime::Value;
    use crate::declared::Fields;
    pub fn display_width(_: &str) -> usize { unimplemented!() }
    pub fn terminal_safe(_: &str) -> String { unimplemented!() }
    pub fn render_complete_styled(_: &Value, _: Option<&Fields>, _: bool) -> Result<String, String> { unimplemented!() }
    pub fn error_text(_: &Value, _: Option<&Fields>) -> String { unimplemented!() }
}
mod execute {
    use rune::{Vm, runtime::{Value, VmError}};
    pub struct Runtime;
    impl Runtime { pub fn new() -> std::io::Result<Self> { unimplemented!() } }
    pub enum WhenInterrupted { Finish }
    pub enum Outcome { Complete(Value), Interrupted, Budget, Yielded, Failed { error: VmError, exhausted: bool } }
    pub fn drive_async(_: &Runtime, _: &mut Vm, _: [&str; 1], _: (Value,), _: usize, _: WhenInterrupted) -> Outcome { unimplemented!() }
}
