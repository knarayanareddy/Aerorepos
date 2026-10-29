"""Reboot durable API: one Project state object per catalog repository."""
from reboot.api import API, Field, Methods, Model, Reader, Tool, Type, Writer


class ProjectState(Model):
    snapshot_json: str = Field(tag=1, default='')


class PublishRequest(Model):
    snapshot_json: str = Field(tag=1)


class SnapshotResponse(Model):
    snapshot_json: str = Field(tag=1)


api = API(
    Project=Type(
        state=ProjectState,
        methods=Methods(
            snapshot=Reader(request=None, response=SnapshotResponse,
                            description='Read the published repository tree snapshot.', mcp=Tool()),
            publish=Writer(request=PublishRequest, response=None,
                           description='Replace a repository tree snapshot.', mcp=None),
        ),
    ),
)
