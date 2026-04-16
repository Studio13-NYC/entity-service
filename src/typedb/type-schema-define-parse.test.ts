import { describe, expect, it } from "vitest";

import {
  parseEntityTypeLabelsFromDefineSchema,
  parseStringAttributeTypesOwnedByEntityFromDefineSchema,
} from "./type-schema-define-parse";

describe("parseEntityTypeLabelsFromDefineSchema", () => {
  it("parses TypeDB 3 define entity blocks", () => {
    const define = `
define
entity user,
  owns username;
attribute username, value string;
entity organization,
  owns status;
entity company,
  sub organization;
`;
    const labels = parseEntityTypeLabelsFromDefineSchema(define);
    expect(labels).toContain("user");
    expect(labels).toContain("organization");
    expect(labels).toContain("company");
  });
});

describe("parseStringAttributeTypesOwnedByEntityFromDefineSchema", () => {
  it("returns string-valued owns for an entity block", () => {
    const define = `
define
attribute name, value string;
attribute karma, value double;
entity musician,
  owns name;
entity band,
  owns name;
`;
    expect(parseStringAttributeTypesOwnedByEntityFromDefineSchema(define, "musician")).toEqual(["name"]);
  });
});
