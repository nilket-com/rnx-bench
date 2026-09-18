use std::path::PathBuf;
#[derive(serde::Deserialize)]struct Config{roots:Vec<PathBuf>,candidate:bool,entries:usize,bytes:u64,#[serde(default)] repeat:bool}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let c:Config=serde_json::from_slice(&std::fs::read(std::env::args_os().nth(1).ok_or("config")?)?)?;
 let mut a=fingerprint::Allowance::bounded(c.entries,c.bytes);
 let roots=c.roots.clone();
 let answer=if c.candidate{fingerprint::candidate::many(c.roots,&mut a)}else{(c.roots.into_iter().collect::<std::collections::BTreeSet<_>>()).into_iter().map(|p|{let t=fingerprint::native(&p,&mut a)?;trace::between(&p)?;Ok(t)}).collect::<Result<Vec<_>,String>>()};
 let repeated=if c.repeat {Some(fingerprint::candidate::many(roots,&mut fingerprint::Allowance::bounded(c.entries,c.bytes)))}else{None};
 println!("{}",serde_json::to_string(&serde_json::json!({"answer":answer,"repeated":repeated,"events":trace::take(),"remaining_bytes":a.remaining_bytes()}))?);Ok(())
}
