| runtime | bare `42` | vs rnx | 10k JSON | vs rnx | JSON encoder |
|---|---|---|---|---|---|
| Bun 1.4.2 | 1.8 ms | 2.5× faster | 3.5 ms | 3.3× faster | built-in (C++) |
| Perl 5.40 | 0.74 ms | 5.8× faster | 8.3 ms | 1.4× faster | JSON::XS (C) |
| LuaJIT 2.1 | 0.41 ms | 10.6× faster | 8.4 ms | 1.4× faster | cjson (C) |
| Lua 5.4.7 | 0.38 ms | 11.3× faster | 9.4 ms | 1.2× faster | cjson (C) |
| rnx (Rune 0.14.2) | 4.3 ms | baseline | 11.4 ms | baseline | host::json_stringify (Rust) |
| Deno 2.9.6 | 11.9 ms | 2.7× slower | 12.0 ms | 1.0× slower | built-in (C++) |
| Node 22.22.1 official | 11.6 ms | 2.7× slower | 17.2 ms | 1.5× slower | built-in (C++) |
| Python 3.14.4 | 8.1 ms | 1.9× slower | 30.1 ms | 2.6× slower | json (C) |
| Ruby 3.3.8 | 34.5 ms | 8.0× slower | 46.8 ms | 4.1× slower | json (C) |
| Node 22.22.1 distro | 58.9 ms | 13.6× slower | 68.8 ms | 6.0× slower | built-in (C++) |
| Kotlin 2.4.20 jar | 32.4 ms | 7.5× slower | 105.1 ms | 9.2× slower | org.json (JVM) |
| Scala 3.9.0 jar | 116.1 ms | 26.8× slower | 255.9 ms | 22.4× slower | upickle (JVM) |
| Julia 1.13.0 | 106.5 ms | 24.6× slower | 458.0 ms | 40.1× slower | JSON.jl |
| R 4.5.2 | 90.8 ms | 21.0× slower | 969.7 ms | 85.0× slower | jsonlite (C/R) |

Pure-script encoders, for the split they show: Lua 5.4 + json.lua 40.4 ms (3.5× slower), LuaJIT + json.lua 17.9 ms (1.6× slower), Perl + JSON::PP 68.6 ms (6.0× slower).
rnx after record 0030: `rnx version` 0.50 ms, `rnx run` 3.5 ms; `rnx eval` is the bare baseline above.
