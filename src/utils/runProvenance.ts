import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { relative, resolve } from "node:path";

export interface RunProvenance {
  provider: string;
  generatedAt: string;
  benchmarkCommit: string | null;
  workingTreeClean: boolean | null;
  composeFile: string | null;
  resolvedComposeSha256: string | null;
  composeImages: string[];
}

function execute(command: string, args: string[], cwd: string): string | null {
  try {
    return execFileSync(command, args, {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return null;
  }
}

function findComposeFile(
  repositoryRoot: string,
  provider: string,
): string | null {
  const candidates = [
    resolve(repositoryRoot, "wrappers", provider, "docker-compose.yml"),
    resolve(repositoryRoot, "wrappers", provider, "docker-compose.yaml"),
    resolve(repositoryRoot, "wrappers", provider, "compose.yml"),
    resolve(repositoryRoot, "wrappers", provider, "compose.yaml"),
  ];

  return candidates.find((candidate) => existsSync(candidate)) ?? null;
}

export function collectRunProvenance(
  provider: string,
  repositoryRoot: string,
): RunProvenance {
  const benchmarkCommit = execute("git", ["rev-parse", "HEAD"], repositoryRoot);

  const status = execute(
    "git",
    [
      "status",
      "--porcelain",
      "--",
      ".",
      ":(exclude)test-results",
      ":(exclude)hf_export",
    ],
    repositoryRoot,
  );

  const composeFile = findComposeFile(repositoryRoot, provider);
  let resolvedComposeSha256: string | null = null;
  let composeImages: string[] = [];

  if (composeFile) {
    const resolvedCompose = execute(
      "docker",
      ["compose", "-f", composeFile, "config"],
      repositoryRoot,
    );

    if (resolvedCompose !== null) {
      resolvedComposeSha256 = createHash("sha256")
        .update(resolvedCompose)
        .digest("hex");
    }

    const images = execute(
      "docker",
      ["compose", "-f", composeFile, "config", "--images"],
      repositoryRoot,
    );

    if (images) {
      composeImages = images
        .split(/\r?\n/)
        .map((image) => image.trim())
        .filter(Boolean);
    }
  }

  return {
    provider,
    generatedAt: new Date().toISOString(),
    benchmarkCommit,
    workingTreeClean: status === null ? null : status === "",
    composeFile: composeFile ? relative(repositoryRoot, composeFile) : null,
    resolvedComposeSha256,
    composeImages,
  };
}
