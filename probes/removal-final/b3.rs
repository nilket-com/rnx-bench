use std::io::Read;
fn main() {
    let mut bytes = Vec::new();
    std::io::stdin().read_to_end(&mut bytes).unwrap();
    println!("{}", blake3::hash(&bytes).to_hex());
}
