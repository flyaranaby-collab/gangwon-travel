// 토스판 화면 만들기: ① 토스 기능 묶음(ait-bridge.js) ② 수첩 본문을 토스 규칙에 맞게 바꿔 dist/index.html 로 저장
import { build } from "esbuild";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
mkdirSync("dist", { recursive: true });
await build({ entryPoints: ["src/bridge.js"], bundle: true, minify: true, format: "iife", target: ["es2018"], outfile: "dist/ait-bridge.js", legalComments: "none" });
execFileSync("python3", ["../tools/toss_copy.py", process.env.NOTE_SRC || "../source/index.html", "dist/index.html", "src/glue.js"], { stdio: "inherit" });
