import json
from aerorepos.v1.project import PublishRequest, SnapshotResponse
from aerorepos.v1.project_rbt import Project
from reboot.aio.contexts import ReaderContext, WriterContext


class ProjectServicer(Project.Servicer):
    async def snapshot(self, context: ReaderContext) -> SnapshotResponse:
        return SnapshotResponse(snapshot_json=self.state.snapshot_json)

    async def publish(self, context: WriterContext, request: PublishRequest) -> None:
        # Reject malformed or unexpectedly large payloads before mutating durable state.
        if len(request.snapshot_json.encode('utf-8')) > 2_000_000:
            raise ValueError('Snapshot exceeds 2 MB')
        data = json.loads(request.snapshot_json)
        if not isinstance(data, dict) or not isinstance(data.get('id'), str) or not isinstance(data.get('files'), list):
            raise ValueError('Snapshot must contain id and files')
        self.state.snapshot_json = request.snapshot_json
