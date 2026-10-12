# JVM jars

`run_bare.sh` and `run_json_loop.sh` run the Scala and Kotlin programs as
precompiled jars, so their timings exclude source compilation but include JVM
startup and any JIT work during the run. The jars are not committed; build them
here before running the suite:

```sh
scala-cli --power package bare.scala --assembly -o bare-scala.jar -f
scala-cli --power package json.scala --assembly -o json-scala.jar -f
kotlinc bare.kt -include-runtime -d bare-kotlin.jar
kotlinc json.kt -cp "$ORG_JSON_JAR" -include-runtime -d json-kotlin.jar
```

`ORG_JSON_JAR` is the org.json jar (20250517 in the dated run). The Kotlin JSON
command in `run_json_loop.sh` puts that jar on the classpath at run time too;
point it at your copy.
