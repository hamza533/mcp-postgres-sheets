// Typed access to the generated reference data (scripts/export_tools.py writes src/data/).
import configData from "@/data/config.json";
import resultsData from "@/data/results.json";
import toolsData from "@/data/tools.json";

export type JsonSchema = {
  type?: string | string[];
  description?: string;
  default?: unknown;
  enum?: unknown[];
  items?: JsonSchema;
  anyOf?: JsonSchema[];
  properties?: Record<string, JsonSchema>;
  required?: string[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  $ref?: string;
  title?: string;
};

export type Tool = {
  name: string;
  title: string | null;
  description: string;
  kind: "read" | "write";
  scope: string;
  hiddenWhenReadOnly: boolean;
  annotations: Record<string, boolean | string>;
  inputSchema: JsonSchema;
  example: Record<string, unknown>;
};

export type EnvVar = { name: string; default: string; section: string; description: string };

export type SafetyCase = {
  id: string;
  category: string;
  title: string;
  outcome: string;
  passed: boolean;
  tool: string;
  example: string;
};

export const tools = toolsData.tools as unknown as Tool[];
export const envVars = configData.variables as EnvVar[];
export const results = resultsData as unknown as {
  safety: {
    passed: number;
    total: number;
    byCategory: Record<string, { passed: number; total: number }>;
    cases: SafetyCase[];
  };
  latency: { maxP95Ms: number; tools: { label: string; p50_ms: number; p95_ms: number }[] };
  tasks: { passed: number; total: number; avgToolCalls: number; model: string } | null;
};

export type InputRow = { name: string; type: string; required: boolean; description: string };

function typeOf(schema: JsonSchema): string {
  if (schema.anyOf) {
    const parts = schema.anyOf.map(typeOf).filter((t) => t !== "null");
    return parts.join(" | ") + (schema.anyOf.some((s) => s.type === "null") ? " (optional)" : "");
  }
  if (schema.enum) return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  if (schema.type === "array") return `${schema.items ? typeOf(schema.items) : "any"}[]`;
  if (Array.isArray(schema.type)) return schema.type.join(" | ");
  return schema.type ?? "any";
}

function constraints(schema: JsonSchema): string {
  const s = schema.anyOf?.find((x) => x.type !== "null") ?? schema;
  const out: string[] = [];
  if (s.minimum !== undefined || s.maximum !== undefined) out.push(`${s.minimum ?? "…"}–${s.maximum ?? "…"}`);
  if (s.maxLength !== undefined) out.push(`max ${s.maxLength} chars`);
  if (schema.default !== undefined && schema.default !== null)
    out.push(`default ${JSON.stringify(schema.default)}`);
  return out.length ? ` (${out.join(", ")})` : "";
}

export function inputRows(tool: Tool): InputRow[] {
  const props = tool.inputSchema.properties ?? {};
  const required = new Set(tool.inputSchema.required ?? []);
  return Object.entries(props).map(([name, schema]) => ({
    name,
    type: typeOf(schema).replace(/(string \| integer \| number \| boolean)(\[\])+/g, "cell[][]"),
    required: required.has(name),
    description: (schema.description ?? "") + constraints(schema),
  }));
}
