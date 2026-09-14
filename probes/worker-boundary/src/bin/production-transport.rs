// Type-check the actual production source with this isolated dependency graph.
#[path = "../../../../../rnx/src/worker_transport.rs"]
mod transport;
fn main() {
    let _ = transport::open as fn(usize, usize) -> _;
}
