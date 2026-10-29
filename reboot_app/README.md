# Reboot project state service (experimental)

This is a Reboot API and servicer for durable repository snapshots. Each `Project` state object stores one JSON snapshot, exposes a read-only `snapshot` Reader (also marked as an MCP tool), and accepts replacement snapshots via a Writer. Publish is deliberately not an MCP tool. This is a foundation, not a production service: no authentication, authorization, ingestion orchestration, or deployment configuration is included. Do not expose it publicly as-is.

The existing static UI reads the checked-in snapshots directly; it is **not yet wired to this service**. The service requires Python >=3.10,<3.13, Reboot and a running Docker daemon. From this directory, following the [Reboot Python guide](https://docs.reboot.dev/get_started/python/):

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install reboot pydantic
rbt dev run
```

Reboot generates Python API code into `backend/api/` during startup. Publishing and reading snapshots requires calling the generated Reboot API with the appropriate state reference; no automatic importer is included. This service has not been runtime-tested in environments without Docker. Pin and test Reboot versions, add authentication and access controls, and implement a trusted importer before deployment.
