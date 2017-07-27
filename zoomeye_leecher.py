#!/usr/bin/env python3

import argparse
import asyncio
import functools
import json
import signal
from urllib.parse import urlencode

import aiohttp
import aiohttp.web

REQUEST_URL = 'https://api.zoomeye.org/host/search?{query}&page={page}'
LOGIN_REQUEST = 'https://api.zoomeye.org/user/login'
LOGIN_DATA = {'username': '',
              'password': ''}


class ZoomEyeLeecher:
    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.stopped = True
        self._token = None
        self._counter = None
        self._results = asyncio.Queue()

    async def _worker(self, session, query, pages_limit):
        while not self.stopped and not self._counter > pages_limit:
            async with session.get(REQUEST_URL.format(query=urlencode({'query': query}),
                                                      page=self._counter),
                                   headers={'Authorization': 'JWT ' + self._token}) as resp:
                if resp.status == 200:
                    self._process_result(json.loads(await resp.text()))
                    self._counter += 1
                else:
                    break

    async def leech(self, query, concurrent_connects, pages_limit):
        async with aiohttp.ClientSession(loop=loop) as session:
            if self._token is None:
                login_data = LOGIN_DATA
                login_data['username'] = self.login
                login_data['password'] = self.password
                async with session.post(LOGIN_REQUEST, data=json.dumps(login_data).encode()) as response:
                    assert response.status == 200
                    self._token = json.loads(await response.text())['access_token']
            self._counter = 1
            self.stopped = False
            workers = (self._worker(session, query, pages_limit) for _ in range(concurrent_connects))
            await asyncio.gather(*workers)

    @staticmethod
    def _process_result(result):
        for match in result['matches']:
            print(match)

    def stop(self):
        self.stopped = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Utility for loading results from ZoomEye search engine')
    parser.add_argument('query', help='Query string')
    parser.add_argument('-l', '--login', help='Email', required=True)
    parser.add_argument('-p', '--password', help='Password', required=True)
    parser.add_argument('-c', '--connections', default=32, type=int, help='Concurrent connections count (default: 32)')
    parser.add_argument('-z', '--limit', default=100, type=int, help='Pages limit (default: 100)')
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    leecher = ZoomEyeLeecher(args.login, args.password)
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, functools.partial(leecher.stop))
    loop.run_until_complete(leecher.leech(args.query, args.connections, args.limit))
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.remove_signal_handler(sig)
    loop.close()
