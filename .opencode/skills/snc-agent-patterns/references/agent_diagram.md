# Agent diagram reference (`HO5t8UXWsAAJrRf.jpg`)
Image: `HO5t8UXWsAAJrRf.jpg` (Agents / Loops / Graphs flow diagram)

Structure (left → right):
- AGENTS: GOAL → AGENT (icon) → ACTIONS (checklist). Label: "autonomous, goal-driven".
- LOOPS: AGENT inside circular arrow looping back to itself. Label: "thinks before it answers".
- GRAPHS: AGENT branches to WORKER 1 / WORKER 2 / WORKER 3; each worker feeds OUTPUT file. Label: "many agents, one answer".

Adaptation to SNC: treat listener (`pbx/`) as AGENT holding `:23` session; add LOOP over SLA results in `api/`; split parser/DB/WebSocket/proxy/dashboard as WORKER nodes converging to nurse station alert.
