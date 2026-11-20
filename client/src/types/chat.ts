/**
 * UI-layer chat types. These are not sent to or returned by the backend.
 */

/**
 * How an assistant message is rendered (plan §7.4):
 * - `answer`        markdown content with clickable [S1] citation chips
 * - `clarification` blue left-border card; `metadata.needs_clarification === true`
 * - `abstention`    amber info box; `abstained === true`
 */
export type AssistantMessageKind = "answer" | "clarification" | "abstention";
