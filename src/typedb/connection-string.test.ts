import { describe, expect, it } from "vitest";

import { parseTypeDbConnectionString } from "./connection-string";

describe("parseTypeDbConnectionString", () => {
  it("parses TypeDB Cloud style typedb://user:pass@https://host:port/?name=db", () => {
    const p = parseTypeDbConnectionString(
      "typedb://admin:password@https://jie88a-0.cluster.typedb.com:80/?name=newgroovegraph",
    );
    expect(p?.addresses).toEqual(["https://jie88a-0.cluster.typedb.com:80"]);
    expect(p?.username).toBe("admin");
    expect(p?.password).toBe("password");
    expect(p?.databaseFromQuery).toBe("newgroovegraph");
  });

  it("returns undefined for empty or non-typedb schemes", () => {
    expect(parseTypeDbConnectionString("")).toBeUndefined();
    expect(parseTypeDbConnectionString("   ")).toBeUndefined();
    expect(parseTypeDbConnectionString("http://localhost")).toBeUndefined();
  });
});
