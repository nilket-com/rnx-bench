pub fn build()->String{std::fs::read_to_string(concat!(env!("OUT_DIR"),"/retained.txt")).unwrap()}
