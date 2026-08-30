#!/bin/sh

[ -n "$CONTAINER_DEBUG" ] && set -x

# This script will be executed as the root user.
if [ $(id -u) -ne 0 ]; then
  echo Init script muts be run by root.
  exit 1
fi

echo Starting container

if command -v systemd-tmpfiles > /dev/null; then
	command systemd-tmpfiles --create
fi

INIT_USERS="root $CONTAINER_USER"
INIT_SCRIPT=init

for user in $INIT_USERS; do
	home=$(getent passwd $(id -u $user) | cut -d: -f6)
	init=$home/$INIT_SCRIPT
	if [ -x $init ]; then
		sudo -u $user $init &
	fi
done

sleep infinity & sleep_pid=$!

on_sigterm() {
	echo Caught SIGTERM, exiting...
	kill -TERM $sleep_pid
	jobs -p | xargs -r kill -TERM
	wait
}

trap "on_sigterm" TERM
wait

