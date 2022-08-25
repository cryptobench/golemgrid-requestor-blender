#!/usr/bin/env python3
import asyncio
from asyncio import CancelledError
from datetime import datetime, timedelta
import pathlib
import sys
import json
from yapapi import events
import time
import argparse
from yapapi import (
    Golem,
    NoPaymentAccountError,
    Task,
    __version__ as yapapi_version,
    WorkContext,
    windows_event_loop_fix,
)
from yapapi.log import enable_default_logger
from yapapi.payload import vm
from yapapi.rest.activity import BatchTimeoutError
import os
import requests
import aiohttp
import requests
from yapapi.rest.activity import CommandExecutionError

examples_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(examples_dir))
task_id = os.getenv('TASKID')
url = 'http://api:8002/v1/status/subtask/blender'

agreements = {}

start_time = datetime.now()


def submit_status_subtask(provider_name, provider_id, task_data, status, time=None):
    url = 'http://api:8002/v1/status/subtask/blender'
    task_id = os.getenv('TASKID')
    if time:
        post_data = {'id': task_id, 'status': status, 'provider': provider_name,
                     'provider_id': provider_id, 'task_data': task_data, 'time': time}
    else:
        post_data = {'id': task_id, 'status': status,
                     'provider': provider_name, 'provider_id': provider_id, 'task_data': task_data, }

    requests.post(url, data=post_data)


def submit_status(status, total_time=None):
    url = 'http://api:8002/v1/status/task/blender'
    task_id = os.getenv('TASKID')
    if total_time:
        post_data = {'id': task_id, 'status': status,
                     'time_spent': total_time}
    else:
        post_data = {'id': task_id, 'status': status, }
    requests.post(url, data=post_data)


def event_consumer(event):

    if isinstance(event, events.AgreementCreated):
        agreements[event.agr_id] = [
            event.provider_id, event.provider_info.name]
    elif isinstance(event, events.TaskStarted):
        agreements[event.task_data] = datetime.now()
        submit_status_subtask(
            provider_name=agreements[event.agr_id][1], provider_id=agreements[event.agr_id][0], task_data=event.task_data, status="Computing")
    elif isinstance(event, events.TaskFinished):
        time_spent = datetime.now() - agreements[int(event.task_id)]
        submit_status_subtask(
            provider_name=agreements[event.agr_id][1], provider_id=agreements[event.agr_id][0], task_data=int(event.task_id), status="Finished", time=time_spent)
    elif isinstance(event, events.WorkerFinished):
        exc = event.exc_info
        reason = str(exc) or repr(exc) or "unexpected error"
        if isinstance(exc, CommandExecutionError):
            submit_status_subtask(
                provider_name=agreements[event.agr_id][1], provider_id=agreements[event.agr_id][0], task_data=event.job_id, status="Failed")
    elif isinstance(event, events.ComputationFinished):
        if not event.exc_info:
            submit_status(status="Finished", total_time={
                datetime.now() - start_time})
        else:
            _exc_type, exc, _tb = event.exc_info
            if isinstance(exc, CancelledError):
                submit_status(status="Cancelled", total_time={
                    datetime.now() - start_time})
            else:
                submit_status(status="Failed", total_time={
                    datetime.now() - start_time})


