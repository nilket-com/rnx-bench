//> using dep com.lihaoyi::upickle::4.2.1
object Json {
  def main(args: Array[String]): Unit = {
    var s = ""
    var x = 0
    while (x < 10000) {
      s = ujson.write(ujson.Obj("a" -> ujson.Arr(x, 2, 3), "b" -> "hello"))
      x += 1
    }
    println(s)
  }
}
