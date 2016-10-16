#!/usr/bin/env python3

""" Note: python 3.5 or higher """

import aiohttp
import asyncio
import json
from urllib.parse import urlencode
from pprint import pprint
import argparse

REQUEST_URL = 'https://api.zoomeye.org/host/search?{query}&page={page}'
LOGIN_REQUEST = 'https://api.zoomeye.org/user/login'
LOGIN_DATA = {'username': '',
              'password': ''}


async def fetch_result(session, queue, token):
    while not queue.empty():
        url = await queue.get()
        async with session.get(url, headers={'Authorization': 'JWT ' + token}) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                break


async def main(loop, login, password, query, concurrent_connects):
    async with aiohttp.ClientSession(loop=loop) as session:
        login_data = LOGIN_DATA
        login_data['username'] = login
        login_data['password'] = password
        async with session.post(LOGIN_REQUEST, data=json.dumps(login_data).encode()) as response:
            assert response.status == 200
            token = json.loads(await response.text())['access_token']
            queue = asyncio.Queue()
            for i in range(1, 1000):
                request_url = REQUEST_URL.format(query=urlencode({'query': query}), page=i)
                queue.put_nowait(request_url)
            tasks = []
            for _ in range(concurrent_connects):
                tasks.append(asyncio.ensure_future(fetch_result(session, queue, token)))
            results = []
            raw_results = await asyncio.gather(*tasks)
            for r in raw_results:
                if r is not None:
                    results.extend(json.loads(r)['matches'])
            pprint(results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Utility for loading results from ZoomEye search engine')
    parser.add_argument('query', help='Query string')
    parser.add_argument('-l', '--login', help='Email', required=True)
    parser.add_argument('-p', '--password', help='Password', required=True)
    parser.add_argument('-c', '--connections', default=32, type=int, help='Concurrent connections count (default: 32)')
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop, args.login, args.password, args.query, args.connections))
    loop.close()
