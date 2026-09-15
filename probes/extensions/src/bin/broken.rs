fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(rnx_extension_fixture::broken())
}
