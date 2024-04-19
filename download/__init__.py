# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/7/13 14:55
# @Version     : Python 3.12.2
"""
requests无法处理连接后服务器拒绝响应的情况,会持续阻塞

方法一: 使用信号量, 信号只会存在主线程中, 不适合多线程程序
    import signal
    class Timeout():
        # Timeout for use with the `with` statement.

        class TimeoutException(Exception):
            # Simple Exception to be called on timeouts.
            pass

        def _timeout(signum, frame):
            # Raise an TimeoutException.
            #
            # This is intended for use as a signal handler.
            # The signum and frame arguments passed to this are ignored.
            raise Timeout.TimeoutException()

        def __init__(self, timeout=10):
            self.timeout = timeout
            signal.signal(signal.SIGALRM, Timeout._timeout)

        def __enter__(self):
            signal.alarm(self.timeout)

        def __exit__(self, exc_type, exc_value, traceback):
            signal.alarm(0)
            return exc_type is Timeout.TimeoutException

    # Demonstration:
    from time import sleep

    print('This is going to take maximum 10 seconds...')
    with Timeout(10):
        sleep(15)
        print('No timeout?')
    print('Done')


方法二: 使用回溯, 回溯的标记依旧只会存在主线程中, 不适合多线程程序
    import requests, sys, time

    TOTAL_TIMEOUT = 10
    def trace_function(frame, event, arg):
        if time.time() - start > TOTAL_TIMEOUT:
            raise Exception('Timed out!')
        return trace_function
    start = time.time()
    sys.settrace(trace_function)
    try:
        res = requests.get('http://localhost:8080', timeout=(3, 6))
    except:
        raise
    finally:
        sys.settrace(None)


方法三: 使用pycurl三方库, 封装过于简单, 使用麻烦; pip install pycurl
    import pycurl
    import io

    url = 'http://www.example.com/example.zip'
    timeout_ms = 1000
    raw = io.StringIO()
    c = pycurl.Curl()
    c.setopt(pycurl.TIMEOUT_MS, timeout_ms)  # total timeout in milliseconds
    c.setopt(pycurl.WRITEFUNCTION, raw.write)
    c.setopt(pycurl.NOSIGNAL, 1)
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.HTTPGET, 1)
    try:
        c.perform()
    except pycurl.error:
        pass # or just pass if you don't want to print the error


方法四: 使用timeout-decorator三方库, 对方案一中信号量的封装, 依旧不适合多线程程序; pip install timeout-decorator
    @timeout_decorator.timeout(5)
    def mytest():
        print("Start")
        for i in range(1,10):
            time.sleep(1)
            print("{} seconds have passed".format(i))

方案五: 使用一个线程来监听其他线程的状态, 超时则结束请求, 不引入任何三方库, 但需要手动实现细节.
"""
import abc
import copy
import itertools
import logging
import math
import shutil
import time
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests

from download.exceptions import *


@dataclass
class RequestStatus(object):
    start_time: float
    response: requests.Response = None
    finished: bool = False


@dataclass
class Task(object):
    url: str
    slice: tuple
    headers: dict
    serial_number: int
    download_times: int = 0
    confirmed: bool = False


@dataclass
class DownloadStatus(object):
    error: DownloadException
    task: Task


DEFAULT_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/85.0.4183.102 Safari/537.36'
}


