// Compile the actual changed assembly source, not a second implementation.
#![allow(dead_code)]
mod host {
    pub(crate) struct HostFunction { pub path: String, pub doc: &'static str }
}
#[path = "../../../../rnx/src/extensions.rs"]
mod extensions;
