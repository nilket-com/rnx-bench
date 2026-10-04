// Scratch probe: format one file with upstream main's formatter; extra args are fmt options.
fn main() {
	let mut args = std::env::args().skip(1);
	let path = args.next().expect("path");
	let mut options = rune::Options::default();
	for o in args {
		options.parse_option(&o).expect("option");
	}
	let text = std::fs::read_to_string(&path).unwrap();
	let mut sources = rune::Sources::new();
	sources.insert(rune::Source::new(&path, &text).unwrap()).unwrap();
	let mut diagnostics = rune::Diagnostics::new();
	match rune::fmt::prepare(&sources).with_options(&options).with_diagnostics(&mut diagnostics).format() {
		Ok(files) => for (_, out) in files { print!("{out}"); },
		Err(e) => { eprintln!("error: {e}; {} diagnostics", diagnostics.diagnostics().len()); std::process::exit(1); }
	}
}
