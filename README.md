# Tinkerbox

Tinkerbox is a tool to manage interactive podman containers for experiments and development.

It is like toolbox and distrobox, but does not share directories with host.

Work in progress, but useable.

Read code for instructions or call `tinkerbox --help`.


## Home partition

Tinkerbox mounts a persistent volume named `<boxname>-home` to the `/home` directory,
so that the user can recreate the container with same name without losing it's data.


## Share directory with host

You can add any `podman run` flags to `tinkerbox create` after `--` separator:
```bash
tinkerbox create -ialpine my_alpine_box -- --volume=$HOME/my_directory:$HOME/my_directory:rw
```


## Display, DBus and sound

Container can use host's X11 and Wayland servers, DBus, PulseAudio and PipeWire.
See `tinkerbox create --help` for exact flags.


## Shell configuration

You can set your preferred shell by `sudo usermod --shell /path/to/shell $USER` or by editing `/usr/local/bin/tinkerbox-login`.

If you would like to set environment variables the `$HOME/.profile` should do the trick.

## Running daemons

Tinkerbox container runs `$HOME/init` for the root and your user.
Put commands you would like to execute at start to `~/init` and make this file executable.

```bash
host $ tinkerbox create -idebian webdav_server -- -p 127.0.0.1:8000:8000
host $ tinkerbox enter webdav_server
box $ sudo apt install chezdav
box $ echo chezdav --public --no-mdns -p 8000 -P $HOME \& > ~/init
box $ chmod +x ~/init
box $ logout
host $ podman stop webdav_server
host $ podman start webdav_server
host $ firefox http://localhost:8000
```

Edit `/usr/local/sbin/tinkerbox-entrypoit` if you want to change initialization further.


## Supported distributions

 * Alpine
 * Archlinux
 * Debian (default)
 * Fedora
 * OpenSuse
        
Other images may work but not tested.

