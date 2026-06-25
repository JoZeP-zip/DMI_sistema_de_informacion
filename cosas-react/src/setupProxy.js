const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const proxy = createProxyMiddleware({
    target: 'http://localhost:8800',
    changeOrigin: true,
  });

  app.use('/api', proxy);
  app.use('/login-react', proxy);
  app.use('/registro-react', proxy);
  app.use('/admin', proxy);
  app.use('/config', proxy);
  app.use('/citas', proxy);
  app.use('/vehiculo', proxy);
};