# Mockups: {Feature Name}

## Purpose

Use this file to make the solution shape obvious at a glance.

- Always include system diagrams and workflow diagrams.
- If the feature touches UI, also include UI wireframes, screen states, and interaction flows.
- Keep this file updated when the architecture, workflow, or UI plan changes.

## System Overview

```text
[Client / Trigger]
  -> [Entry Point]
  -> [Core Logic / Workflow]
  -> [Persistence / External Systems]
  -> [Outputs / Side Effects]
```

## Primary Workflow

```text
1. User / system initiates action
2. Request enters {boundary}
3. Validation / routing occurs
4. Core processing runs
5. State is persisted / emitted
6. Result is surfaced to user / operator
```

## State / Sequence Notes

- Key transitions:
- Failure paths:
- Recovery / retry behavior:

## UI Mockups

Add this section when the work has user-facing UI. Use ASCII wireframes, Mermaid, or concise annotated descriptions.

```text
+--------------------------------------------------+
| Screen / Panel name                              |
|--------------------------------------------------|
| Primary content                                  |
| Supporting controls                              |
| Status / errors / next actions                   |
+--------------------------------------------------+
```

## Open Questions

-
