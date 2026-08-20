import assert from "node:assert";
import fs from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import { load } from "cheerio";

const ROOT = dirname(import.meta.dirname);
const runner_temp = process.env.RUNNER_TEMP;
const release_tag = process.env.GITHUB_REF_NAME;

assert(runner_temp, "$RUNNER_TEMP should be set");
assert(release_tag, "$GITHUB_REF_NAME should be set");

const tag_match = /^v(\d+)\.(\d+)\.(\d+)$/.exec(release_tag);
assert(tag_match, "$GITHUB_REF_NAME should match vMAJOR.MINOR.PATCH");

const major = BigInt(tag_match[1]);
const minor = BigInt(tag_match[2]);
const revision = BigInt(tag_match[3]);
assert(major <= 0x1ffn, "The tag major version does not fit Version64");
assert(minor <= 0xffn, "The tag minor version does not fit Version64");
assert(revision <= 0xffffn, "The tag patch version does not fit Version64");

const expected_version = `${major}.${minor}.${revision}.0`;
// Version64 stores major, minor, revision, and build in 9, 8, 16, and 31 bits.
const expected_version64 = (major << 55n) + (minor << 47n) + (revision << 31n);

/**
 * This directory will store one temporary package root for each module.
 * @example `$RUNNER_TEMP/packages/WeaponMastery_7a1a5ee1-3060-4c0a-a896-6833734c6617/`
 */
const packages_root = resolve(runner_temp, "packages");
await fs.rm(packages_root, { recursive: true, force: true });
await fs.mkdir(packages_root, { recursive: true });

for await (const meta_file of fs.glob("Mods/*/meta.lsx", { cwd: ROOT })) {
  const id = basename(dirname(meta_file));

  const xml = await fs.readFile(resolve(ROOT, meta_file), "utf8");
  const $ = load(xml, { xml: true });
  const name = $("node[id='ModuleInfo'] > attribute[id='Name']").attr("value");
  assert(name, `'${meta_file}' should have a module name`);

  const raw_version64 = $("node[id='ModuleInfo'] > attribute[id='Version64']").attr("value");
  assert(raw_version64, `'${meta_file}' should have a module version64`);
  assert(/^\d+$/.test(raw_version64), `'${meta_file}' should have a module version64`);

  const version64 = BigInt(raw_version64);
  const version = `${version64 >> 55n}.${(version64 >> 47n) & 0xffn}.${(version64 >> 31n) & 0xffffn}.${version64 & 0x7ffffffn}`;

  if (version !== expected_version) {
    console.log(
      `::warning title=Version mismatch::${name} (${id}) is ${version}, but ${release_tag} requires ${expected_version}`,
    );
  }

  const package_root = resolve(packages_root, id);
  const package_meta_path = resolve(package_root, "Mods", id, "meta.lsx");

  await fs.mkdir(dirname(package_meta_path), { recursive: true });
  await fs.cp(resolve(ROOT, "Mods", id), resolve(package_root, "Mods", id), { recursive: true });

  for (const path of ["Public", "Generated/Public"]) {
    const source = resolve(ROOT, path, id);
    const destination = resolve(package_root, path, id);
    await fs.mkdir(dirname(destination), { recursive: true });
    await fs.cp(source, destination, { recursive: true }).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "ENOENT") throw error;
    });
  }

  const scripts_source = resolve(ROOT, "Scripts");
  await fs
    .cp(scripts_source, resolve(package_root, "Scripts"), { recursive: true })
    .catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "ENOENT") throw error;
    });

  {
    const xml = await fs.readFile(package_meta_path, "utf8");
    const $ = load(xml, { xml: true });
    const version64 = $("node[id='ModuleInfo'] > attribute[id='Version64']");
    assert(version64.length === 1, `'${meta_file}' should have one module Version64`);
    version64.attr("value", expected_version64.toString());
    await fs.writeFile(package_meta_path, $.xml());
  }

  console.log(`Staged ${name} (${id})`);
}
