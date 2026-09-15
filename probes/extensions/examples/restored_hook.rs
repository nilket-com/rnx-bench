fn main() -> Result<(), Box<dyn std::error::Error>> {
    std::panic::set_hook(Box::new(|_| eprintln!("previous hook restored")));
    rnx::main_with(rnx::Extensions::none().with("fixture", |_| Ok(vec![])))?;
    panic!("after main_with returned");
}
