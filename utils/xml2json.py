# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2024/5/15 15:55
# @Version     : Python 3.12.2
# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/11/14 14:56
# @Version     : Python 3.6.4
from urllib.parse import urlparse

import xmltodict


def converter(xml_content: str):
    # 兼容 XML 标签
    xml_content = xml_content.strip()
    if xml_content.startswith('<?xml'):
        xml_content = '\n'.join(xml_content.split('\n')[1:])

    # 将 XML 转换为字典
    target = {
        'groups': []
    }
    for array_name, arrays in xmltodict.parse(xml_content)['resources'].items():
        for array in arrays:
            tag = array['@name']
            # if tag != 'auth_base_url':
            #     continue
            items = []
            for item in array['item']:
                items.append({
                    "domain": urlparse(item).hostname,
                    "type": "pub"
                })
            target['groups'].append(
                {
                    'tag': tag,
                    'list': items
                }
            )
    return target
