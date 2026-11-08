// Same-origin loopback reverse proxy for local QA only; no deployed configuration.
const http = require('node:http');
http.createServer((request, response) => {
  const upstream = http.request({hostname:'127.0.0.1',port:request.url.startsWith('/api/v1/')?8001:3001,
    path:request.url,method:request.method,headers:request.headers}, result => {
    response.writeHead(result.statusCode,result.headers); result.pipe(response);
  });
  upstream.on('error',()=>{response.writeHead(502);response.end('QA upstream unavailable');});
  request.pipe(upstream);
}).listen(3002,'127.0.0.1');
