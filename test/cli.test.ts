import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const CLI = resolve(__dirname, "..", "dist", "cli.js");

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

  it("prints the version", () => {
    const { stdout, status } = runCli(["--version"]);
    expect(status).toBe(0);
    expect(stdout.trim()).toBe("0.1.0");
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
