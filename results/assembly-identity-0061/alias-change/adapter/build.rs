fn main(){println!("cargo:rustc-env=BUILD_ORIGIN={}",std::env::var("OUT_DIR").unwrap());}
