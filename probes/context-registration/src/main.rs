use std::{hint::black_box, time::Instant};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mode = std::env::args().nth(1).unwrap_or_default();
    if mode == "empty" { return Ok(()); }
    let t = Instant::now();
    let context = rune::Context::with_default_modules()?;
    let elapsed = t.elapsed();
    black_box(&context);
    if mode == "lifecycle" {
        let t = Instant::now();
        drop(context);
        println!("{},{}", elapsed.as_nanos(), t.elapsed().as_nanos());
        return Ok(());
    }
    if mode == "time" { println!("{}", elapsed.as_nanos()); }
    Ok(())
}
