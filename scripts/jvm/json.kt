import org.json.JSONObject
import org.json.JSONArray
fun main() {
    var s = ""
    for (x in 0 until 10000) {
        s = JSONObject().put("a", JSONArray().put(x).put(2).put(3)).put("b", "hello").toString()
    }
    println(s)
}
