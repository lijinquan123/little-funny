# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2021/11/8 16:57
# @Version     : Python 3.12.2


class DownloadException(Exception):
    """下载异常"""

    def __init__(self, reason=None):
        self.message = type(self).__name__
        self.reason = reason
        super().__init__(self.__dict__)


class DownloadSuccess(DownloadException):
    """下载成功"""


class RequestError(DownloadException):
    """请求错误"""


class ReachMaxDownloadLimitError(DownloadException):
    """达到最大下载限制错误"""


class StopAllDownloadTasksError(DownloadException):
    """停止所有下载任务错误"""


class ContentLengthError(DownloadException):
    """内容长度错误"""


class MediaMergeError(DownloadException):
    """媒体合并失败"""


class AudioDownloadError(DownloadException):
    """音频下载失败"""


class VideoDownloadError(DownloadException):
    """视频下载失败"""


class NotFoundVideoError(DownloadException):
    """视频不存在错误"""


class UnacceptableTaskError(DownloadException):
    """不被接受的任务错误"""


class M3U8StructError(DownloadException):
    """m3u8结构错误"""


class M3u8StreamError(M3U8StructError):
    """m3u8媒体流错误"""
