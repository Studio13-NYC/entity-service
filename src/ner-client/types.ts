export type ExtractOptions = {
  use_aliases?: boolean;
  use_model?: boolean;
  /** When true (and `useTypeDbTypes` is false), map labels not in `schema` to `gg-generic`. */
  useGgGenericForUnknownCatalogLabels?: boolean;
};

export type TypeCandidateItem = {
  label: string;
  source?: string;
  score?: number | null;
  fitsExistingType?: boolean | null;
};

export type EntityTypePayload = {
  name: string;
  aliases?: string[];
};

export type KnownEntityPayload = {
  label: string;
  /** Canonical surface form */
  canonical?: string;
  /** Handoff / Python alias for `canonical` */
  canonical_text?: string;
  aliases?: string[];
};

export type EntitySchemaPayload = {
  /** String ids and/or `{ name, aliases }` objects (matches Python BeforeValidator). */
  entityTypes?: (string | EntityTypePayload)[];
  knownEntities?: KnownEntityPayload[];
};

export type ExtractRequest = {
  text: string;
  labels?: string[];
  options?: ExtractOptions;
  /** Runtime known entities + aliases (JSON key `schema` on the wire). */
  schema?: EntitySchemaPayload;
  /** Read-only TypeDB define alignment on this process (requires `TYPEDB_*` on FastAPI). */
  useTypeDbTypes?: boolean;
};

export type EntityCandidate = {
  text: string;
  label: string;
  start: number;
  end: number;
  confidence: number;
  labelCandidates?: TypeCandidateItem[];
};

export type ExtractResponse = {
  entities: EntityCandidate[];
  typeCandidates: TypeCandidateItem[];
};

export type HealthResponse = {
  ok: boolean;
};
