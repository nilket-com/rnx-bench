fn main() {
    let _ = rnx::Extensions::none().with("fixture", |_: &mut rune::Module| Ok(vec![]));
}
