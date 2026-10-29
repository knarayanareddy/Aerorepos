import asyncio
from project_servicer import ProjectServicer
from reboot.aio.applications import Application


async def main():
    await Application(servicers=[ProjectServicer]).run()


if __name__ == '__main__':
    asyncio.run(main())
