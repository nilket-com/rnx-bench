fn main() {
    println!("revision={}", env!("PROBE_REV"));
    println!("dirty={}", env!("PROBE_DIRTY"));
    println!("source={}", env!("PROBE_SOURCE"));
    if std::env::args().any(|a| a == "--require-clean") && env!("PROBE_DIRTY") != "false" {
        eprintln!("probe: dirty or unidentifiable build; use RNX_DEP_RUNTIME=/absolute/path/to/checkout");
        std::process::exit(1);
    }
}
