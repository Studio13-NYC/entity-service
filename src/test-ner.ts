import { NerServiceClient } from "./ner-client/client";
import { toEntitySchemaPayload } from "./typedb/schema-adapter";

const baseUrl = process.env.NER_SERVICE_URL ?? "http://127.0.0.1:8000";

function heading(title: string): void {
  console.log("\n---", title, "---\n");
}

async function main(): Promise<void> {
  const client = new NerServiceClient(baseUrl);

  heading(`NER_SERVICE_URL=${baseUrl}`);

  heading("GET /health");
  const health = await client.health();
  console.log(JSON.stringify(health, null, 2));

  heading('POST /extract — full phrase (labels: recording + artist)');
  const full = await client.extract({
    text: "Girlfriend by Matt Sweet",
    labels: ["recording", "artist"],
  });
  console.log(JSON.stringify(full, null, 2));

  heading("POST /extract — label filter (artist only)");
  const artistOnly = await client.extract({
    text: "Girlfriend by Matt Sweet",
    labels: ["artist"],
  });
  console.log(JSON.stringify(artistOnly, null, 2));

  heading("POST /extract — no labels (omit field)");
  const noLabels = await client.extract({
    text: "Girlfriend by Matt Sweet",
  });
  console.log(JSON.stringify(noLabels, null, 2));

  heading("POST /extract — empty text");
  const empty = await client.extract({ text: "" });
  console.log(JSON.stringify(empty, null, 2));

  heading("POST /extract — options.use_aliases: false (no alias matches)");
  const aliasesOff = await client.extract({
    text: "Girlfriend by Matt Sweet",
    options: { use_aliases: false },
  });
  console.log(JSON.stringify(aliasesOff, null, 2));

  heading("POST /extract — schema via TypeDB adapter (toEntitySchemaPayload)");
  const typeDbSnapshot = {
    entityTypes: [{ id: "work" }],
    knownEntities: [
      {
        typeId: "work",
        canonicalName: "Invisible Cities",
        aliases: ["Invis Cities"],
      },
    ],
  };
  const withSchema = await client.extract({
    text: "Reading Invis Cities tonight",
    schema: toEntitySchemaPayload(typeDbSnapshot),
  });
  console.log(JSON.stringify(withSchema, null, 2));

  heading("POST /extract — use_model: true (placeholder returns no extra entities)");
  const modelFlag = await client.extract({
    text: "Girlfriend by Matt Sweet",
    options: { use_model: true },
  });
  console.log(JSON.stringify(modelFlag, null, 2));

  console.log("\nAll smoke calls finished OK.\n");
}

main().catch((err: unknown) => {
  console.error("ERROR:", err);
  process.exit(1);
});
