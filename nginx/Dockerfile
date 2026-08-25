FROM nginx:1.27-alpine

RUN apk add --no-cache openssl curl \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx.prod.conf /etc/nginx/nginx.conf.template
COPY html/404.html html/50x.html /usr/share/nginx/html/
COPY docker-entrypoint.d/40-ssl-and-config.sh /docker-entrypoint.d/40-ssl-and-config.sh
RUN chmod +x /docker-entrypoint.d/40-ssl-and-config.sh

EXPOSE 80 443

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fk https://127.0.0.1/health || curl -fs http://127.0.0.1/health || exit 1
