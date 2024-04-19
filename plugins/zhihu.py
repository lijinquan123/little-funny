# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2024/4/19 11:09
# @Version     : Python 3.12.2
import logging
from pathlib import Path

from simple_tools import requestx
from simple_tools.commons import fix_filename

from download import Downloader


class 知学堂(object):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://www.zhihu.com",
        "Referer": "https://www.zhihu.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def __init__(self, cookie: str = '', download_dir: Path = Path(r'C:\Download\知乎知学堂')):
        self.session = requestx.Sessionx()
        headers = self.headers.copy()
        if cookie:
            headers['Cookie'] = cookie
        self.session.headers = headers
        self.download_dir = download_dir
        self.logger = logging.getLogger(Path(__file__).stem)

    def 请求课件下载地址(self, file_id: str):
        api = f'https://api.zhihu.com/education/file/{file_id}'
        return self.session.request('get', api).json()['data']['file_url']

    def 获取所有的课程(self):
        api = 'https://www.zhihu.com/api/v4/knowledge_school/purchased/courses?type=ordinary_course&limit=6&offset=0'
        courses = []
        pn = 0
        print('\n正在获取课程...')
        while True:
            raw_courses = (body := self.session.request('get', api).json())['data']
            pn += len(raw_courses)
            for course in raw_courses:
                courses.append({
                    'id': course['content']['id'],
                    'name': course['content']['title'],
                    'author': course['author']['url'],
                })
            totals = body['paging']['totals']
            is_end = body['paging']['is_end']
            print(f'已解析课程 {pn}/{totals}/{len(courses)}, is_end: {is_end}')
            if is_end:
                print()
                break
            api = body['paging']['next']
        return courses

    @staticmethod
    def 解析课件视频链接(lessons: list):
        videos = []
        for lesson in lessons:
            serial_number_txt = lesson['index']['serial_number_txt']
            title = lesson['title']
            if (data := lesson['resource']['data']) and (playlist := data.get('playlist') or {}):
                playlist = sorted(playlist.values(), key=lambda x: x['width'], reverse=True)
                url = playlist[0]['url']
                suffix = playlist[0]['format']
                videos.append({
                    'name': f'{serial_number_txt}_{title}.{suffix}',
                    'url': url,
                })
        return videos

    @staticmethod
    def 解析课件编号(lessons: list):
        files = []
        for lesson in lessons:
            for file in lesson.get('file_list') or []:
                name = file['file_name']
                # file_type: 4: PPT
                files.append({
                    'name': name,
                    'file_id': file['file_id'],
                })
        return files

    def 获取课程的所有课件(self, course_id: str, course_name: str):
        api = f'https://api.zhihu.com/education/training/{course_id}/video_page/catalog?limit=10&offset=0'
        lessons = []
        files = []
        pn = 0
        print(f'\n正在获取 <{course_name}> 课件...')
        while True:
            raw_lessons = (body := self.session.request('get', api).json()['data'])['data']
            pn += len(raw_lessons)
            if ls := self.解析课件视频链接(raw_lessons):
                lessons.extend(ls)
            if fs := self.解析课件编号(raw_lessons):
                files.extend(fs)
            totals = body['paging']['totals']
            is_end = body['paging']['is_end']
            print(f'已解析课件 <{course_name}> {pn}/{totals}/{len(lessons)}, is_end: {is_end}')
            if is_end:
                print()
                break
            api = body['paging']['next']
        return {
            'lessons': lessons,
            'files': files,
        }

    def 下载媒资(self, url, filepath: Path):
        filepath.parent.mkdir(exist_ok=True, parents=True)
        download = Downloader(
            url,
            self.headers,
            Path(r'C:\Download\temp'),
            filepath,
            self.logger,
            threads_num=5,
            timeout=60,
        ).start()
        return download.is_all_tasks_confirmed

    def 下载所有课程(self):
        # 下载视频
        courses = self.获取所有的课程()
        for course in courses:
            videos = self.获取课程的所有课件(course['id'], course_name := course['name'])
            for index, video in enumerate(files := videos['files'], start=1):
                file_id = video['file_id']
                name = fix_filename(video['name'])
                print(f'\n正在下载 {index}/{len(files)} <{course_name}> {name}')
                if (filepath := self.download_dir / course_name / name).exists():
                    print(f'已存在 {index}/{len(files)} <{course_name}> {name}')
                    continue
                url = self.请求课件下载地址(file_id)
                print(f'下载状态: {self.下载媒资(url, filepath)}, {index}/{len(files)} <{course_name}> {name}')

            for index, video in enumerate(lessons := videos['lessons'], start=1):
                url = video['url']
                name = fix_filename(video['name'])
                print(f'\n正在下载 {index}/{len(lessons)} <{course_name}> {name}')
                if (filepath := self.download_dir / course_name / name).exists():
                    print(f'已存在 {index}/{len(lessons)} <{course_name}> {name}')
                    continue
                print(f'下载状态: {self.下载媒资(url, filepath)}, {index}/{len(lessons)} <{course_name}> {name}')


if __name__ == '__main__':
    ck = ""
    zxt = 知学堂(ck)
    zxt.下载所有课程()
