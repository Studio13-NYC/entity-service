import type { EntitySchemaPayload, KnownEntityPayload } from "../ner-client/types";

/**
 * Normalized entity type from TypeDB (or your query layer). `id` becomes the extractor
 * entity label on the wire (`knownEntities[].label`).
 */
export type TypeDbEntityType = {
  id: string;
};

/**
 * One persisted entity with a canonical name and optional synonym strings from TypeDB.
 */
export type TypeDbKnownEntity = {
  typeId: string;
  canonicalName: string;
  aliases?: readonly string[];
};

/**
 * Snapshot your app would build after TypeDB reads (types + known instances).
 * Keep this shape stable at the adapter boundary; map raw driver rows into it upstream.
 */
export type TypeDbSchemaSnapshot = {
  entityTypes: readonly TypeDbEntityType[];
  knownEntities: readonly TypeDbKnownEntity[];
};

/**
 * Converts a TypeDB-oriented snapshot into the JSON body fragment expected by
 * `POST /extract` (`schema`: `entityTypes` + `knownEntities`).
 */
export function toEntitySchemaPayload(snapshot: TypeDbSchemaSnapshot): EntitySchemaPayload {
  const entityTypes = snapshot.entityTypes.map((t) => t.id);
  const knownEntities: KnownEntityPayload[] = snapshot.knownEntities.map((e) => ({
    label: e.typeId,
    canonical: e.canonicalName,
    aliases: [...(e.aliases ?? [])].filter((a) => a.trim().length > 0),
  }));
  return { entityTypes, knownEntities };
}
