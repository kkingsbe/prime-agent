import { type Static, Type } from "typebox";
import type { ToolDefinition } from "../extensions/types.js";

export const delegateSchema = Type.Object({
	task: Type.String({
		description:
			"Self-contained task for the subagent. Include everything it needs: files to read, work to produce, and how to report back.",
	}),
	name: Type.Optional(
		Type.String({
			description: "Short name for the subagent (e.g. 'draft', 'tester').",
		}),
	),
	model: Type.Optional(
		Type.String({
			description: "Optional model id override for this subagent.",
		}),
	),
});

export type DelegateToolInput = Static<typeof delegateSchema>;

export interface DelegateToolOptions {
	/** Spawns an RLM child and resolves with its admission handle. */
	spawnChild: (task: string, name?: string, model?: string) => Promise<unknown>;
	/** Optional sync/blocking spawn: resolves with the child's final message instead of the admission handle. */
	blockForResult?: (task: string, name?: string, model?: string) => Promise<unknown>;
}

export interface DelegateToolDetails {
	status: "ok";
}

export function createDelegateToolDefinition(
	options?: DelegateToolOptions,
): ToolDefinition<typeof delegateSchema, DelegateToolDetails> {
	return {
		name: "delegate",
		label: "delegate",
		description:
			"Spawn a background subagent (RLM child) to work on `task` in isolation. " +
			"Multiple delegate calls in one message run their subagents in parallel. " +
			"THE TURN ENDS AUTOMATICALLY after this call — do not keep working, polling, or checking status; " +
			"subagent results arrive as messages on later turns.",
		promptSnippet: "delegate - spawn a background subagent, then the turn ends automatically",
		executionMode: "parallel",
		parameters: delegateSchema,
		execute: async (_toolCallId, params, _signal, _onUpdate, _ctx) => {
			if (options?.blockForResult) {
				const final = await options.blockForResult(params.task, params.name, params.model);
				return {
					content: [{ type: "text", text: typeof final === "string" ? final : JSON.stringify(final) }],
					details: { status: "ok" },
					isError: false,
				};
			}
			const handle = await options?.spawnChild(params.task, params.name, params.model);
			return {
				content: [
					{
						type: "text",
						text: JSON.stringify(handle),
					},
				],
				details: { status: "ok" },
				isError: false,
				// The turn ends after this batch: children run in the background and
				// results arrive via messages on later turns (OpenAI-handoff style).
				terminate: true,
			};
		},
	};
}
