# Tinkerbox

Tinkerbox is a tool to manage interactive podman containers for experements and development.

It is like toolbox and distrobox, but does not share directories with host.

Work in progress, but useable.

Read code for instructions or call `tinkerbox --help`.


## Persistent volumes

Tinkerbox mounts two persistent volumes for each container:

 * `<boxname>-home` to `/home`
 * `tinkerbox-shared` to `/mnt/shared`

The last one is shared between containers and intended to be used to store different kind of caches like `~/.cache/pip`.

Make a symbolic link for your cache directory to this volume.
```bash
mkdir -p /mnt/shared/cache
for dir in $HOME/{.cargo,.rustup,.cache/{pip,deno}}; do
    mkdir -p $(dirname $dir)
    ln -s /mnt/shared/cache/$(basename $dir) $dir 
done
```


## Share directory with host

You can add any `podman run` flags to `tinkerbox create` after `--` separator:
```bash
tinkerbox create -Ialpine my_alpine_box -- --volume=$HOME/my_directory:$HOME/my_directory:rw
```


## Display, DBus and sound

Container can use host's X11 and Wayland servers, DBus, PulseAudio and PipeWire.
See `tinkerbox create --help` for exact flags.


## Shell configuration

You can set your preferred shell by `sudo usermod --shell /path/to/shell $USER` or by editing `/usr/local/bin/tinkerbox-login`.

If you would like to set environment variables the `$HOME/.profile` should do the trick.

## Running daemons

Tinkerbox container runs `/usr/local/bin/tinkerbox-init` as entry point by your regular user (**not root**).
Put commands you would like to execute at start there.

```bash
host $ tinkerbox create -Idebian http_server -- -p 129.0.0.1:8000:8000
host $ tinkerbox enter http_server
box $ sudo apt install python3
box $ echo python3 -m http.server -d $HOME 8000 > /usr/local/bin/tinkerbox-init
box $ logout
host $ podman restart http_server
host $ firefox http://localhost:8000
```


## Supported distributions

 * Alpine
 * Archlinux
 * Debian (default)
 * Fedora
 * OpenSuse
