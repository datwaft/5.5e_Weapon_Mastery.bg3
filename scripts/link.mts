import fs from "node:fs/promises";
import assert from "node:assert";
import { basename, dirname, resolve } from "node:path";
import { load } from "cheerio";

/**
 * `Data` folder from Baldur's Gate installation
 * @example `C:\\Program Files (x86)\\Steam\\steamapps\\common\\Baldurs Gate 3\\Data`
 */
const GAME_DATA = process.env.GAME_DATA;
assert(GAME_DATA, "$GAME_DATA should be set");

const ROOT = dirname(import.meta.dirname);

const modules: { id: string; name: string }[] = [];
for await (const meta_file of fs.glob("Mods/*/meta.lsx", { cwd: ROOT })) {
  const id = basename(dirname(meta_file));

  const xml = await fs.readFile(meta_file, "utf8");
  const $ = load(xml, { xml: true });
  const name = $("node[id='ModuleInfo'] > attribute[id='Name']").attr("value");
  assert(name, `'${meta_file}' should have a module name`);

  modules.push({ id, name });
}
assert(modules.length > 0, "No modules found");

const path_segments = ["Projects", "Editor/Mods", "Mods", "Public", "Generated/Public"];

const exists = (file: string) =>
  fs
    .access(file)
    .then(() => true)
    .catch(() => false);

for (const module of modules) {
  for (const segment of path_segments) {
    const source = resolve(ROOT, segment, module.id);
    const target = resolve(GAME_DATA, segment, module.id);

    await fs.mkdir(source, { recursive: true });
    await fs.mkdir(dirname(target), { recursive: true });

    if (await exists(target)) {
      if ((await fs.lstat(target)).isSymbolicLink() && (await fs.realpath(target)) === (await fs.realpath(source))) {
        console.log(`Already linked: ${segment}/${module.id}`);
        continue;
      }
      console.error(`Cannot link '${segment}/${module.id}': '${target}' already exists and is not our link`);
      continue;
    }

    await fs.symlink(source, target, "junction");
    console.log(`Linked ${module.name} (${module.id}) ${segment}`);
  }
}
