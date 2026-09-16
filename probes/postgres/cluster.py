"""Private Unix-socket cluster, including cleanup if startup is interrupted."""
import json
import os
import pathlib
import signal
import subprocess
import tempfile
import time

PG = pathlib.Path('/usr/lib/postgresql/18/bin')


class Cluster:
    def __enter__(self):
        for name in ('initdb', 'pg_ctl', 'psql'):
            if not (PG / name).is_file():
                raise RuntimeError(f'required fixture tool missing: {PG / name}')
        for old in pathlib.Path(tempfile.gettempdir()).glob('rnx-pg-contract-*'):
            pidfile = old/'data/postmaster.pid'
            if not pidfile.exists():
                continue
            pid = int(pidfile.read_text().splitlines()[0])
            owner = old/'fixture-owner'
            owner_alive = owner.exists() and pathlib.Path(f'/proc/{owner.read_text().strip()}').exists()
            if pathlib.Path(f'/proc/{pid}').exists() and not owner_alive:
                raise RuntimeError(f'previous fixture postmaster still alive: {pid} at {old}')
        self.temp = tempfile.TemporaryDirectory(prefix='rnx-pg-contract-')
        self.root = pathlib.Path(self.temp.name)
        self.root.chmod(0o700)
        (self.root/'fixture-owner').write_text(str(os.getpid()))
        self.data = self.root / 'data'
        self.postmaster = None
        self.previous = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self.interrupted)
        self.events = []
        try:
            self.command(['initdb', '-D', self.data, '--auth=trust', '--no-locale', '--encoding=UTF8'])
            (self.data / 'pg_hba.conf').write_text('local all locked scram-sha-256\nlocal all all trust\n')
            self.command(['pg_ctl', '-D', self.data, '-l', self.root/'server.log', '-o',
                          f"-c listen_addresses='' -c unix_socket_directories='{self.root}' -c timezone=UTC", '-w', 'start'])
            self.postmaster = int((self.data/'postmaster.pid').read_text().splitlines()[0])
            self.sql("CREATE ROLE locked LOGIN PASSWORD 'fixture-correct-password'")
            return self
        except BaseException:
            self.close()
            raise

    def interrupted(self, *_):
        raise KeyboardInterrupt('fixture interrupted')

    def command(self, args, check=True):
        proc = subprocess.Popen([str(PG/args[0]), *map(str, args[1:])], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True,
                                env={k:v for k,v in os.environ.items() if not k.startswith('PG')})
        event = dict(stage=args[0], pid=proc.pid, directory=str(self.root), data=str(self.data))
        self.events.append(event)
        if os.environ.get('RNX_PG_STAGE_FILE'):
            pathlib.Path(os.environ['RNX_PG_STAGE_FILE']).write_text(json.dumps(event))
        try:
            stdout, stderr = proc.communicate(timeout=20)
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
            raise
        result = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
        if check and result.returncode:
            raise RuntimeError(f'{args[0]} failed: {stderr}\n{stdout}')
        return result

    def sql(self, sql, check=True):
        return self.command(['psql', '-XAt', '-h', self.root, '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', sql], check)

    @property
    def url(self):
        return f'postgresql:///postgres?host={self.root}&application_name=rnx-pg-fixture'

    def activity(self):
        return self.sql("SELECT pid, state, query FROM pg_stat_activity WHERE application_name='rnx-pg-fixture'").stdout.strip()

    def wait_idle(self, timeout=5):
        deadline = time.monotonic() + timeout
        while self.activity():
            if time.monotonic() >= deadline:
                raise AssertionError(self.activity())
            time.sleep(.01)

    def close(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            pidfile = self.data/'postmaster.pid'
            if pidfile.exists():
                self.postmaster = int(pidfile.read_text().splitlines()[0])
                self.command(['pg_ctl', '-D', self.data, 'stop', '-m', 'fast', '-w'])
            if self.postmaster:
                deadline = time.monotonic() + 5
                while pathlib.Path(f'/proc/{self.postmaster}').exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                assert not pathlib.Path(f'/proc/{self.postmaster}').exists(), self.postmaster
            self.temp.cleanup()
            assert not self.root.exists()
        finally:
            signal.signal(signal.SIGINT, self.previous)

    def __exit__(self, *_):
        self.close()
