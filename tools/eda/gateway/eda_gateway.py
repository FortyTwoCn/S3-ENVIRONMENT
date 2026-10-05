"""Local HTTP client for the official EasyEDA Run API Gateway bridge."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.request

READ_STATE = (
    'const project = await eda.dmt_Project.getCurrentProjectInfo(); '
    'const document = await eda.dmt_SelectControl.getCurrentDocumentInfo(); '
    'return {version: eda.sys_Environment.getEditorCurrentVersion(), '
    'isClient: eda.sys_Environment.isClient(), '
    'isJLCEDAPro: eda.sys_Environment.isJLCEDAProEdition(), '
    'isHalfOfflineMode: eda.sys_Environment.isHalfOfflineMode(), '
    'project: project ? {uuid: project.uuid, name: project.name, friendlyName: project.friendlyName} : null, '
    'document: document ? {uuid: document.uuid, documentType: document.documentType, tabId: document.tabId} : null};'
)


def request(port, endpoint, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'http://127.0.0.1:{port}/{endpoint}', data=data,
        headers={'Content-Type': 'application/json'} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=35 if data else 1) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode('utf-8')) from error


def find_bridge():
    for port in range(49620, 49630):
        try:
            health = request(port, 'health')
            if health.get('service') == 'easyeda-bridge':
                return port, health
        except (OSError, ValueError, RuntimeError):
            pass
    raise RuntimeError('Bridge not running; run Start-Bridge.ps1 first')


def execute(code, window_id=None):
    port, health = find_bridge()
    if not health.get('edaConnected'):
        raise RuntimeError('No EDA window connected; check extension permissions and reconnect')
    if health.get('edaWindowCount', 0) > 1 and not window_id:
        raise RuntimeError('Multiple EDA windows connected; provide --window-id')
    payload = {'code': code}
    if window_id:
        payload['windowId'] = window_id
    result = request(port, 'execute', payload)
    if result.get('success') is not True:
        raise RuntimeError(f'EDA execution failed: {result}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'read-state', 'execute'])
    parser.add_argument('--code-file', type=Path)
    parser.add_argument('--window-id')
    args = parser.parse_args()
    if args.action == 'status':
        port, health = find_bridge()
        result = {'port': port, 'health': health, 'windows': request(port, 'eda-windows')}
    elif args.action == 'read-state':
        result = execute(READ_STATE, args.window_id)
    else:
        if not args.code_file:
            parser.error('execute requires --code-file containing an async JavaScript function body')
        result = execute(args.code_file.read_text(encoding='utf-8'), args.window_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
