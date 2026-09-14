fn main() {
    use time::{OffsetDateTime, UtcOffset, format_description::well_known::Rfc3339};
    let ts = OffsetDateTime::from_unix_timestamp_nanos(-1_500_000_000).unwrap();
    println!("neg ms  : {}", ts.format(&Rfc3339).unwrap());
    let now = OffsetDateTime::now_utc();
    println!("now utc : {}", now.format(&Rfc3339).unwrap());
    let off = UtcOffset::current_local_offset();
    println!("local   : offset={:?}", off);
    let p = OffsetDateTime::parse("2026-09-14T12:00:00Z", &Rfc3339).unwrap();
    println!("parsed  : {} ms={}", p, p.unix_timestamp_nanos() / 1_000_000);
    println!("max ms  : {:?}", OffsetDateTime::from_unix_timestamp_nanos(i128::from(i64::MAX) * 1_000_000).is_err());
}
