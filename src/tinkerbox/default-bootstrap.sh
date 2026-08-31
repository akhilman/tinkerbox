#!/bin/sh

set -e

[ -n "$CONTAINER_DEBUG" ] && set -x

: "${CONTAINER_USER:?CONTAINER_USER is not set}"

echo -n "Package manager: "
if command -v apk; then
	# apk upgrade
	apk add --no-cache sudo shadow
elif command -v apt-get; then
	export DEBIAN_FRONTEND=noninteractive
	apt-get update
	# apt-get upgrade -y
	apt-get install -y sudo procps less
  rm -rf /var/lib/apt/lists/
elif command -v dnf; then
	# dnf upgrade -y
	dnf install -y sudo procps-ng less
	dnf clean all
elif command -v pacman; then
	pacman --noconfirm -Sy --needed sudo less
	pacman -Scc --noconfirm
elif command -v zypper; then
	zypper install -y sudo which less
	zypper clean --all
else
	echo WARNING: Unsupported package manager! >&2
fi

USER_SHELL=$(getent passwd "$CONTAINER_USER" | cut -d: -f7)
BASH_PATH=$(command -v bash > /dev/null)
if [ "$USER_SHELL" = /bin/sh ] && [ -n "$BASH_PATH" ]; then
	usermod --shell "$BASH_PATH" "$CONTAINER_USER"
fi

install -d -m 0755 /etc/sudoers.d
cat > /etc/sudoers.d/"$CONTAINER_USER" << EOF
$CONTAINER_USER ALL=(ALL:ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/"$CONTAINER_USER"

