fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx::Extensions::none().with("fixture", rnx_extension_fixture::build))
}
