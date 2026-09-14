fn main() {
    use jiff::{Timestamp, Zoned, tz::TimeZone};
    let ts = Timestamp::from_millisecond(-1500).unwrap();
    println!("neg ms  : {ts}");
    let now = Timestamp::now();
    println!("now utc : {now}");
    let local = now.to_zoned(TimeZone::system());
    println!("local   : {local}  offset={}", local.offset());
    let p: Timestamp = "2026-09-14T12:00:00Z".parse().unwrap();
    println!("parsed  : {} ms={}", p, p.as_millisecond());
    let z: Zoned = "2026-09-14T12:00:00+02:00[Europe/Paris]".parse().unwrap();
    println!("zoned   : {z}");
    println!("strftime: {}", local.strftime("%Y-%m-%d %H:%M:%S %Z"));
    println!("max ms  : {:?}", Timestamp::from_millisecond(i64::MAX).is_err());
}
