# Aerorepos

A curated, static directory of open-source aerospace engineering projects. Explore aerodynamics, propulsion, turbomachinery, structures, design optimization, flight dynamics, space systems and supporting simulation infrastructure. This is a starting collection, **not an exhaustive inventory**. The focus labels and descriptions are editorial; repository statistics are snapshots and do not imply endorsement, validation, or fitness for a particular engineering application.

## Explore locally

```sh
python3 server/app.py
# Open http://localhost:8000
```

No build step or third-party packages are required. The Python standard-library server loads the checked-in catalog and snapshots into SQLite at startup and serves them through a read-only API. A static server also works as a fallback. Search supports multiple terms, `/` focuses search, and you can filter by discipline, sort, inspect a project, copy its Markdown entry, or pick a random project from the current results. The catalog is available at [`data/catalog.json`](data/catalog.json).

## Curation and updates

Entries are manually selected for relevance to aerospace or its supporting engineering workflows. Some tools (for example, wind-turbine simulation or general finite-element libraries) are included because their methods are useful to aerospace, not because they are aircraft-specific. Verify the license and engineering applicability upstream: GitHub may not identify a license, in which case the index says “See repository.” Stars and push dates are GitHub metadata, not measures of quality or validation.

To add a project, edit `data/catalog.json`, using an existing entry as a template. Include a canonical GitHub repository URL, a specific focus, a concise description, and an existing domain. Check the repository's license before proposing it. To refresh metadata for all existing entries, authenticate the GitHub CLI and run:

```sh
python3 scripts/refresh.py
```

The refresh fails without writing the file if any GitHub request fails. It does not automatically discover projects or verify license terms. Contributions and corrections are welcome through GitHub issues or pull requests.

## Inspiration and research

- [AI ToolScour](https://github.com/knarayanareddy/toolscour) inspired the static catalog, searchable domains, project inspector, sorting, random discovery and copy-as-Markdown features.
- [Awesome Aerospace Engineering](https://github.com/awesomelistsio/awesome-aerospace-engineering) inspired broad discipline-based discovery. Unlike that broader list, Aerorepos focuses on source repositories and does not intentionally catalog commercial-only tools.
- [Awesome Space Systems Simulation](https://github.com/aoezhb/awesome-space-systems-simulation) inspired explicit scope, practical focus labels and caution about validation and licensing.

Repository metadata is obtained from the GitHub API. Consult the linked upstream projects for authoritative licensing, documentation, validation and current status.

## Map and retrieval

The interactive ecosystem map connects every project to its editorial discipline. Node size reflects the snapshot star count. Select a node for project details; pan by dragging and zoom with the wheel or controls. Related-project suggestions use shared discipline and focus, not verified dependencies. They must not be interpreted as integration or compatibility claims. All map nodes are keyboard accessible.

The discovery assistant is **lexical retrieval over catalog records**, not a generative RAG system: it ranks matching terms and displays the actual catalog description and source link. It does not crawl upstream documentation, use embeddings, generate answers, or claim to know information absent from the index. A full RAG implementation would require a documented ingestion, chunking, embedding, retrieval and model-serving pipeline, as well as source-level citations and evaluation; none is configured here.

## Toward a census

A complete census cannot be guaranteed: GitHub search has indexing and result limits, topic tagging is inconsistent, and many projects live elsewhere. This discovery tool collects candidates for review, rather than silently mixing noisy matches into the curated catalog:

```sh
python3 scripts/discover.py --pages 2 --output candidates.json
```

It searches several engineering topics, deduplicates against the existing catalog, records the matching queries and emits an **unreviewed** queue. GitHub CLI authentication and API access are required; rate limits and the 1,000-results-per-query ceiling apply. Review each candidate for aerospace relevance, repository identity, source availability and license before adding it. The queue is ignored by Git by default. Broader discovery should include additional queries and non-GitHub hosts; neither this tool nor the current catalog covers all such sources.

[Reboot](https://github.com/reboot-dev/reboot) is a full-stack application framework with durable state, reactive frontends and MCP support. It is not itself a repository mapping tool. Aerorepos does not currently use Reboot; its map is an independent exploratory implementation.

## Repository source explorer

Each catalog project's profile links to a repository explorer showing the actual **file containment tree** at a pinned Git tree revision, with folder drill-down, indexed-path search and links to files on GitHub. Regenerate all snapshots with `python3 scripts/index_repositories.py`, or use `--repo owner/name` for one project. The indexer requests GitHub's recursive tree via the authenticated `gh` CLI, does not execute repository code, and records the revision, date, GitHub truncation flag, returned total and selection limit. It selects up to 300 files per repository with documentation and source files prioritized; when partial, the map and search cover only that sample. The map shows up to 18 immediate children while the side list shows all indexed children. A returned tree count is not a complete repository count if GitHub reports truncation. File edges represent containment, **not parsed imports, calls, or dependencies**. Some files and whole paths may therefore be absent. Snapshots can be stale and the linked commit or file might no longer be available upstream.

## Reboot foundation

[`reboot_app/`](reboot_app/) contains an experimental Reboot API and servicer for per-project durable snapshots, with read and write operations and an MCP-marked reader. The current explorer is still static and does not call this service; it has no automatic snapshot importer, authentication, or production deployment. Reboot requires Docker, which was unavailable in the development sandbox, so the service has not been runtime-tested. This is not yet the full Reboot-backed application or the code-dependency graph requested; those require integration, source parsing, and deployment work.

### Sampled Python import links

`python3 scripts/index_python_imports.py` optionally analyzes up to five indexed Python files per repository using Python's AST and stores unambiguously matched local imports in the snapshot. Select a file in the explorer to see any sampled outgoing or incoming links with source-line evidence. Absolute matches are resolved against indexed path suffixes and relative matches against the source directory; these are heuristics, not a full Python import resolver. Namespaces, dynamic imports, external libraries, other languages, unindexed files and unparsed files are not comprehensively covered. Parse/download failures are recorded per file. Re-run this script after regenerating trees, because tree regeneration replaces the analysis. These links are evidence to investigate, not guaranteed runtime dependency graphs.

## Docker-free backend

`server/app.py` provides a runnable alternative to Reboot, using Python's built-in HTTP server and SQLite; it does **not** implement Reboot or MCP. It serves `/api/catalog`, `/api/snapshot?repo=owner%2Frepo` and `/api/health` to the same-origin browser UI. The UI uses the API when available and falls back to checked-in static files on a static host. The explorer labels the source it used.

At startup, the server validates and atomically replaces its database index with the current checked-in catalog and available snapshot JSON files. Rerun the indexer and restart the server to ingest changed snapshots. The database is generated at `data/aerorepos.sqlite3` and is Git-ignored; the JSON files remain the source of truth. An invalid snapshot prevents startup rather than replacing a good existing index. Test with `python3 -m unittest discover -s tests`.

The server is read-only and binds to localhost by default. For a sandbox preview use `python3 server/app.py --host 0.0.0.0 --port 8001`. It is intended for local exploration, not a hardened production deployment. It does not offer authentication, background harvesting, source-content retrieval, generative RAG, or the durable workflow and MCP features of Reboot. The experimental Reboot scaffold remains separate and is not used by this server.
