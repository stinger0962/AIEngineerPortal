#!/usr/bin/env bash
# Disposable loopback-only integration. Frontend must be built with relative API.
set -euo pipefail
cd "$(dirname "$0")/.."
# Fail before any test mutation when another service already owns a fixture port.
node - <<'JS'
const net=require('node:net');
(async()=>{
 const servers=[];
 try{
  for(const port of [8001,3001,3002]){
   const server=net.createServer(); servers.push(server);
   await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});
  }
 }catch{console.error('QA ports must be unused: 8001, 3001, 3002');process.exitCode=1;}
 finally{for(const server of servers)server.close();}
})();
JS
export PAID_QA_RUN
PAID_QA_RUN=$(node -e "console.log(require('node:crypto').randomUUID())")
export PAID_QA_DIR
PAID_QA_DIR=$(mktemp -d)
chmod 700 "$PAID_QA_DIR"
export PAID_BROWSER_QA=isolated-local-only
export NEXT_PUBLIC_PRODUCT_MODE=paid
backend_pid= frontend_pid= proxy_pid=
cleanup() {
  for pid in "$proxy_pid" "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; fi
  done
  rm -rf "$PAID_QA_DIR"
}
trap cleanup EXIT
# No access log: fixture outbox/cookie values never enter artifacts.
PYTHONPATH="$PWD/backend:$PWD/backend/tests/browser" "${QA_PYTHON:-python}" -m uvicorn paid_server:app --host 127.0.0.1 --port 8001 --no-proxy-headers --no-access-log > /tmp/paid-integration-api.log 2>&1 &
backend_pid=$!
(cd frontend && exec node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3001) > /tmp/paid-integration-web.log 2>&1 &
frontend_pid=$!
node frontend/scripts/paid-integration-proxy.cjs > /tmp/paid-integration-proxy.log 2>&1 &
proxy_pid=$!
for attempt in $(seq 1 60); do
  kill -0 "$backend_pid" "$frontend_pid" "$proxy_pid" 2>/dev/null || { echo 'QA child exited before readiness'; exit 1; }
  if curl --fail --silent http://127.0.0.1:8001/health >/dev/null && curl --fail --silent http://127.0.0.1:3002/account >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8001/health >/dev/null
curl --fail --silent http://127.0.0.1:3002/account >/dev/null
kill -0 "$backend_pid" "$frontend_pid" "$proxy_pid"
# Verify the proxy reaches this exact disposable backend, not a pre-existing app.
curl --fail --silent --dump-header "$PAID_QA_DIR/headers" -H 'X-Paid-Client: 1' http://127.0.0.1:3002/api/v1/account/session >/dev/null
grep -qi "^x-paid-qa-run: $PAID_QA_RUN" "$PAID_QA_DIR/headers"
node frontend/scripts/paid-account-integration-test.cjs
