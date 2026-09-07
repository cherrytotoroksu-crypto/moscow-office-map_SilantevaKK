import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const load = (name) => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const save = (name, value) => fs.writeFileSync(path.join(root, name), JSON.stringify(value, null, 2) + '\n', 'utf8');
const dates = load('data/building_dates.json');
const layer = load('data/all_projects_layer.json');
const classifierPath = path.join(root, 'data/unified_classifier_audited_2026-08-27.json');
const classifierText = fs.readFileSync(classifierPath, 'utf8');
const classifier = JSON.parse(classifierText);
const layerById = new Map(layer.map((row) => [row.canonical_project_id, row]));
const filled = [];

for (const row of classifier.records) {
  if (row.sales_start_date) continue;
  const matches = (row.legacy_ids || []).map((id) => layerById.get(id)).filter(Boolean);
  const dated = matches.filter((r) => r.sales_start_year && r.sales_start_quarter);
  if (dated.length !== 1) continue;
  const sourceKey = Object.keys(dates).find((key) => dates[key].canonical_project_id === dated[0].canonical_project_id);
  if (!sourceKey) continue;
  const source = dates[sourceKey];
  row.sales_start_date = `${dated[0].sales_start_year}-Q${dated[0].sales_start_quarter}`;
  row.sales_start_confidence = 'needs_review';
  row.sales_start_source = `data/building_dates.json key=${sourceKey}; checked ${source.last_checked}; ${source.source || ''}`;
  filled.push(row.name);
}

let output = classifierText;
for (const row of classifier.records) {
  if (!row.sales_start_date) continue;
  const marker = `"name": ${JSON.stringify(row.name)},`;
  const start = output.indexOf(marker);
  if (start < 0) throw new Error(`Cannot locate classifier row: ${row.name}`);
  const end = output.indexOf('\n      "canonical_no":', start);
  if (end < 0) throw new Error(`Cannot locate canonical_no for: ${row.name}`);
  const block = output.slice(start, end);
  if (block.includes('"sales_start_date"')) continue;
  const fields = `\n      "sales_start_date": ${JSON.stringify(row.sales_start_date)},\n      "sales_start_confidence": ${JSON.stringify(row.sales_start_confidence)},\n      "sales_start_source": ${JSON.stringify(row.sales_start_source)},`;
  output = output.slice(0, end) + fields + output.slice(end);
}
fs.writeFileSync(classifierPath, output, 'utf8');
console.log(JSON.stringify({ filled: filled.length, names: filled }, null, 2));
