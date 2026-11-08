"""StagVPN free-node prober: fetch app-data-new, probe liveness, emit ovpn files + pool import list."""
import base64, json, socket, sys, urllib.request

API = 'https://server.stagvpn.com/api/v1/app-data-new'


def fetch_nodes():
    req = urllib.request.Request(API, headers={'User-Agent': 'okhttp/4.11.0'})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    return [s for s in d.get('ikev2servers', []) if s.get('is_free') == 1 and s.get('status') == 1]


def probe(node):
    ip = node['ip']
    alive = {'icmp': False, 'udp1194': None}
    try:
        socket.setdefaulttimeout(6)
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).connect((ip, 1194))
        alive['udp1194'] = 'udp-unreachable-check-n/a'  # UDP connect always succeeds; real check needs OVPN handshake
    except OSError:
        alive['udp1194'] = 'unreachable'
    return alive


def write_ovpn(node, outdir):
    path = f'{outdir}/stag_{node["id"]}.ovpn'
    open(path, 'w', encoding='utf-8', newline='').write(node['opnconfig'].replace('\r\n', '\n'))
    with open(f'{outdir}/stag_{node["id"]}_cred.txt', 'w') as f:
        f.write(node['ikev2_user_name'] + '\n' + node['ikev2_user_password'] + '\n')
    return path


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else '.'
    nodes = fetch_nodes()
    print(f'free nodes: {len(nodes)}')
    for n in nodes:
        info = probe(n)
        print(n['id'], n['server_name'], n['ip'], info)
        print('  ovpn ->', write_ovpn(n, outdir))


if __name__ == '__main__':
    main()
