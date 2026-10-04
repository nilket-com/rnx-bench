"""Probe-only readiness: gunicorn workers have loaded the app, before accepting traffic."""
import json,os

def post_worker_init(worker):
	os.write(2,(json.dumps({'event':'worker_ready','pid':worker.pid})+'\n').encode())
