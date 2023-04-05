import asyncio

import aiodocker
from rich.progress import Progress

from .console import console
from .setting import IMAGES


async def pull(
    progress: Progress,
    docker: aiodocker.Docker,
    from_image: str,
    sem: asyncio.Semaphore,
) -> None:
    while True:
        async with sem:
            try:
                task = {}
                async for status in docker.pull(from_image, stream=True):
                    if not (status.get("id") and status.get("progressDetail")):
                        continue

                    if status["id"] not in task:
                        description = (
                            f'{from_image} ({status["status"]}: {status["id"]})'
                        )
                        total = status["progressDetail"]["total"]
                        task_id = progress.add_task(description, total=total)
                        task[status["id"]] = task_id

                    completed = status["progressDetail"]["current"]
                    progress.update(task[status["id"]], completed=completed)

            except aiodocker.DockerError as e:
                if "Client.Timeout" in e.message:
                    progress.console.log(
                        "[DockerError]",
                        e.status,
                        e.message,
                        f'"{from_image}"',
                        style="yellow",
                    )
                    continue
                else:
                    progress.console.log(
                        "[DockerError]",
                        e.status,
                        e.message,
                        f'"{from_image}"',
                        style="red",
                    )
            except KeyError as e:
                progress.console.log(
                    "[KeyError]", from_image, e.args, status, style="red"
                )
            else:
                progress.console.log("Completed:", from_image)

            break


async def main() -> None:
    console.log("Pull the following Docker images:", *IMAGES)

    sem = asyncio.Semaphore(3)
    async with aiodocker.Docker() as docker:
        with Progress() as progress:
            await asyncio.wait(
                [
                    asyncio.create_task(
                        pull(
                            docker=docker, progress=progress, from_image=image, sem=sem
                        )
                    )
                    for image in IMAGES
                ]
            )

    console.log("All completed!!")
