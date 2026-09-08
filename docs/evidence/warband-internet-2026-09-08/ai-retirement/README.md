# Temporary Amsterdam AI client retirement — 2026-09-08

The user authorized retiring the temporary VM after the successful
[native Internet-play verification](../README.md). Retirement completed at
09:04 UTC. Only these three resources were deleted:

| Resource | Identity | Final API check |
| --- | --- | --- |
| `saga2d-warband-ai` VM, `nl-ams-1` | `c14893d7-0610-4714-9d8d-f84009467322` | HTTP 404 |
| Dedicated 20 GB SBS disk | `eb73decb-5680-4fb6-be75-0c7ac209033c` | HTTP 404 |
| Reserved IPv4, formerly `51.158.175.125` | `75f89c9d-e7e9-4c47-8f49-662e94a44639` | HTTP 404 |

The deployment credential was scoped to project
`42ae77f6-b012-4e0f-b76d-93be6a61c56f`. Before deleting anything, API checks
matched the VM name, project, ownership tag, single attached disk and address;
SSH confirmed its managed-instance marker. The journal was retained before
storage deletion. The disk and IP were confirmed detached before deletion.

`before.json` records those identities and Paris health before retirement.
`actions.jsonl` records the terminate action and the two explicit deletes.
`after.json` records all three HTTP 404 responses, zero Amsterdam instances
and reserved IPs in this project, and the unchanged Paris server identity and
address. The Paris multiplayer VM `d56b46e5-fe7d-404c-9b5d-48bc87143433` at
`51.159.207.49` remained running; `https://games.tachyon-ai.eu/healthz` returned
HTTP 200 with `ok` before and after retirement.

`ai-journal.jsonl` retains 27 allowlisted JSON events, including 15 submitted
orders and authoritative snapshots reaching tick 399. It also records a later
room that timed out waiting for a partner. Submission events alone do not
prove order acceptance; the snapshots and earlier native report supply that
evidence. Non-JSON systemd chatter and arbitrary error text were omitted;
private seat credentials and cloud keys are not included.

The active local `dist/online-ai/target.json` was removed. Its history was
saved as `dist/online-ai/target.retired.json`, with the former target nested
under `former_target` so remote commands cannot use it as a live target.
Future use requires provisioning a new VM. The released old IP must not be
contacted as though it still belongs to this project.

Paris resources, the Saga2D project and IAM, the Amsterdam security group,
and the shared Ubuntu image snapshot were retained. No deletion targeted
them. The retired client's compute, storage and IPv4 resources no longer
exist; this receipt is resource verification, not a cloud invoice.

The operation followed Scaleway's official
[Instance action API](https://www.scaleway.com/en/developers/api/instance/v1/instances):
`terminate` deletes the instance but only detaches SBS volumes. The detached
disk was then deleted through the
[Block volume API](https://www.scaleway.com/en/developers/api/block/volume),
and the released address through the
[Instance IP API](https://www.scaleway.com/en/developers/api/instance/v1/ips).
