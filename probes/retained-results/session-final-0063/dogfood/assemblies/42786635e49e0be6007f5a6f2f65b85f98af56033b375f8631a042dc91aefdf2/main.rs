fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with("polars", native_0::build).with_lifecycle("postgres", native_1::build))
}
