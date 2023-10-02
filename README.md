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

You may add any `podman run` flags to `tinkerbox create` after `--` separator:
```bash
tinkerbox create -Ialpine my_alpine_box -- --volume=$HOME/my_directory:$HOME/my_directory:rw
```


## Display, DBus and sound

Container can use host's X11 and Wayland servers, DBus and PulseAudio.
See `tinkerbox create --help` for exact flags.


## Supported distributions

 * Alpine
 * Archlinux
 * Debian (default)
 * Fedora
 * OpenSuse
