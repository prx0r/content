/**
 * content-sensor extension — pi tools backed by the content MCP (stdio).
 *
 * Spawns `python3 /home/ubuntu/content/mcp_server.py --serve` once per
 * session and exposes signal → rank → expand → compile verbs to the model.
 * The MCP owns intent + graph + contracts + receipts; pi just drives it.
 */
import { spawn, type ChildProcess } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const MCP_CMD = process.env.CONTENT_MCP_PY || "python3";
const MCP_ARG = process.env.CONTENT_MCP_PATH || "/home/ubuntu/content/mcp_server.py";

let proc: ChildProcess | null = null;
let nextId = 0;
const pending = new Map<number, (v: unknown) => void>();
let buf = "";

function ensureProc(): ChildProcess {
	if (proc && proc.exitCode === null) return proc;
	proc = spawn(MCP_CMD, [MCP_ARG, "--serve"], { stdio: ["pipe", "pipe", "ignore"] });
	proc.stdout!.on("data", (chunk: Buffer) => {
		buf += chunk.toString();
		let nl: number;
		while ((nl = buf.indexOf("\n")) >= 0) {
			const line = buf.slice(0, nl).trim();
			buf = buf.slice(nl + 1);
			if (!line) continue;
			try {
				const msg = JSON.parse(line) as { id?: number; result?: unknown; error?: unknown };
				if (typeof msg.id === "number" && pending.has(msg.id)) {
					const res = pending.get(msg.id)!;
					pending.delete(msg.id);
					res(msg.error ? { error: msg.error } : msg.result);
				}
			} catch { /* keep going */ }
		}
	});
	return proc;
}

function mcpCall(tool: string, args: Record<string, unknown>): Promise<unknown> {
	const p = ensureProc();
	return new Promise((resolve) => {
		const id = ++nextId;
		pending.set(id, resolve);
		p.stdin!.write(JSON.stringify({ jsonrpc: "2.0", id, method: "tools/call", params: { name: tool, arguments: args } }) + "\n");
		setTimeout(() => {
			if (pending.has(id)) { pending.delete(id); resolve({ error: "mcp timeout" }); }
		}, 590000);
	});
}

async function toolText(tool: string, args: Record<string, unknown>): Promise<string> {
	const res = (await mcpCall(tool, args)) as {
		content?: Array<{ type?: string; text?: string }>;
		error?: unknown;
	};
	if (res && typeof res === "object" && "error" in res) return `ERROR: ${JSON.stringify(res.error).slice(0, 500)}`;
	const parts = res?.content ?? [];
	return parts.map((c) => String(c.text ?? "")).join("\n").slice(0, 8000) || "(empty result)";
}

const GARDEN = Type.String({ description: "Garden: powpowpow or ukgraph", default: "ukgraph" });

export default function contentSensor(pi: ExtensionAPI) {
	pi.on("session_shutdown", () => {
		try { proc?.kill(); } catch { /* already gone */ }
		proc = null;
	});
	pi.registerTool({
		name: "content_signals",
		label: "Content Signals",
		description: "Top deterministic, evidence-linked content signals for a garden. Start here.",
		parameters: Type.Object({ garden: GARDEN }),
		async execute(_id, params) {
			const text = await toolText("signals_top", { garden: params.garden, limit: 10 });
			return { content: [{ type: "text", text }], details: { tool: "signals_top" } };
		},
	});
	pi.registerTool({
		name: "content_rank",
		label: "Content Rank",
		description: "Rank eligible signals by interest with framing verdicts (Jev or deterministic fallback).",
		parameters: Type.Object({ garden: GARDEN }),
		async execute(_id, params) {
			const text = await toolText("rank_signals", { garden: params.garden, limit: 5 });
			return { content: [{ type: "text", text }], details: { tool: "rank_signals" } };
		},
	});
	pi.registerTool({
		name: "content_expand",
		label: "Content Expand",
		description: "Seed signal plus supporting graph neighbourhood (2-4 strongest facts).",
		parameters: Type.Object({ signal_id: Type.String({ description: "Signal id from content_signals" }) }),
		async execute(_id, params) {
			const text = await toolText("expand_signal", { signal_id: params.signal_id });
			return { content: [{ type: "text", text }], details: { tool: "expand_signal" } };
		},
	});
	pi.registerTool({
		name: "content_compile",
		label: "Content Compile",
		description: "Signal plus query (CHANGE, WHY, WHERE, COMPARE, OPPORTUNITY, WARNING, EXPLAIN) into a gated render manifest.",
		parameters: Type.Object({
			signal_id: Type.String(),
			query: Type.String({ description: "Content query", default: "OPPORTUNITY" }),
		}),
		async execute(_id, params) {
			const text = await toolText("content_from_signal", { signal_id: params.signal_id, query: params.query });
			return { content: [{ type: "text", text }], details: { tool: "content_from_signal" } };
		},
	});
	pi.registerTool({
		name: "content_queue",
		label: "Content Queue",
		description: "Review queue: signal to video attachments with render paths.",
		parameters: Type.Object({}),
		async execute(_id) {
			const text = await toolText("lineage", { limit: 20 });
			return { content: [{ type: "text", text }], details: { tool: "lineage" } };
		},
	});
	pi.registerTool({
		name: "content_status",
		label: "Content Status",
		description: "What the content factory can do right now (renderers, audio, data, publishing).",
		parameters: Type.Object({}),
		async execute(_id) {
			const text = await toolText("content_status", {});
			return { content: [{ type: "text", text }], details: { tool: "content_status" } };
		},
	});
}
