use std::{fs, path::Path, process::Command};
fn git(root: &Path, args: &[&str]) -> Result<Vec<u8>, ()> {
    let mut c = Command::new("git");
    for (k, _) in std::env::vars_os() {
        if k.to_string_lossy().starts_with("GIT_") { c.env_remove(k); }
    }
    c.env("GIT_CONFIG_GLOBAL", "/dev/null").env("GIT_CONFIG_SYSTEM", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1").env("GIT_ATTR_NOSYSTEM", "1")
        .env("GIT_OPTIONAL_LOCKS", "0").env("GIT_NO_REPLACE_OBJECTS", "1");
    let o = c.arg("-C").arg(root).args(["-c", "core.autocrlf=false", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null"]).args(args).output().map_err(|_| ())?;
    if !o.status.success() { return Err(()); }
    Ok(o.stdout)
}
fn observe(here: &Path) -> Result<(String, bool, String), ()> {
    let top = String::from_utf8(git(here, &["rev-parse", "--show-toplevel"])?).map_err(|_| ())?;
    let root = Path::new(top.trim());
    // A nested fixture must belong to this source root, not an enclosing unrelated repo.
    if root.join("coordinate-fixture").canonicalize().map_err(|_| ())? != here.canonicalize().map_err(|_| ())? { return Err(()); }
    let rev = String::from_utf8(git(root, &["rev-parse", "HEAD"])?).map_err(|_| ())?.trim().to_owned();
    let tree = git(root, &["ls-tree", "-r", "-z", &rev])?;
    let mut paths = Vec::new(); let mut expected = Vec::new(); let mut dirty = false;
    for row in tree.split(|b| *b == 0).filter(|r| !r.is_empty()) {
        let (head, name) = row.split_at(row.iter().position(|b| *b == b'\t').ok_or(())?);
        let fields: Vec<_> = std::str::from_utf8(head).map_err(|_| ())?.split(' ').collect();
        let name = std::str::from_utf8(&name[1..]).map_err(|_| ())?;
        println!("cargo:rerun-if-changed={}", root.join(name).display());
        let meta=fs::symlink_metadata(root.join(name)).map_err(|_| ())?;
        if fields[1] != "blob" || !meta.is_file() { return Err(()); }
        use std::os::unix::fs::PermissionsExt;
        if (meta.permissions().mode() & 0o111 != 0) != (fields[0] == "100755") { dirty = true; }
        paths.push(name.to_owned()); expected.push(fields[2].to_owned());
    }
    for (chunk, expected) in paths.chunks(64).zip(expected.chunks(64)) {
        let mut args=vec!["hash-object", "--no-filters", "--"]; args.extend(chunk.iter().map(String::as_str));
        let got=String::from_utf8(git(root,&args)?).map_err(|_| ())?;
        if got.lines().collect::<Vec<_>>() != expected.iter().map(String::as_str).collect::<Vec<_>>() { dirty = true; }
    }
    let index = git(root, &["ls-files", "-z"])?;
    if index.split(|b| *b==0).filter(|r| !r.is_empty()).collect::<Vec<_>>() != paths.iter().map(|s| s.as_bytes()).collect::<Vec<_>>() { dirty = true; }
    let extra = git(root,&["ls-files", "--others", "--exclude-standard", "-z"])?;
    // Cargo's own marker is transport bookkeeping, not a source file.
    if extra.split(|b| *b==0).any(|r| !r.is_empty() && r!=b".cargo-ok") { dirty = true; }
    println!("cargo:rerun-if-changed={}",root.display());
    Ok((rev,dirty,root.display().to_string()))
}
fn main() {
    let here=std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let (rev,dirty,source)=observe(Path::new(&here)).unwrap_or(("unknown".into(),true,here));
    println!("cargo:rustc-env=PROBE_REV={rev}");
    println!("cargo:rustc-env=PROBE_DIRTY={dirty}");
    println!("cargo:rustc-env=PROBE_SOURCE={source}");
}
