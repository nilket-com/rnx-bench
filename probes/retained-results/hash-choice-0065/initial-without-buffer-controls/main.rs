//! Isolated hash-choice measurement. These wire names never enter product documents.
mod blake;
mod large;
mod parallel;
mod single;
mod stock;
mod wire {
    #[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
    pub struct File {
        pub path: String,
        pub executable: bool,
        pub bytes: u64,
        pub sha256: String,
    }
}
use std::{path::PathBuf, time::Instant};
struct Hex([u8; 32]);
impl AsRef<[u8]> for Hex {
    fn as_ref(&self) -> &[u8] {
        &self.0
    }
}
impl std::fmt::LowerHex for Hex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        for b in self.0 {
            write!(f, "{b:02x}")?;
        }
        Ok(())
    }
}
struct BlakeHash(blake3::Hasher);
impl BlakeHash {
    fn new() -> Self {
        Self(blake3::Hasher::new())
    }
    fn update(&mut self, b: impl AsRef<[u8]>) {
        self.0.update(b.as_ref());
    }
    fn finalize(self) -> Hex {
        Hex(*self.0.finalize().as_bytes())
    }
}
struct ParallelHash(blake3::Hasher);
impl ParallelHash {
    fn new() -> Self {
        Self(blake3::Hasher::new())
    }
    fn update(&mut self, b: impl AsRef<[u8]>) {
        self.0.update_rayon(b.as_ref());
    }
    fn finalize(self) -> Hex {
        Hex(*self.0.finalize().as_bytes())
    }
}
#[derive(serde::Deserialize)]
struct Inputs {
    root: PathBuf,
    paths: Vec<PathBuf>,
    artifact: PathBuf,
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<_> = std::env::args().collect();
    if a.get(1).map(String::as_str) == Some("hash-reference") {
        println!("{}", blake3::hash(&std::fs::read(&a[2])?).to_hex());
        return Ok(());
    }
    if a.get(1).map(String::as_str) == Some("reference") {
        let i: Inputs = serde_json::from_slice(&std::fs::read(&a[2])?)?;
        let files: Vec<_> = i
            .paths
            .iter()
            .map(|p| {
                let bytes = std::fs::read(i.root.join(p)).unwrap();
                (
                    p.to_str().unwrap().to_owned(),
                    blake3::hash(&bytes).to_hex().to_string(),
                )
            })
            .collect();
        let b = std::fs::read(i.artifact)?;
        println!(
            "{}",
            serde_json::json!({"files":files,"artifact":blake3::hash(&b).to_hex().to_string()})
        );
        return Ok(());
    }
    let i: Inputs = serde_json::from_slice(&std::fs::read(&a[3])?)?;
    let start = Instant::now();
    // Parallel rows include pool startup; affinity is set by the external driver.
    if a[2].starts_with("parallel") {
        rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build_global()?;
    }
    macro_rules! run {
        ($m:ident) => {
            match a[1].as_str() {
                "tree" => serde_json::to_value($m::listed(&i.root, i.paths)?)?,
                "native" => {
                    serde_json::to_value($m::native(&i.root, &mut $m::Allowance::default())?)?
                }
                "artifact" => {
                    serde_json::to_value($m::one(&i.artifact, &mut $m::Allowance::default())?)?
                }
                _ => return Err("unknown workload".into()),
            }
        };
    }
    let result = match a[2].as_str() {
        "double-sha256" => run!(stock),
        "single-sha256" => run!(single),
        "blake3" => run!(blake),
        "parallel-16k" => run!(parallel),
        "parallel-1m" => run!(large),
        _ => return Err("unknown algorithm".into()),
    };
    let ms = start.elapsed().as_secs_f64() * 1000.0;
    println!("{}", serde_json::json!({"ms":ms,"result":result}));
    Ok(())
}
#[cfg(test)]
mod tests {
    #[test]
    fn published_empty_blake3_vector() {
        assert_eq!(
            blake3::hash(b"").to_hex().as_str(),
            "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"
        );
    }
}
