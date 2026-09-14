fn main() {
    use chrono::{DateTime, Utc, Local, SecondsFormat};
    let ts = DateTime::<Utc>::from_timestamp_millis(-1500).unwrap();
    println!("neg ms  : {}", ts.to_rfc3339_opts(SecondsFormat::Millis, true));
    let now = Utc::now();
    println!("now utc : {}", now.to_rfc3339_opts(SecondsFormat::Millis, true));
    let local = Local::now();
    println!("local   : {}  offset={}", local.to_rfc3339(), local.offset());
    let p = DateTime::parse_from_rfc3339("2026-09-14T12:00:00Z").unwrap();
    println!("parsed  : {} ms={}", p, p.timestamp_millis());
    println!("strftime: {}", local.format("%Y-%m-%d %H:%M:%S %Z"));
    println!("max ms  : {:?}", DateTime::<Utc>::from_timestamp_millis(i64::MAX).is_none());
}
