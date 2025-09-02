FROM mcr.microsoft.com/playwright:v1.40.0-jammy

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/New_York
ENV DISPLAY=:1

# Install VNC and desktop components
RUN apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb \
    fluxbox \
    x11vnc \
    supervisor \
    git \
    python3 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN cd /opt && \
    git clone --depth 1 https://github.com/novnc/noVNC.git && \
    cd noVNC && \
    git clone --depth 1 https://github.com/novnc/websockify.git utils/websockify

# Create directories
RUN mkdir -p /var/log/supervisor /app /screenshots

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Playwright browsers are already installed in base image

EXPOSE 5901 7900

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
