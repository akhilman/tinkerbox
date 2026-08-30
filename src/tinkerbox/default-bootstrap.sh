#!/bin/sh

[ -n "$CONTAINER_DEBUG" ] && set -x

echo -n "Package manager: "
if command -v apk; then
	apk upgrade
	apk add sudo shadow
elif command -v apt-get; then
	apt-get update
	apt-get upgrade -y
	apt-get install -y sudo procps less
elif command -v dnf; then
	dnf upgrade -y
	dnf install -y sudo procps-ng less
elif command -v pacman; then
	pacman --noconfirm -Suy --needed sudo less
elif command -v zypper; then
	zypper update -y
	zypper install -y sudo which less
else
	echo WARNING: Unsupported distro!
fi

IMAGE_USER_NAME=$(id -nu $CONTAINER_UID)
IMAGE_USER_HOME=$(getent passwd $CONTAINER_UID | cut -d: -f6)
USER_HOME=$CONTAINER_HOME
if [ "$IMAGE_USER_NAME" != "$CONTAINER_USER" ]; then
    usermod --login $CONTAINER_USER $IMAGE_USER_NAME
fi
if [ "$IMAGE_USER_HOME" != "$USER_HOME" ] && [ -d $IMAGE_USER_HOME ]; then
    mv "$IMAGE_USER_HOME" "$USER_HOME"
    usermod --home $USER_HOME $CONTAINER_USER
fi
mkdir -p $USER_HOME
chown $CONTAINER_USER: $USER_HOME
chmod 700 $USER_HOME

USER_SHELL=$(getent passwd $CONTAINER_UID | cut -d: -f7)
BASH_PATH=$(command -v bash)
if [ $USER_SHELL = /bin/sh ] && [ -n "$BASH_PATH" ]; then
	usermod --shell $BASH_PATH $CONTAINER_USER
fi

mkdir -p /etc/sudoers.d
cat > /etc/sudoers.d/$CONTAINER_USER << EOF
$CONTAINER_USER ALL=(ALL:ALL) NOPASSWD: ALL
EOF

