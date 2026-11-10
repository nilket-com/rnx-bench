pub struct Extensions(Vec<fn()->String>);impl Extensions{pub fn none()->Self{Self(vec![])}pub fn with(mut self,_:&str,b:fn()->String)->Self{self.0.push(b);self}pub fn with_lifecycle(self,n:&str,b:fn()->String)->Self{self.with(n,b)}}pub fn main_with(e:Extensions)->Result<(),Box<dyn std::error::Error>>{for b in e.0{println!("{}",b());}Ok(())}
// runtime edit
