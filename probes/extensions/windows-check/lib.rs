// Isolated Windows type check of actual assembly/lifecycle sources. This is
// not a full rnx cross-build or Windows execution; the rest of the host is stubbed.
#![allow(dead_code)]
mod host {
    pub(crate) struct HostFunction { pub path: String, pub doc: &'static str }
}
mod format {
    pub(crate) fn terminal_safe(text: &str) -> String { text.into() }
}
#[path = "../../../../rnx/src/extensions.rs"]
mod extensions;
#[path = "../../../../rnx/src/lifecycle.rs"]
mod lifecycle;
pub use lifecycle::Scope;
