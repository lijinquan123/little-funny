# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2024/5/15 15:55
# @Version     : Python 3.12.2
import json
import time
from urllib.parse import urlparse

import xmltodict

FAKE_MAP = {
    '0': 'taobao.com',
    '1': 'youtube.com',
    '2': 'google.com',
    '3': 'facebook.com',
}


def converter(xml_content: str):
    # 兼容 XML 标签
    xml_content = xml_content.strip()
    if xml_content.startswith('<?xml'):
        xml_content = '\n'.join(xml_content.split('\n')[1:])

    # 将 XML 转换为字典
    target = {
        'version': time.strftime('%Y/%m/%d %H:%M:%S'),
        'resolves': [],
        'groups': [],
    }
    resources = xmltodict.parse(xml_content)['resources']
    ips = resources['pri-ip-list']['item']
    for array_name, arrays in resources['domain-group'].items():
        for array in arrays:
            tag = array['@name']
            items = []
            prefixes = {}
            if isinstance(array['item'], str):
                array['item'] = [array['item']]
            for index, item in enumerate(array['item']):
                if isinstance(item, dict):
                    item = item['#text']
                domain = urlparse(item).hostname
                if domain is None:
                    domain = item
                items.append({
                    "domain": domain,
                    "type": "pub"
                })
                prefix = domain.split('.')[0]
                prefixes[prefix] = index
            for index, prefix in enumerate(prefixes, start=1):
                if not prefix:
                    continue
                num = prefix[-1]
                if not num.isdigit():
                    num = '0'
                if num in FAKE_MAP:
                    fake_domain = prefix + '.' + FAKE_MAP[num]
                    # 添加到groups中
                    items.insert(prefixes[prefix] + index, {
                        "domain": fake_domain,
                        "type": "pri"
                    })
                    # 添加到resolves中
                    target['resolves'].append({
                        "domain": fake_domain,
                        "type": "A",
                        "list": ips
                    })
            target['groups'].append(
                {
                    'tag': tag,
                    'list': items
                }
            )
    return json.dumps(target, indent=2, ensure_ascii=False)


def check(content: str):
    def check_str(s):
        if not s.strip():
            raise Exception(f'{k} contains empty\n{json_item}')

    def check_ip(s):
        ip = s.strip().split('.')
        if len(ip) != 4:
            raise Exception(f'{s} is not ip\n{json_item}')
        for p in ip:
            if not p.isdigit():
                raise Exception(f'{s} is not ip\n{json_item}')
            p = int(p)
            if p > 255 or p < 0:
                raise Exception(f'{s} is not ip\n{json_item}')

    try:
        data = json.loads(content)
        resolves = data['resolves']
        fake_domains = set()
        for item in resolves:
            # 检查域名是否有空
            json_item = json.dumps(item, ensure_ascii=False, indent=2)
            for k, v in item.items():
                if k in ['domain', 'type']:
                    check_str(v)
                elif k in ['list']:
                    if not v:
                        raise Exception(f'{k} contains empty\n{json_item} ')
                    for i in v:
                        check_str(i)
                        check_ip(i)

            # 找出所有假域名
            if item['type'] == 'A':
                fake_domains.add(item['domain'])

        # 找出groups填充的假域名
        groups = data['groups']
        for group in groups:
            for item in group['list']:
                domain = item['domain']
                if item['type'] == 'pri' and domain not in fake_domains:
                    index = group['list'].index(item)
                    group['list'] = group['list'][index - 2:index + 1]
                    json_group = json.dumps(group, ensure_ascii=False, indent=2)
                    raise Exception(f'{domain} is not in fake domain\n{json_group}')
    except Exception as e:
        print(e)
