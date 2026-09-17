use std::{
	future::Future,
	io::Write,
	pin::Pin,
	rc::Rc,
	sync::Arc,
	task::{Context, Poll},
};
fn event(s: &str) {
	let mut f = std::fs::OpenOptions::new()
		.append(true)
		.create(true)
		.open(std::env::var("RNX_PROBE_EVENTS").unwrap())
		.unwrap();
	writeln!(f, "{s}").unwrap();
}
struct ContextOwner;
impl Drop for ContextOwner {
	fn drop(&mut self) {
		event("context dropped");
	}
}
#[derive(rnx::rune::Any)]
struct ValueOwner;
impl Drop for ValueOwner {
	fn drop(&mut self) {
		event("value dropped");
	}
}
struct Pending {
	started: bool,
	panic: bool,
	_local: Rc<()>,
}
impl Future for Pending {
	type Output = Result<i64, String>;
	fn poll(mut self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<Self::Output> {
		if !self.started {
			self.started = true;
			event("operation polled");
		}
		Poll::Pending
	}
}
impl Drop for Pending {
	fn drop(&mut self) {
		if self.started {
			event("operation dropped");
			assert!(!self.panic, "injected destructor failure");
		}
	}
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
	rnx::main_with(
		rnx::Extensions::none().with_lifecycle("fixture", |m, scope| {
			m.ty::<ValueOwner>().map_err(|e| e.to_string())?;
			m.function("value", || ValueOwner)
				.build()
				.map_err(|e| e.to_string())?;
			let owner = Arc::new(ContextOwner);
			m.function("owner", move || {
				let _ = &owner;
				42i64
			})
			.build()
			.map_err(|e| e.to_string())?;
			m.function("pending", move |panic: bool| {
				scope.track(Pending {
					started: false,
					panic,
					_local: Rc::new(()),
				})
			})
			.build()
			.map_err(|e| e.to_string())?;
			Ok(vec![])
		}),
	)
}
