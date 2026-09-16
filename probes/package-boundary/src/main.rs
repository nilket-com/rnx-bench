use rune::ast::Spanned;
use rune::compile::{self, SourceLoader};
use rune::{Context, Diagnostics, Item, Source, Sources, Vm};
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

struct Loader {
    roots: BTreeMap<String, PathBuf>,
    trace: Vec<Value>,
}
impl SourceLoader for Loader {
    fn load(&mut self, root: &Path, item: &Item, span: &dyn Spanned) -> compile::Result<Source> {
        let parts = item
            .iter()
            .map(|c| match c {
                rune::item::ComponentRef::Str(s) => Ok(s.to_owned()),
                _ => Err(compile::Error::msg(span, "non-string module item")),
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mapped = parts.first().and_then(|s| self.roots.get(s));
        let mut base = if let Some(path) = mapped {
            path.clone()
        } else {
            root.parent().unwrap().to_owned()
        };
        for part in parts.iter().skip(usize::from(mapped.is_some())) {
            base.push(part);
        }
        // The mapped root itself is a directory entry (mod.rn); nested candidates
        // retain pinned Rune order: name/mod.rn before name.rn.
        let candidates = if mapped.is_some() && parts.len() == 1 {
            vec![base.join("mod.rn")]
        } else {
            vec![base.join("mod.rn"), base.with_extension("rn")]
        };
        let chosen = candidates.iter().find(|p| p.is_file()).cloned();
        self.trace.push(json!({"root":root,"item":item.to_string(),"parts":parts,"mapped":mapped,"candidates":candidates,"chosen":chosen}));
        let path = chosen.ok_or_else(|| {
            compile::Error::msg(span, format!("missing probe module: {}", base.display()))
        })?;
        Source::from_path(&path).map_err(|e| compile::Error::msg(span, e))
    }
}
fn main() {
    let args: Vec<_> = std::env::args_os().collect();
    let entry = PathBuf::from(&args[1]);
    let roots: BTreeMap<String, PathBuf> =
        serde_json::from_slice(&std::fs::read(&args[2]).unwrap()).unwrap();
    let mut loader = Loader {
        roots,
        trace: vec![],
    };
    let mut sources = Sources::new();
    sources.insert(Source::from_path(&entry).unwrap()).unwrap();
    let context = Context::with_default_modules().unwrap();
    let mut diagnostics = Diagnostics::new();
    let result = rune::prepare(&mut sources)
        .with_context(&context)
        .with_source_loader(&mut loader)
        .with_diagnostics(&mut diagnostics)
        .build();
    let mut report =
        json!({"entry":entry,"loads":loader.trace,"compile_ok":result.is_ok(),"errors":[]});
    let mut errors = vec![];
    for d in diagnostics.diagnostics() {
        if let rune::diagnostics::Diagnostic::Fatal(fatal) = d
            && let rune::diagnostics::FatalDiagnosticKind::CompileError(error) = fatal.kind()
        {
            errors.push(json!({"source":sources.get(fatal.source_id()).unwrap().name(),"offset":error.span().range().start,"message":error.to_string()}));
        }
    }
    report["errors"] = json!(errors);
    if let Ok(unit) = result {
        let unit = Arc::new(unit);
        let mut vm = Vm::new(Arc::new(context.runtime().unwrap()), unit.clone());
        match vm.call(["main"], ()) {
            Ok(v) => report["value"] = json!(rune::from_value::<i64>(v).unwrap()),
            Err(error) => {
                report["runtime_error"] = json!(error.to_string());
                if let Some(location) = error.first_location()
                    && let Some(inst) = location
                        .unit
                        .debug_info()
                        .and_then(|info| info.instruction_at(location.ip))
                {
                    let source = sources.get(inst.source_id).unwrap();
                    let path = source.path().unwrap();
                    let text = std::fs::read_to_string(path).unwrap();
                    let offset = inst.span.range().start;
                    report["origin"] = json!({"source":path,"offset":offset,"line":text[..offset].bytes().filter(|b|*b==b'\n').count()+1});
                }
            }
        }
    }
    println!("{report}");
}
