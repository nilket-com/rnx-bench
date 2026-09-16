#!/usr/bin/env python3
"""Prove that socket-backed stdin is outside the server's cleanup ownership."""
import argparse, json, pathlib, socket, subprocess
from wire import Server, status

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args()
    rows=[]
    for mode in ('null','pipe','socket'):
        peers=[]
        if mode=='null':stdin=subprocess.DEVNULL
        elif mode=='pipe':stdin=subprocess.PIPE
        else:
            stdin,peer=socket.socketpair();peers=[stdin,peer]
        server=None
        try:
            server=Server(args.output/mode,stdin=stdin)
            assert status(server.raw(server.request(data=b'ok')))==200
        finally:
            try:
                if server is not None:server.close()
            finally:
                if server is not None and server.p.stdin:server.p.stdin.close()
                for peer in peers:peer.close()
        events=server.events();baseline=next(e for e in events if e['event']=='socket_baseline')
        closed=next(e for e in events if e['event']=='closed')
        assert closed['inherited_sockets']==(1 if mode=='socket' else 0)
        assert closed['sockets']==0
        rows.append({'mode':mode,'baseline':baseline,'closed':closed})
    (args.output/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Three stdin modes passed.')
if __name__=='__main__':main()
