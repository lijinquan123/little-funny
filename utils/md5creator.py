# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/10/10 16:05
# @Version     : Python 3.6.4
import argparse
import hashlib
import sys
import traceback
from pathlib import Path


def md5creator(args):
    # 参数处理
    input_file = Path(args.input)
    output_file = args.output
    if output_file is None:
        output_file = input_file.parent / f'{input_file.name}.jm'
    chunk_size = args.chunk_size
    show = args.show
    # 实现
    start = 0
    end = 0
    need_wrap = False
    with open(input_file, 'rb') as fr, open(output_file, 'w', encoding='utf-8') as fw:
        while True:
            # 读取字节并计算MD5
            chunk = fr.read(chunk_size)
            if not chunk:
                break
            end += len(chunk)
            md5sum = hashlib.md5(chunk).hexdigest()
            line = f'{start}-{end - 1},{md5sum}'
            if show:
                print(line)
            # 写入到新文件
            if need_wrap:
                line = f'\n{line}'
            fw.write(line)
            start = end
            need_wrap = True
    print(f'Completed! Output file named "{output_file}"')


def main():
    parser = argparse.ArgumentParser(usage='MD5 Creator', description=' --help')
    parser.add_argument(dest='input', type=str, help='input file')
    parser.add_argument('-o', '--output', required=False, type=str, help='output file', dest='output')
    parser.add_argument('-cs', '--chunk-size', type=int, default=1024, help='chunk size', dest='chunk_size')
    parser.add_argument('-s', '--show', action='store_true', help='show each chunk md5sum', dest='show')
    error_code = 0
    try:
        md5creator(parser.parse_args(sys.argv[1:]))
    except (KeyboardInterrupt, Exception):
        traceback.print_exc()
        error_code = 130
    sys.exit(error_code)
