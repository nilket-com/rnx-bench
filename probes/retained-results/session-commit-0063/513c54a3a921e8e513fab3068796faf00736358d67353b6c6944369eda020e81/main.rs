fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with_lifecycle("fixture", native_0::build).with("polars", native_1::build).with_lifecycle("postgres", native_2::build))
}
