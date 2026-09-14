#![allow(dead_code)]
#[path = "../../../../../rnx/src/presentation.rs"] mod presentation;
use std::hint::black_box;
use std::time::Instant;
fn main() {
    let line: String = "let 界 = [42, \"é\\t\", Some(1.25)]; /* comment */\n".repeat(300).chars().take(10_000).collect();
    for _ in 0..100 { black_box(presentation::highlight(black_box(&line))); }
    println!("iteration,nanoseconds,characters,bytes");
    for i in 0..1000 {
        let start = Instant::now();
        black_box(presentation::highlight(black_box(&line)));
        println!("{i},{},{},{}", start.elapsed().as_nanos(), line.chars().count(), line.len());
    }
}
