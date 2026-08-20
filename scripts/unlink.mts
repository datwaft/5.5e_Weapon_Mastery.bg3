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

const lstat = (file: string) =>
  fs.lstat(file).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return undefined;
    throw error;
  });

for (const module of modules) {
  for (const segment of path_segments) {
    const source = resolve(ROOT, segment, module.id);
    const target = resolve(GAME_DATA, segment, module.id);

    const target_stat = await lstat(target);
    if (!target_stat) {
      console.log(`Not linked: ${segment}/${module.id}`);
      continue;
    }

    // Only remove symlinks and junctions. `realpath` also works for regular paths.
    if (!target_stat.isSymbolicLink()) {
      console.error(`Cannot unlink '${segment}/${module.id}': '${target}' is not a link to this checkout`);
      process.exitCode = 1;
      continue;
    }

    // Resolve both paths before deleting anything. A missing path is not verifiable.
    const [target_realpath, source_realpath] = await Promise.all([fs.realpath(target), fs.realpath(source)]).catch(
      (error: NodeJS.ErrnoException) => {
        if (error.code === "ENOENT") return [undefined, undefined];
        throw error;
      },
    );
    if (!target_realpath || !source_realpath || target_realpath !== source_realpath) {
      console.error(`Cannot unlink '${segment}/${module.id}': '${target}' is not a link to this checkout`);
      process.exitCode = 1;
      continue;
    }

    await fs.unlink(target);
    console.log(`Unlinked ${module.name} (${module.id}) ${segment}`);
  }
}
