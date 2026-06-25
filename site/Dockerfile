FROM nginx:alpine
COPY default.conf /etc/nginx/conf.d/default.conf
COPY *.html style.css /usr/share/nginx/html/
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO /dev/null http://127.0.0.1/ || exit 1
