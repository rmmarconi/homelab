# Shlink — encurtador de links (short.x7velo.com), atrás do proxy da Cloudflare.
# A porta 80 cai no default_server do mediacenter.conf (ACME + redirect para HTTPS).
server {
    listen 443 ssl http2;
    server_name short.x7velo.com;

    ssl_certificate     /etc/letsencrypt/live/short.x7velo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/short.x7velo.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;

    # IP real do visitante (estatísticas e geolocalização do Shlink)
    include snippets/cloudflare-realip.conf;

    root /opt/shlink/public;
    index index.php;
    charset utf-8;

    location / {
        try_files $uri $uri/ /index.php$is_args$args;
    }

    location ~ \.php$ {
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass unix:/run/php/shlink.sock;
        fastcgi_index index.php;
        include fastcgi.conf;
        # Só o REMOTE_ADDR (já corrigido pelo real_ip) conta: descarta cabeçalhos forjáveis
        fastcgi_param HTTP_X_FORWARDED_FOR "";
        fastcgi_param HTTP_X_REAL_IP "";
        fastcgi_param HTTP_CF_CONNECTING_IP "";
        fastcgi_param HTTPS on;
    }

    location ~ /\. { deny all; }

    access_log /var/log/nginx/shlink.access.log;
    error_log  /var/log/nginx/shlink.error.log;
}
