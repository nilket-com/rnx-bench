use rune::{
	SourceId,
	ast::{self, Spanned},
	parse::Parser,
};
use serde_json::{Value, json};
fn metrics(source: &str) -> Value {
	let mut parser = Parser::new(source, SourceId::EMPTY, false);
	let mut tokens = 0;
	let mut questions = 0;
	while !parser.is_eof().unwrap() {
		let token = parser.parse::<ast::Token>().unwrap();
		tokens += 1;
		questions += usize::from(matches!(token.kind, ast::Kind::QuestionMark));
	}
	json!({"physical_lines":source.lines().count(),"nonblank_noncomment_lines":source.lines().filter(|l|!l.trim().is_empty()&&!l.trim_start().starts_with("//")).count(),"characters":source.chars().count(),"tokens":tokens,"question_tokens":questions})
}
fn main() {
	let mut outputs = serde_json::Map::new();
	for path in std::env::args().skip(1) {
		let text = std::fs::read_to_string(&path).unwrap();
		let file = Parser::new(&text, SourceId::EMPTY, false)
			.parse_all::<ast::File>()
			.unwrap();
		let mut groups = std::collections::BTreeMap::<&str, String>::new();
		for (item, _) in &file.items {
			let group = match item {
				ast::Item::Fn(f) => match &text[f.name.span().range()] {
					"routes" => "routes",
					"features" | "home" | "page" => "content",
					"join" | "field" | "escape" | "respond" | "html" | "not_allowed" | "bad"
					| "hex" | "decode" | "form" => "helpers",
					_ => "handlers",
				},
				_ => "constants",
			};
			groups
				.entry(group)
				.or_default()
				.push_str(&format!("{}\n", &text[item.span().range()]));
		}
		let mut output = serde_json::Map::new();
		output.insert("total".into(), metrics(&text));
		for (group, source) in groups {
			output.insert(group.into(), metrics(&source));
		}
		outputs.insert(path, Value::Object(output));
	}
	println!("{}", serde_json::to_string_pretty(&outputs).unwrap());
}
