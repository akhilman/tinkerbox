#!/bin/sh

set -e

[ -n "$CONTAINER_DEBUG" ] && set -x

: "${CONTAINER_USER:?CONTAINER_USER is not set}"
: "${CONTAINER_HOME:?CONTAINER_HOME is not set}"
: "${CONTAINER_UID:?CONTAINER_UID is not set}"
: "${CONTAINER_GID:?CONTAINER_GID is not set}"


echo Installing basic packages >&2
if command -v apk > /dev/null; then
	apk add --no-cache sudo shadow
elif command -v apt-get > /dev/null; then
	export DEBIAN_FRONTEND=noninteractive
	apt-get update
	apt-get install -y sudo procps less
  rm -rf /var/lib/apt/lists/
elif command -v dnf > /dev/null; then
	dnf install -y sudo procps-ng less
	dnf clean all
elif command -v pacman > /dev/null; then
	pacman --noconfirm -Sy --needed sudo less
	pacman -Scc --noconfirm
elif command -v zypper > /dev/null; then
	zypper install -y sudo which less
	zypper clean --all
else
	echo WARNING: Unsupported package manager! >&2
fi

echo Creating user >&2
if command -v groupadd >/dev/null 2>&1; then
    groupadd --gid "$CONTAINER_GID" "$CONTAINER_USER"
    useradd --create-home \
        --uid "$CONTAINER_UID" \
        --gid "$CONTAINER_GID" \
        --home-dir "$CONTAINER_HOME" \
        "$CONTAINER_USER"
elif command -v addgroup >/dev/null 2>&1; then
    addgroup -g "$CONTAINER_GID" "$CONTAINER_USER"
    adduser -D -u "$CONTAINER_UID" -G "$CONTAINER_USER" \
        -h "$CONTAINER_HOME" "$CONTAINER_USER"
else
    echo "Unsupported user management tools" >&2
    exit 1
fi

echo Setting up shell >&2
USER_SHELL=$(getent passwd "$CONTAINER_USER" | cut -d: -f7)
BASH_PATH=$(command -v bash 2> /dev/null || true)
if [ "$USER_SHELL" = /bin/sh ] && [ -n "$BASH_PATH" ]; then
	usermod --shell "$BASH_PATH" "$CONTAINER_USER"
fi

echo Setting up sudo >&2
install -d -m 0755 /etc/sudoers.d
cat > /etc/sudoers.d/"$CONTAINER_USER" << EOF
$CONTAINER_USER ALL=(ALL:ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/"$CONTAINER_USER"