class Downloader(metaclass=abc.ABCMeta):
    def __init__(self, url, headers, output_dir: Path, output_file: Path, logger: logging.Logger,
                 timeout: float = 30, threads_num: int = 5):
        # 下载状态记录字典
        # self.statuses: typing.Dict[int, RequestStatus] = {}
        self.timeout = timeout
        self.url = url
        self.headers = headers
        self.is_stop_all = False
        self.temp_dir = output_dir
        self.output_file = output_file
        self.max_times = 3
        if not isinstance(threads_num, int) or threads_num < 1:
            threads_num = 1
        self.threads_num = threads_num
        self.stop_status_codes = [403]
        self.chunk_size = 1024 * 1024
        self.logger = logger
        self.tasks = []
        self.status_code = 200

    def build_tasks(self):
        headers = self.build_headers(self.headers)
        if 'range' not in headers:
            headers['range'] = 'bytes=0-'
        resp = requests.request('get', self.url, headers=headers, stream=True, timeout=self.timeout)
        resp.raise_for_status()
        content_range = int(resp.headers['Content-Range'].split('/', 1)[-1])
        memory_size = min(50 * 1024 * 1024, math.ceil(content_range / self.threads_num))
        tasks = []
        serial_number = 0
        for start_position in itertools.count(0, memory_size):
            if start_position >= content_range:
                break
            tasks.append(Task(
                url=resp.url,
                slice=(start_position, 0, min(start_position + memory_size, content_range) - 1),
                headers=copy.deepcopy(self.headers),
                serial_number=serial_number
            ))
            serial_number += 1
        return tasks

    @staticmethod
    def build_headers(headers: dict) -> dict:
        """
        构建流式下载请求头
        :param headers: 请求头
        :return:
        """
        if headers is None:
            headers = DEFAULT_HEADERS
        headers = {k.lower(): v for k, v in headers.items()}
        if 'user-agent' not in headers:
            headers['user-agent'] = DEFAULT_HEADERS['user-agent']
        return headers

    def raise_for_status(self, response: requests.Response):
        """
        状态码异常时抛出错误
        :param response: 响应
        :return:
        """
        if response.status_code in self.stop_status_codes:
            self.logger.warning(f'异常状态码: {response.status_code}, 终止程序运行！')
            self.status_code = response.status_code
            self.is_stop_all = True
        try:
            response.raise_for_status()
        except Exception as e:
            raise RequestError(type(e).__module__ + '.' + type(e).__name__)

    @property
    def is_all_tasks_confirmed(self) -> bool:
        """
        是否所有的下载任务都已经确认
        :return:
        """
        for task in self.tasks:
            if task.confirmed is False:
                return False
        return True

    def concurrent(self):
        """
        并发下载任务
        :return:
        """
        with ThreadPoolExecutor(max_workers=self.threads_num) as executor:
            while not (self.is_stop_all or self.is_all_tasks_confirmed):
                for download in executor.map(self.download, [task for task in self.tasks if task.confirmed is False]):
                    if download.error.message == DownloadSuccess.__name__:
                        download.task.confirmed = True

    # def watchdog(self):
    #     """监测每个线程的下载时间,超时则停止连接"""
    #     # 暂时不处理
    #     # 即使关闭连接,requests还是会卡主,这是套接字决定的,永远无法处理
    #     for thread_id, status in self.statuses.items():
    #         if status.finished is False and status.response is not None and time.time() - status.start_time > self.timeout:
    #             # 关闭连接
    #             status.response.close()

    def download(self, task: Task) -> DownloadStatus:
        path = self.temp_dir / f'{task.serial_number:05}'
        try:
            if self.is_stop_all:
                raise StopAllDownloadTasksError()
            start, offset, end = task.slice
            if start + offset > end:
                self.logger.warning(f'切片异常: {start + offset}-{end}')
                raise ValueError(f'切片异常: {start + offset}-{end}')
            task.download_times += 1
            if task.download_times > self.max_times:
                self.logger.warning(f'已达到下载上限：{self.max_times}, 终止程序运行')
                self.is_stop_all = True
                raise ReachMaxDownloadLimitError(f'download_times: {task.download_times}')
            elif task.download_times > 1:
                self.logger.debug(f'第{task.download_times}次下载：{path}')
            try:
                self.save(task, path)
            except requests.exceptions.RequestException as e:
                raise RequestError(type(e).__module__ + '.' + type(e).__name__)
            finally:
                task.slice = start, path.stat().st_size, end
            if task.slice[2] - task.slice[1] - task.slice[0] > 100:
                raise ContentLengthError(f'{task.slice[0] + task.slice[1]}-{task.slice[2]}')
            raise DownloadSuccess()
        except DownloadException as e:
            error = e
        except Exception as e:
            self.is_stop_all = True
            raise e
        if error.message not in [DownloadSuccess.__name__, StopAllDownloadTasksError.__name__]:
            self.logger.debug(f'下载失败: {error}, {path}')
        return DownloadStatus(error, task)

    def save(self, task: Task, path: Path):
        url = task.url
        headers = task.headers
        start, offset, end = task.slice
        headers['range'] = f"bytes={start + offset}-{end}"
        chunk_size = min(self.chunk_size, end - start - offset)
        start_time = time.time()
        with requests.request('get', url, headers=headers, stream=True, timeout=self.timeout) as resp:
            self.raise_for_status(resp)
            count = 0
            with open(path, 'ab') as f:
                for chunk in resp.iter_content(chunk_size):
                    f.write(chunk)
                    f.flush()
                    count += len(chunk)
                    if count >= end - start - offset:
                        break
                    if time.time() - start_time > self.timeout:
                        if count < end - start - offset:
                            self.logger.debug(f'超时了, count: {count}, {end - start - offset + 1}')
                        break

    def wipe(self):
        self.logger.debug(f'删除缓存文件夹: {self.temp_dir}')
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def merge_files(self, files: typing.List[Path], path: Path) -> bool:
        """
        合并文件到指定路径

        合并的文件第一个直接改名字为指定路径,后余文件追加合并到指定路径后立即删除该文件,减少使用磁盘空间容量
        :param files: 文件列表
        :param path: 存储路径
        :return:
        """
        if path.exists():
            path.unlink()
        if not files:
            return False
        files[0].rename(path)
        with open(path, 'ab') as fa:
            for file in files[1:]:
                with open(file, 'rb') as fr:
                    while True:
                        chunk = fr.read(self.chunk_size)
                        if not chunk:
                            break
                        fa.write(chunk)
                        fa.flush()
                if file.exists():
                    file.unlink()
        return True

    def merge_temp_files(self) -> bool:
        """
        合并所有临时文件到指定路径
        :return:
        """
        if self.output_file.exists():
            self.output_file.unlink()
        self.logger.debug(f'合并文件: {self.temp_dir} -> {self.output_file}')
        is_merge_success = self.merge_files(sorted(self.temp_dir.iterdir()), self.output_file)
        self.logger.debug(f'is_merge_success：{is_merge_success}')
        return is_merge_success

    def start(self):
        """
        开启下载程序

        下载前删除已存在的临时文件夹
        所有任务下载成功后则合并临时文件夹到指定路径
        删除临时文件夹
        :return:
        """
        try:
            self.tasks = self.build_tasks()
            self.logger.debug(f'总任务数：{len(self.tasks)}')
            self.wipe()
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.concurrent()
            # self.logger.error(f'IS_STOP_ALL: {self.is_stop_all}')
            if self.is_all_tasks_confirmed:
                self.merge_temp_files()
        except Exception as e:
            self.logger.exception(f'下载异常, 终止程序运行: {e}')
        self.wipe()
        return self
