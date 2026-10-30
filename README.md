# Tinkerbox

Tinkerbox is a tool for managing interactive [Podman](https://podman.io/) containers intended for experiments and development.

It is similar to [Toolbox](https://containertoolbx.org/) and [Distrobox](https://distrobox.it/), but does **not** share the host’s home directory or other filesystem paths by default. Containers stay isolated; persistence and host integration are controlled explicitly through profiles and CLI options.

**Status:** Work in progress / alpha, but usable.

## Features

- Isolated development environments (no automatic host directory sharing)
- Profile-based configuration (TOML/JSON) for images and containers
- Image building from profiles with ordered `add` / `run` steps grouped by user
- Flexible mounts, volumes, devices, networks, port publishing, and file copying
- Optional host service passthrough (X11, Wayland, DBus, PulseAudio, PipeWire, GPU)
- Python ≥ 3.13 implementation

The default profiles provide a ready-to-use experience (supported distros, persistent `/home` volume, init scripts, etc.). You can write your own profiles with completely different behaviour.

## Requirements

- Linux (primary target; Podman required)
- [Podman](https://podman.io/)
- Python ≥ 3.13

## Installation

```bash
# From the repository root (refactor-python branch)
pip install .
# or, for development
pip install -e .
```

The `tinkerbox` command becomes available after installation.

## Quick start

Using the built-in default profiles:

```bash
# Build a default image (Debian-based by default)
tinkerbox image build my-debian

# Create a container from it
tinkerbox container create my-debian mybox

# Enter the container
tinkerbox container enter mybox

# Or create and enter in one step
tinkerbox container create --enter my-debian mybox
```

List resources:

```bash
tinkerbox image list
tinkerbox container list
```

## Command overview

```
tinkerbox [--debug] <entity> <command> ...
```

### Image commands (`tinkerbox image` / `tinkerbox im`)

| Command | Aliases | Description |
|---------|---------|-------------|
| `build` | `bd` | Build an image from a profile |
| `list` | `ls` | List images |
| `remove` | `rm` | Remove one or more images |
| `profile` | `pr` | Manage image profiles (`list`, `cat`, `extract`) |

### Container commands (`tinkerbox container` / `tinkerbox ct`)

| Command | Aliases | Description |
|---------|---------|-------------|
| `create` | `cr` | Create a container from an image |
| `enter` | `en` | Enter a running container |
| `list` | `ls` | List containers |
| `remove` | `rm` | Remove one or more containers |
| `start` | `st` | Start containers |
| `stop` | `sp` | Stop containers |
| `profile` | `pr` | Manage container profiles (`list`, `cat`, `extract`) |

Run any command with `--help` for full options (e.g. `tinkerbox container create --help`).

## Profiles

Configuration is driven by **profiles** (TOML or JSON files). Profiles can extend others (`extends = ["default"]`). CLI flags can also supply or override profile data.

### Where profiles are stored

Profiles are looked up in this order:

1. User config  
   - `~/.config/tinkerbox/image/` — image profiles  
   - `~/.config/tinkerbox/container/` — container profiles  
   (or under `$XDG_CONFIG_HOME/tinkerbox/` if set)

2. System config  
   - `/etc/tinkerbox/image/`  
   - `/etc/tinkerbox/container/`

3. Built-in defaults packaged with the application (`default`)

Files may be named `name.toml` or `name.json`.

Inspect profiles:

```bash
tinkerbox image profile list
tinkerbox image profile cat [--flatten] default
tinkerbox image profile extract <image>

tinkerbox container profile list
tinkerbox container profile cat [--flatten] default
tinkerbox container profile extract <container>
```

## Variable substitution

Profile fields support variable substitution using the `@{…}` syntax
(implemented by `tinkerbox.utils.substitute` and the `variables()` /
`substitute()` methods on image, container, and base profiles).

Substitution is applied after a profile is flattened (all `extends` merged)
and before the image is built or the container is created.

### Syntax

| Form | Meaning |
|------|---------|
| `@{VAR}` | Required. Raises `ValueError` if the variable is undefined. |
| `@{VAR?}` | Optional. Expands to an empty string if undefined. |
| `@{VAR:-default}` | Expands to `default` if the variable is undefined or empty. |

- Variable names must start with a letter or underscore and may contain only
  letters, digits, and underscores (`[A-Za-z_][A-Za-z0-9_]*`).
- Values may themselves contain `@{…}` references; they are expanded
  recursively.
- A variable that expands to a value that refers back to itself raises
  `RecursionError`.
- The separator logic used elsewhere (e.g. in mount/volume specs) treats
  text inside `@{…}` as opaque, so colons inside substitutions are safe.

### Available variables

**Always available (base profile)**

| Variable | Source |
|----------|--------|
| Every host environment variable | `os.environ` (e.g. `@{HOME}`, `@{PATH}`, `@{USER}`) |
| `PROFILE_NAME` | Name of the profile being loaded (if set) |
| `TZ` | Host timezone from `timedatectl` or `/etc/localtime` (if detectable) |

**Image profiles** (in addition to the base set)

| Variable | Source |
|----------|--------|
| `UID` | Host user ID (`os.getuid()`) |
| `GID` | Host group ID (`os.getgid()`) |
| `CONTAINER_USER` | Profile `user` field, or the host username if unset |
| `CONTAINER_HOME` | Profile `home` field, or the host home directory if unset |
| `IMAGE_FROM` | Profile `from` field (base image), if set |
| `IMAGE_NAME` | Profile `name` field, if set |

**Container profiles** (in addition to the base set)

| Variable | Source |
|----------|--------|
| `CONTAINER_NAME` | Container name, if set |
| `CONTAINER_IMAGE` | Image name/reference, if set |

When a **container** is created, the variable map is the merge of the image
profile’s variables and the container profile’s variables
(`{**image_vars, **container_vars}`). Consequently container creation can also
use `UID`, `GID`, `CONTAINER_USER`, `CONTAINER_HOME`, and the other image
variables.

### What is substituted

- **Image profiles:** `from`, `name`, `user`, `home`, every `environment`
  value, every `add` / `run` field that supports it, `entrypoint`, `cmd`.
- **Container profiles:** `name`, `image`, every `environment` value,
  devices, mounts, volumes, copy/exec entries, and `enter_command`.

### Examples

Default image profile (excerpt):

```toml
[environment]
CONTAINER_UID  = "@{UID}"
CONTAINER_GID  = "@{GID}"
CONTAINER_USER = "@{CONTAINER_USER}"
CONTAINER_HOME = "@{CONTAINER_HOME}"
```

Default container profile (excerpt):

```toml
[environment]
HOME = "@{CONTAINER_HOME}"
USER = "@{CONTAINER_USER}"
TZ   = "@{TZ?}"          # empty if timezone cannot be detected

[[volumes]]
target = "/home"
source = "@{CONTAINER_NAME}-home"
```

Custom examples:

```toml
# Optional host path with a fallback
[[volumes]]
source = "@{PROJECTS_DIR:-/tmp/projects}"
target = "/work"

# Build an image name from the profile name
name = "myapp-@{PROFILE_NAME}"

# Nested / recursive expansion
# If EXTRA=foo and PATH already contains @{EXTRA}/bin …
environment = { PATH = "@{PATH}:@{HOME}/.local/bin" }
```

Required variable that is missing:

```toml
# Raises ValueError: variable 'MISSING' is not defined
source = "@{MISSING}"
```


### Default profiles (what you get out of the box)

The built-in **default image** and **default container** profiles provide:

- Supported base distributions: Alpine, Arch Linux, Debian (default), Fedora, openSUSE, Ubuntu  
  (other images using `apk`, `apt`, `dnf`, `pacman` or `zypper` may work but are untested)
- A matching host user created inside the image
- Persistent named volume `<container-name>-home` mounted at `/home`
- tmpfs mounts for `/tmp` and `/run`
- Passing of common environment variables (`TERM`, `XDG_*`, …)
- Execution of executable `~/init` scripts for both `root` and the container user on start

These behaviours are **not** hard-coded into Tinkerbox itself. They come from the default profiles. You can write your own profiles that omit the home volume, use a different base image, skip init scripts, or implement any other layout you need.

Creating the user is profile's responsibility. The default profile does this with the `bootstrap.sh` script.

### Image build order: grouping of `add` and `run` by user

When building an image, Tinkerbox groups `add` and `run` steps by the target user and emits them in a deliberate order (see `src/tinkerbox/image.py`):

1. **Root phase**  
   - `ENV`  
   - `USER root`
   - `ADD` instructions whose `chmod` is `root`, `0` or empty
   - `RUN` instructions for `root`, `0` on not specified user

2. **Intermediate users** (if any)  
   - `USER <intermediate-user>`
   - `ADD` instructions owned by the intermediate user  
   - `RUN` instructions for the intermediate user

3. **Final user phase**  
   - `USER <final-user>` and `WORKDIR`  
   - `ADD` instructions owned by the final user  
   - `RUN` instructions for the final user

4. `ENTRYPOINT` / `CMD` and profile labels

This ensures files and commands that must run as root happen first, while user-owned content and commands run only when the final user context is established.

If `chmod` or `user` is not specified `ADD` and `RUN` would be run by `root`.

## Common options

### Creating a container

```bash
tinkerbox container create [OPTIONS] IMAGE NAME
```

Useful flags:

- `--enter` / `-E` – enter immediately after creation
- `--profile` / `-P` – extra profiles to extend
- `--passthrough` / `-t` – host services: `x11`, `wayland`, `dbus`, `pulse`, `pipewire`, `gpu`, `all`
- `--volume` / `-v` – bind mounts or named volumes
- `--mount` / `-m` – additional filesystem mounts
- `--publish` / `-p` – port publishing
- `--device` / `-d` – host devices
- `--env` / `-e` – environment variables
- `--copy` / `-c` – copy files into the container at creation time
- `--exec` / `-x` – run commands during creation
- `--network` / `-n` – networking options
- `--override` – replace (instead of merge) inherited list/set/map options

Example with host directory sharing and display (still using the default profile’s home volume):

```bash
tinkerbox container create \
  --passthrough x11,wayland,pulse \
  --volume $HOME/projects:/home/$USER/projects:rw \
  my-debian devbox
```

### Building an image

```bash
tinkerbox image build [OPTIONS] NAME
```

Useful flags:

- `--from` / `-f` – base image
- `--pull` / `-p` – pull policy (`missing`, …)
- `--user` / `-u`, `--home` – user settings
- `--add` / `-a` – add files (host path, URL, or text)
- `--run` / `-r` – run commands during build (grouped by user as described above)
- `--env` / `-e` – environment variables
- `--profile` / `-P` – profiles to extend

## Persistent home & data (default profile)

With the default container profile a named volume `<container-name>-home` is mounted at `/home`. Recreating a container with the same name reuses the volume, so your files survive.

This is purely a feature of the default profile. Custom profiles can mount `/home` differently, use no volume at all, or place the home directory elsewhere.

## Display, audio, D-Bus, GPU

Pass host services with `--passthrough` (or configure them in a container profile):

```bash
tinkerbox container create -t x11,wayland,pulse,pipewire,dbus,gpu ...
```

## Running init / daemon scripts (default profile)

The default image entrypoint runs executable `~/init` scripts for both `root` and the container user (if present). Example workflow:

```bash
# Host
tinkerbox container create --publish 127.0.0.1:8000:8000 my-debian webdav
tinkerbox container enter webdav

# Inside container
sudo apt update && sudo apt install -y chezdav
echo 'chezdav --public --no-mdns -p 8000 -P $HOME &' > ~/init
chmod +x ~/init
exit

# Host
tinkerbox container stop webdav
tinkerbox container start webdav
# → service available on localhost:8000
```

Again, this behaviour comes from the default profiles; custom profiles can omit or replace the entrypoint.

## Development notes

This branch is a full rewrite in Python. See `REWRITE.md` for design notes, planned subcommands, and open TODOs (rebase/recreate, richer list output, timezone handling, etc.).

```bash
# Run from source
python -m tinkerbox ...
```

## License

MIT License – see [LICENSE](LICENSE).