async def main(params, subnet_tag, driver=None, network=None):
    package = await vm.repo(
        image_hash="b1cd32b619c5e1dc91a257f11dcec1a88f2d071f5941d17358328d77",
        min_mem_gib=0.5,
        min_storage_gib=2.0,
    )
    submit_status(status="Started")

    async def worker(ctx: WorkContext, tasks):
        scene_path = params['scene_file']
        scene_name = params['scene_name']
        format = params['output_format']
        out_extension = params['output_extension'].lower()
        task_id = os.getenv("TASKID")
        ctx.send_file(scene_path, f"/golem/input/{scene_name}")
        async for task in tasks:
            frame = task.data
            ctx.run("/bin/bash", "-c",
                    f"blender -b /golem/input/{scene_name} -o /golem/output/output# -F {format} -t 0 -f {frame}")
            # format includes .
            output_file = f"/requestor/output/output_{frame}{out_extension}"
            ctx.download_file(
                f"/golem/output/output{frame}{out_extension}", output_file)
            try:
                # Set timeout for executing the script on the provider. Usually, 30 seconds
                # should be more than enough for computing a single frame, however a provider
                # may require more time for the first task if it needs to download a VM image
                # first. Once downloaded, the VM image will be cached and other tasks that use
                # that image will be computed faster.
                yield ctx.commit(timeout=timedelta(minutes=175))
                # TODO: Check if job results are valid
                # and reject by: task.reject_task(reason = 'invalid file')
                task.accept_result(result=output_file)
                url = 'http://api:8002/v1/blender/subtask/upload'
                with open(output_file, 'rb') as f:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, data={'file': f, 'id': os.getenv("TASKID")}) as response:
                            await response.text()

            except BatchTimeoutError:
                print(
                    f"{TEXT_COLOR_RED}"
                    f"Task {task} timed out on {ctx.provider_name}, time: {task.running_time}"
                    f"{TEXT_COLOR_DEFAULT}"
                )
                submit_status_subtask(
                    provider_name=ctx.provider_name, provider_id=ctx.provider_id, task_data=frame, status="Failed")
                raise

    # Iterator over the frame indices that we want to render
    frames: range = range(params['startframe'], params['endframe'])
    # Worst-case overhead, in minutes, for initialization (negotiation, file transfer etc.)
    # TODO: make this dynamic, e.g. depending on the size of files to transfer
    init_overhead = 3
    # Providers will not accept work if the timeout is outside of the [5 min, 30min] range.
    # We increase the lower bound to 6 min to account for the time needed for our demand to
    # reach the providers.
    min_timeout, max_timeout = 6, 170

    timeout = timedelta(minutes=max(
        min(init_overhead + len(frames) * 2, max_timeout), min_timeout))

    async with Golem(
        budget=10.0,
        subnet_tag=subnet_tag,
        driver=driver,
        network=network,
    ) as golem:
        await golem.add_event_consumer(event_consumer)

        print(
            f"yapapi version: {yapapi_version}\n"
            f"Using subnet: {subnet_tag}, "
            f"payment driver: {golem.driver}, "
            f"and network: {golem.network}\n"
        )

        num_tasks = 0
        start_time = datetime.now()

        completed_tasks = golem.execute_tasks(
            worker,
            [Task(data=frame) for frame in frames],
            payload=package,
            max_workers=1000,
            timeout=timeout,
        )
        async for task in completed_tasks:
            num_tasks += 1
            print(
                f"Task computed: {task}, result: {task.result}, time: {task.running_time}"
            )

        print(
            f"{num_tasks} tasks computed, total time: {datetime.now() - start_time}"
        )

    task_id = os.getenv("TASKID")
    url = f"http://container-manager-api:8003/v1/container/ping/shutdown/{task_id}"
    requests.get(url)

if __name__ == "__main__":
    now = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")

    # This is only required when running on Windows with Python prior to 3.8:
    windows_event_loop_fix()
    parser = argparse.ArgumentParser()
    parser.add_argument('-j', '--jpath', type=str, required=True)
    args = parser.parse_args()
    jsonParams = open(args.jpath,)
    # returns JSON object as
    # a dictionary
    params = json.load(jsonParams)
    enable_default_logger(
        log_file=f"blender-yapapi-{now}.log",
        debug_activity_api=True,
        debug_market_api=True,
        debug_payment_api=True,
    )

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        main(params, subnet_tag="devnet-beta",
             network="rinkeby")
    )

    try:
        loop.run_until_complete(task)
    except NoPaymentAccountError as e:
        handbook_url = (
            "https://handbook.golem.network/requestor-tutorials/"
            "flash-tutorial-of-requestor-development"
        )
        print(
            f"No payment account initialized for driver `{e.required_driver}` "
            f"and network `{e.required_network}`.\n\n"
            f"See {handbook_url} on how to initialize payment accounts for a requestor node."
        )
    except KeyboardInterrupt:
        print(
            "Shutting down gracefully, please wait a short while "
            "or press Ctrl+C to exit immediately..."
        )
        task.cancel()
        try:
            loop.run_until_complete(task)
            print(
                f"Shutdown completed, thank you for waiting!"
            )
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
