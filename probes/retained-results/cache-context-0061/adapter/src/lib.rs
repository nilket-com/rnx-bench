pub fn build()->String{let p=env!("RETAINED_PATH");format!("{}\n{}\n{}",env!("CARGO_MANIFEST_DIR"),p,std::fs::read_to_string(p).unwrap())}
