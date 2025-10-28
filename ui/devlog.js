const http = require('http');

const server = http.createServer((req, res) => {
  // CORS + preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }

  if (req.method !== 'POST' || req.url !== '/devlog') {
    res.writeHead(404);
    return res.end('Not found');
  }

  let body = '';
  req.on('data', chunk => (body += chunk));
  req.on('end', () => {
    try {
      const { level = 'log', args = [] } = JSON.parse(body || '{}');
      const ts = new Date().toISOString();
      const out = Array.isArray(args) ? args : [args];
      (console[level] || console.log)(`[${ts}]`, ...out);
    } catch (e) {
      console.error('devlog parse error:', e);
    }
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*' });
    res.end();
  });
});

const PORT = 3001;
server.listen(PORT, '127.0.0.1', () =>
  console.log(`devlog listening on http://127.0.0.1:${PORT}/devlog`)
);

