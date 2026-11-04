fn main() {
	cc::Build::new()
		.file("measure.c")
		.include("<VALGRIND_ROOT>/include")
		.compile("step0_measure");
	println!("cargo:rerun-if-changed=measure.c");
}
