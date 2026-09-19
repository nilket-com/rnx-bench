//! Isolated raw-object checkout check. No status/diff/clean-filter comparison.
use std::{collections::HashSet, fs, os::unix::fs::PermissionsExt, path::Path, process::Command};
fn git(root: &Path, args: &[&str]) -> Result<Vec<u8>, String> {
    let mut c = Command::new("git");
    for (k, _) in std::env::vars_os() {
        if k.to_string_lossy().starts_with("GIT_") {
            c.env_remove(k);
        }
    }
    c.env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_ATTR_NOSYSTEM", "1")
        .env("GIT_NO_REPLACE_OBJECTS", "1")
        .env("GIT_OPTIONAL_LOCKS", "0");
    let p = c
        .arg("-C")
        .arg(root)
        .args([
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.attributesFile=/dev/null",
        ])
        .args(args)
        .output()
        .map_err(|e| e.to_string())?;
    if !p.status.success() {
        return Err(String::from_utf8_lossy(&p.stderr).into_owned());
    }
    Ok(p.stdout)
}
fn verify(root: &Path, rev: &str) -> Result<usize, String> {
    let head = git(root, &["rev-parse", "HEAD"])?;
    if String::from_utf8_lossy(&head).trim() != rev {
        return Err("HEAD differs".into());
    }
    let raw = git(root, &["ls-tree", "-r", "-z", rev])?;
    let mut rows = Vec::new();
    let mut dirs = HashSet::new();
    let mut total = 0u64;
    for row in raw.split(|b| *b == 0).filter(|r| !r.is_empty()) {
        let pos = row
            .iter()
            .position(|b| *b == b'\t')
            .ok_or("bad tree record")?;
        let fields = std::str::from_utf8(&row[..pos])
            .map_err(|e| e.to_string())?
            .split(' ')
            .collect::<Vec<_>>();
        let name = std::str::from_utf8(&row[pos + 1..]).map_err(|e| e.to_string())?;
        if fields.len() != 3 || fields[1] != "blob" || !matches!(fields[0], "100644" | "100755") {
            return Err("unsupported tree entry".into());
        }
        let p = root.join(name);
        for ancestor in p.parent().unwrap().ancestors() {
            if ancestor == root || !dirs.insert(ancestor.to_owned()) {
                break;
            }
            if !fs::symlink_metadata(ancestor)
                .map_err(|e| e.to_string())?
                .is_dir()
            {
                return Err("symlink/non-directory component".into());
            }
        }
        let m = fs::symlink_metadata(&p).map_err(|e| e.to_string())?;
        if !m.is_file() {
            return Err("nonregular file".into());
        }
        if (m.permissions().mode() & 0o111 != 0) != (fields[0] == "100755") {
            return Err("mode differs".into());
        }
        total += m.len();
        if rows.len() >= 100_000 || total > 512 * 1024 * 1024 {
            return Err("allowance".into());
        }
        rows.push((name.to_owned(), fields[2].to_owned()));
    }
    let index = git(root, &["ls-files", "--stage", "-z"])?;
    let mut staged = Vec::new();
    for row in index.split(|b| *b == 0).filter(|r| !r.is_empty()) {
        let pos = row
            .iter()
            .position(|b| *b == b'\t')
            .ok_or("bad index record")?;
        if !row[..pos].ends_with(b" 0") {
            return Err("unmerged index".into());
        }
        staged.push(std::str::from_utf8(&row[pos + 1..]).map_err(|e| e.to_string())?);
    }
    if staged != rows.iter().map(|r| r.0.as_str()).collect::<Vec<_>>() {
        return Err("tracked set differs".into());
    }
    let extra = git(root, &["ls-files", "--others", "--exclude-standard", "-z"])?;
    if extra
        .split(|b| *b == 0)
        .any(|p| !p.is_empty() && p != b".cargo-ok")
    {
        return Err("untracked source".into());
    }
    for chunk in rows.chunks(64) {
        let mut args = vec!["hash-object", "--no-filters", "--"];
        args.extend(chunk.iter().map(|r| r.0.as_str()));
        let hashes = git(root, &args)?;
        if String::from_utf8_lossy(&hashes).lines().collect::<Vec<_>>()
            != chunk.iter().map(|r| r.1.as_str()).collect::<Vec<_>>()
        {
            return Err("raw blob mismatch".into());
        }
    }
    Ok(rows.len())
}
fn main() {
    let args = std::env::args().collect::<Vec<_>>();
    match verify(Path::new(&args[1]), &args[2]) {
        Ok(n) => println!("{n}"),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    }
}
