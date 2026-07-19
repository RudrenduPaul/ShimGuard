import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { createRequire } from "node:module";

const CLI = resolve(__dirname, "..", "dist", "cli.js");
const require = createRequire(import.meta.url);
const { version: packageVersion } = require("../package.json") as { version: string };

function runCli(args: string[]): { stdout: string; status: number } {
  try {
    const stdout = execFileSync("node", [CLI, ...args], { encoding: "utf-8" });
    return { stdout, status: 0 };
  } catch (err) {
    const e = err as { stdout?: string; status?: number };
    return { stdout: e.stdout ?? "", status: e.status ?? 2 };
  }
}

describe("CLI", () => {
  it("prints help output listing the verify subcommand", () => {
    const { stdout, status } = runCli(["--help"]);
    expect(status).toBe(0);
    expect(stdout).toMatch(/verify/);
    expect(stdout).toMatch(/shimguard/);
  });

  it("prints the version matching package.json", () => {
    const { stdout, status } = runCli(["--version"]);
    expect(status).toBe(0);
    expect(stdout.trim()).toBe(packageVersion);
  });

  it("exits 2 with a clear error on an invalid repo slug", () => {
    const { stdout, status } = runCli(["verify", "not-a-valid-slug", "--issues", "1"]);
    expect(status).toBe(2);
    expect(stdout).toBe("");
  });

  it("exits 2 with a clear error on an invalid --issues value", () => {
    const { stdout, status } = runCli(["verify", "owner/repo", "--issues", "not-a-number"]);
    expect(status).toBe(2);
    expect(stdout).toBe("");
  });
});
