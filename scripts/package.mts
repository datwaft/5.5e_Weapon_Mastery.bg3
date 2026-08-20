import assert from "node:assert";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { dirname, resolve } from "node:path";
import { load } from "cheerio";

const exec_file = promisify(execFile);
const ROOT = dirname(import.meta.dirname);

const runner_temp = process.env.RUNNER_TEMP;
assert(runner_temp, "$RUNNER_TEMP should be set");

/**
 * This directory will store one temporary package root for each module.
 * @example `dist/.staging/WeaponMastery_7a1a5ee1-3060-4c0a-a896-6833734c6617/`
 */
const packages_root = resolve(ROOT, "dist", ".staging");

const divine = resolve(runner_temp, "lslib", "Packed", "Tools", "Divine.exe");
const output_directory = resolve(ROOT, "dist");
const exec_options = { maxBuffer: 100 * 1024 * 1024 };
await fs.mkdir(output_directory, { recursive: true });

const package_names = new Set<string>();
for (const entry of await fs.readdir(packages_root, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;

  const id = entry.name;
  const package_root = resolve(packages_root, id);
  const xml = await fs.readFile(resolve(package_root, "Mods", id, "meta.lsx"), "utf8");
  const $ = load(xml, { xml: true });
  const name = $("node[id='ModuleInfo'] > attribute[id='Name']").attr("value");
  assert(name, `'${id}/meta.lsx' should have a module name`);

  const package_base_name = name
    .replace(/[\u0000-\u001f<>:"\/\\|?*]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/[. ]+$/g, "");
  assert(package_base_name, `Module '${id}' has no usable package name`);

  const package_name = `${package_base_name}.pak`;
  const package_name_key = package_name.toLowerCase();
  assert(!package_names.has(package_name_key), `Package name collision: '${package_name}'`);
  package_names.add(package_name_key);

  const package_path = resolve(output_directory, package_name);

  await exec_file(
    divine,
    ["-g", "bg3", "-a", "create-package", "-s", package_root, "-d", package_path, "-c", "lz4hc"],
    exec_options,
  );

  const hash = createHash("sha256")
    .update(await fs.readFile(package_path))
    .digest("hex");
  await fs.writeFile(`${package_path}.sha256`, `${hash}  ${package_name}\n`);
  await fs.rm(package_root, { recursive: true, force: true });
  console.log(`Packaged ${name} (${id}) as ${package_name}`);
}

await fs.rm(packages_root, { recursive: true, force: true });
