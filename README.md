# Tinkerbox

Tinkerbox is a tool for managing interactive [Podman](https://podman.io/) containers intended for experiments and development.

It is similar to [Toolbox](https://containertoolbx.org/) and [Distrobox](https://distrobox.it/), but does **not** share the host’s home directory or other filesystem paths by default. Containers stay isolated; persistence and host integration are controlled explicitly through profiles and CLI options.

**Status:** Work in progress / alpha, but usable.

## Features

- Isolated development environments (no automatic host directory sharing)
- Profile-based configuration (TOML/JSON) for images and containers
- Image building from standard OCI images using profiles, no need for specially prepared images
- Flexible mounts, volumes, devices, networks, port publishing, and file copying
- Optional host service passthrough (X11, Wayland, DBus, PulseAudio, PipeWire, GPU)
- Uses only standard python libraries, no external dependencies

The default profiles provide a ready-to-use experience (supported distros, persistent `/home` volume, init scripts, etc.). You can write your own profiles with completely different behaviour.

## Requirements

- Linux
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
| `enter` | `en` | Enter a container |
| `list` | `ls` | List containers |
| `remove` | `rm` | Remove one or more containers |
| `start` | `st` | Start containers |
| `stop` | `sp` | Stop containers |
| `profile` | `pr` | Manage container profiles (`list`, `cat`, `extract`) |

Run any command with `--help` for full options (e.g. `tinkerbox container create --help`).

## Profiles

Configuration is driven by **profiles** (TOML or JSON files). Profiles can extend others (`extends = ["default"]`). CLI flags can also supply or override profile data.

### Image profiles

Image profiles describe how to build a container image. They live under:

- `~/.config/tinkerbox/image/` (or `$XDG_CONFIG_HOME/tinkerbox/image/`)
- `/etc/tinkerbox/image/`
- there is built-in image profile `default` that can be overridden by placing a file `default.toml` or `default.json` to the profiles directory.

Files may be `name.toml` or `name.json`. Load/inspect with:

```bash
tinkerbox image profile list
tinkerbox image profile cat default
tinkerbox image profile cat --flatten default
tinkerbox image profile extract <image>
```

Profiles may **extend** others (`extends = ["default"]`). After loading, Tinkerbox **flattens** the chain (base first, then overrides), then applies **variable substitution** (`@{…}`) before building.

#### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable summary (documentation only). |
| `extends` | string or list of strings | Base profile name(s) to merge under this one. |
| `from` | string | Base image reference (Containerfile `FROM`). Example: `"debian"`, `"fedora:41"`. |
| `pull` | string | When to pull the base image. See [Pull policy](#pull-policy). |
| `name` | string | Image name. |
| `user` | string | Container user name. Defaults to the host username if omitted. |
| `home` | string | That user’s home directory. Defaults to the host home if omitted. |
| `environment` / `env` | map or list of `KEY=VAL` | Environment variables baked into the image. Values are substituted. |
| `add` | list of add entries | Files/content to copy into the image (see [Add entries](#add-entries)). |
| `run` | list of run entries | Commands to run during the build (see [Run entries](#run-entries)). |
| `entrypoint` | string or list of strings | Image `ENTRYPOINT`. |
| `cmd` | string or list of strings | Image `CMD`. |
| `override` | string or list of strings | When merging with a parent profile, replace (instead of append) the listed collections. See [Image's override](#images-override). |

String fields that support substitution include `from`, `name`, `user`, `home`, environment values, `entrypoint`, `cmd`, and the relevant fields inside `add` / `run`.

#### Pull policy

| Value | Aliases | Meaning |
|-------|---------|---------|
| `missing` | `m` | Pull only if the base image is not present locally (default). |
| `always` | `a` | Always pull. |
| `never` | `n` | Never pull. |
| `newer` | `u`, `update` | Pull if a newer image is available. |

#### Image's override

When this profile is merged on top of a parent, list fields normally **append**. `override` forces **replace** for the named parts:

| Value | Alias | Effect |
|-------|-------|--------|
| `all` | | Replace all of `add`, `run`, and `environment` from the parent. |
| `add` | `a` | Replace parent `add` list. |
| `run` | `r` | Replace parent `run` list. |
| `env` | `e` | Replace parent `environment` map (keys from the child win per key when not fully replaced—see merge rules in code: env keys from child override parent keys; with `env`/`all` override the parent map is not kept). |

Scalar fields (`from`, `name`, `user`, `home`, `entrypoint`, `cmd`, `pull`) are overwritten by the child whenever the child sets them.

#### Add entries

Each element of `add` is either a **string** (short form) or a **table/object**. The variant is chosen by which source field is present:

| Variant | Discriminator | Meaning |
|---------|---------------|---------|
| Host file | `source` (alias `src`) | Copy from a path on the build host. |
| URL | `url` | Fetch from a URL (including git-style sources where supported by the builder). |
| Inline text | `content` | Write a literal string as a file. |
| Built-in | `builtin` | Copy a file shipped inside the Tinkerbox package (e.g. bootstrap scripts). |

##### Common fields (all variants)

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `destination` | `dst` | string (path) | yes | Path inside the image. |
| `chmod` | | string | no | Mode (e.g. `"755"`). |
| `chown` | | string | no | File owner, such as `"root"` or another user name. If omitted or `null`, defaults to `root`. |

##### Host file (`source`)

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Host path (alias `src`). |
| `link` | bool | Prefer linking when supported. |
| `unpack` | bool | Unpack archives when supported. |
| `exclude` | list of strings | Paths to exclude. |

**String form** (CLI / compact profile):

```text
SOURCE
SOURCE:DESTINATION
SOURCE:DESTINATION:opt=value,opt2,...
```

If only `SOURCE` is given, destination defaults to the same path. Options use comma-separated `key` or `key=value` (including `link`, `unpack`, `exclude=…`, `chmod=…`, `chown=…`).

##### URL (`url`)

Same as host file for `link`, `unpack`, `exclude`, plus:

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Remote URL. |
| `keep-git-dir` | bool | Keep `.git` when fetching a git tree (if applicable). |
| `checksum` | string | Optional checksum verification. |

##### Text (`content`)

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | File body (substitution applied). |

##### Built-in (`builtin`)

| Field | Type | Description |
|-------|------|-------------|
| `builtin` | string | Resource name under Tinkerbox’s built-in files (e.g. `default-bootstrap.sh`). |

##### TOML examples

```toml
[[add]]
source = "./config/app.toml"
destination = "/etc/app/config.toml"
chown = "root"
chmod = "644"

[[add]]
url = "https://example.com/tool.tar.gz"
destination = "/opt/tool"
unpack = true

[[add]]
content = "hello @{CONTAINER_USER}\n"
destination = "/etc/motd"

[[add]]
builtin = "default-entrypoint.sh"
destination = "/usr/local/sbin/entrypoint.sh"
chown = "root"
chmod = "755"
```

During the build, `add` and `run` steps are **ordered by user**: root-owned adds and root runs first, then intermediate users, then the final image `user` (see image build logic). Prefer `chown` / `run.user` that match that model.

#### Run entries

Each element of `run` is a command executed while building the image (as root or another user).

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `command` | `cmd` | string or list of strings | yes | Command to run. A list is exec form (no shell); a string is a single argv element or shell form depending on builder usage—prefer list form for clarity. |
| `user` | | string | no | User to run as (e.g. `"root"`). Omitted/`null` means the implementation default for that phase; string form defaults to `root`. |
| `mount` | | object or list of objects | no | Extra mounts for this run (string key/value maps, passed through to the build runner). |
| `network` | | string | no | Network mode for this run. |
| `security` | | string | no | Security options for this run. |

**String form:**

```text
COMMAND
USER:COMMAND
USER:COMMAND:mount=type=bind,src=...,dst=...:network=host:security=...
```

##### TOML examples

```toml
[[run]]
command = ["/bin/sh", "/usr/local/sbin/bootstrap.sh"]
user = "root"

[[run]]
command = ["npm", "install", "-g", "yarn"]
user = "root"
```

#### Built-in default image profile (reference)

The shipped `default` image profile roughly:

- `from = "debian"`
- Sets `CONTAINER_UID` / `CONTAINER_GID` / `CONTAINER_USER` / `CONTAINER_HOME` from substitution variables
- Adds built-in `default-bootstrap.sh` and `default-entrypoint.sh` under `/usr/local/sbin/`
- Runs the bootstrap script as `root`
- Sets `cmd = ["sudo", "/usr/local/sbin/entrypoint.sh"]`

Supported bases called out for that default bootstrap path include Alpine, Arch, Debian, Fedora, openSUSE Tumbleweed, and Ubuntu; other images with a common package manager may work but are untested. Custom image profiles can use any `from` and need not use the default bootstrap at all.

#### Minimal custom image profile

```toml
## ~/.config/tinkerbox/image/dev.toml
description = "Debian-based dev image"
extends = ["default"]
from = "debian"

[[run]]
command = ["apt-get", "install", "-y", "git", "curl"]
user = "root"
```

```bash
tinkerbox image build my-dev -P dev
## or rely on profile name field if you pass name only via profile / CLI as implemented
```

Note: The final user is created by `bootstrap.sh` in `default` profile. If you do not extend your profile from the `default` you must add `[[run]]` command to create a user.

```toml
[[run]]
user="root"
command="useradd --create-home --uid @{UID} --home-dir @{CONTAINER_HOME} @{CONTAINER_USER}"
```

#### Related variables (image build)

When substituting an image profile, the following are available in addition to the host environment and base profile variables:

| Variable | Meaning |
|----------|---------|
| `UID` / `GID` | Host user/group ids |
| `CONTAINER_USER` | Profile `user`, or host username |
| `CONTAINER_HOME` | Profile `home`, or host home |
| `IMAGE_FROM` | Profile `from`, if set |
| `IMAGE_NAME` | Profile `name`, if set |
| `PROFILE_NAME` | Loaded profile name, if set |
| `TZ` | Host timezone when detectable |

See the [Variable substitution](#variable-substitution) section for `@{VAR}`, `@{VAR?}`, and `@{VAR:-default}` syntax.

### Container profiles

Container profiles describe how to create and run a container from an image.
They live under:

- `~/.config/tinkerbox/container/` (or `$XDG_CONFIG_HOME/tinkerbox/container/`)
- `/etc/tinkerbox/container/`
- built-in package data (`default`)

Files may be `name.toml` or `name.json`. Load/inspect with:

```bash
tinkerbox container profile list
tinkerbox container profile cat default
tinkerbox container profile cat --flatten default
tinkerbox container profile extract <container>
```

Profiles may **extend** others (`extends = ["default"]`). After loading, Tinkerbox **flattens** the chain, then applies **variable substitution** before create. When creating a container, variables from the **image** profile are merged with the container profile’s variables so image-side values such as `CONTAINER_USER` / `CONTAINER_HOME` are available.

#### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable summary. |
| `extends` | string or list of strings | Base container profile name(s) to merge under this one. |
| `name` | string | Container name. |
| `image` | string | Image name/reference to run. |
| `environment` / `env` | map or list of `KEY=VAL` | Environment variables set on the container. Values are substituted. |
| `pass_environment` | string or list of strings | Names of **host** environment variables to pass into the container when entering it, in addition to the explicitly configured `environment` variables baked into the container. |
| `passthrough` | string or list of strings | Host services to expose (display, audio, GPU, …). See [Passthrough](#passthrough). |
| `devices` | list | Host devices. See [Device](#device). |
| `mounts` | list | Podman `--mount` entries. See [Mount](#mount). |
| `volumes` | list | Podman `--volume` entries. See [Volume](#volume). |
| `networks` | list | Podman `--network` entries. See [Network](#network). |
| `publish` | list | Published ports. See [Publish](#publish). |
| `copy` | list | Files to copy into the container at create time. See [Copy](#copy). |
| `exec` | list | Commands to run inside the container at create time. See [Exec](#exec). |
| `enter_command` | string | Command used when entering the container (login shell selection, etc.). |
| `override` | string or list of strings | When merging with a parent, replace (instead of append/union) the listed collections. See [Container's override](#containers-override). |

#### Passthrough

Set of host integrations to enable. Values (and short aliases):

| Value | Alias | Meaning |
|-------|-------|---------|
| `all` | `a` | All supported passthroughs. |
| `x11` | `x` | X11 display. |
| `wayland` | `w` | Wayland display. |
| `pulse` | `pa` | PulseAudio. |
| `pipewire` | `pw` | PipeWire. |
| `gpu` | `g` | GPU devices / access. |
| `dbus` | `b` | D-Bus. |

Example:

```toml
passthrough = ["x11", "wayland", "pulse"]
## or
passthrough = "x11,wayland,pulse"
```

Exact mounts/sockets applied for each flag are implemented at create time (not plain profile fields).

#### Device

Maps to Podman `--device=HOST[:CONTAINER][:PERMISSIONS]`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host_device` | string | yes | Path on the host (e.g. `/dev/dri`). |
| `container_device` | string | no | Path inside the container; defaults to the host path when omitted in the argument form. |
| `permissions` | string or list | no | Subset of `r` (read), `w` (write), `m` (mknod). A compact string such as `"rwm"` is accepted. |

**String form:** `host-device[:container-device][:permissions]`

```toml
[[devices]]
host_device = "/dev/dri"
container_device = "/dev/dri"
permissions = ["r", "w", "m"]
```

#### Mount

Opaque Podman `--mount` specification. Required field `type`; every other key is passed through as a mount option (Podman accepts e.g. `source`/`src`, `destination`/`dst`/`target`, `tmpfs-size`, `ro`, …).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | yes | Mount type: `bind`, `volume`, `tmpfs`, `image`, … |
| *(any other keys)* | string, bool, or null | no | Type-specific options, forwarded to `--mount`. |

**String forms:**

```text
type=TYPE,option=value,...
TYPE:option=value,...
```

Boolean-style flags may appear as bare keys (`ro`) and are stored as true.

```toml
[[mounts]]
type = "tmpfs"
destination = "/tmp"
tmpfs-size = "5g"

[[mounts]]
type = "bind"
source = "/var/data"
destination = "/data"
ro = true
```

Option **values** that are strings are subject to variable substitution; keys are not rewritten (Podman synonyms such as `dst` vs `destination` are left as written).

#### Volume

Maps to Podman `--volume=[SOURCE:]TARGET[:OPTIONS]`.

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `target` | `tgt` | string | yes | Path inside the container. |
| `source` | `src` | string | no | Host path or named volume. |
| `options` | | string or list of strings | no | Comma-separated options (`rw`, `ro`, `z`, …). |

**String form:** `[SOURCE:]TARGET[:OPTIONS]`

```toml
[[volumes]]
source = "@{CONTAINER_NAME}-home"
target = "/home"

[[volumes]]
source = "/home/me/work"
target = "/work"
options = ["rw"]
```

#### Network

Maps to Podman `--network=MODE[:OPTIONS]`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | yes | Network mode or network name (e.g. `bridge`, `host`, `none`, or a custom network). |
| *(any other keys)* | string or null | no | Mode-specific options (`alias=…`, etc.), forwarded to `--network`. |

**String form:** `MODE` or `MODE:opt=value,opt2,...`

```toml
[[networks]]
mode = "bridge"

[[networks]]
mode = "mynet"
alias = "web"
```

#### Publish

Maps to Podman `-p` / `--publish`.

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `container_port` | `port` | int, range string, or object | yes | Container port or range. |
| `host_port` | | int, range string, or object | no | Host port or range. |
| `ip` | | string | no | Host IP to bind. |
| `protocol` | | `"tcp"` or `"udp"` | no | Protocol. |

Port ranges may be written as `"8000-8010"` or `{ start = 8000, end = 8010 }`.

**String form:** `[[IP:][HOSTPORT]:]CONTAINER_PORT[/PROTOCOL]`  
(as accepted by the parser’s colon-splitting rules)

```toml
[[publish]]
container_port = 8000
host_port = 8000
ip = "127.0.0.1"
protocol = "tcp"

[[publish]]
port = "9000-9010"
protocol = "udp"
```

#### Copy

Copy files into the container when it is created (from the host or from another container).

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `source` | `src` | string | yes | Path to copy from. |
| `destination` | `dst` | string | no | Path inside the target container; if omitted, destination is the same as source. |
| `source_container` | `container` | string | no | If set, `source` is read from this container instead of the host. |
| `ignore_failure` | | bool | no | Do not fail create if the copy fails (default `false`). |

**String form:** `[SRC_CONTAINER:]SOURCE[:DESTINATION]`

```toml
[[copy]]
source = "./config/app.toml"
destination = "/etc/app/config.toml"

[[copy]]
source_container = "otherbox"
source = "/var/data"
destination = "/var/data"
```

#### Exec

Commands executed inside the container during create (after the container exists).

| Field | Aliases | Type | Required | Description |
|-------|---------|------|----------|-------------|
| `command` | `cmd` | string or list of strings | yes | Command to run. Prefer list (exec) form. |
| `user` | | string | no | User to run as. |
| `work_dir` | | string | no | Working directory inside the container. |
| `ignore_failure` | | bool | no | Do not fail create if the command fails (default `false`). |

**String form:** `[USER:[WORK_DIR:]]COMMAND`

```toml
[[exec]]
command = ["systemctl", "--user", "daemon-reload"]
user = "@{CONTAINER_USER}"
```

#### Container's override

When this profile is merged on top of a parent, list/set fields normally **append** or **union**. `override` forces **replace** for the named parts:

| Value | Alias | Replaces parent … |
|-------|-------|-------------------|
| `all` | | all collections below |
| `devices` | `d` | `devices` |
| `env` | `e` | `environment` |
| `pass-env` | `E` | `pass_environment` |
| `mounts` | `m` | `mounts` |
| `networks` | `n` | `networks` |
| `publish` | `p` | `publish` |
| `passthrough` | `s` | `passthrough` |
| `volumes` | `v` | `volumes` |
| `copy` | `c` | `copy` |
| `exec` | `x` | `exec` |

Scalars such as `name`, `image`, and `enter_command` are overwritten by the child whenever the child sets them. `passthrough` is a set: without override it is the union of parent and child.

#### Built-in default container profile (reference)

The shipped `default` container profile roughly:

- Sets `enter_command` to start the user’s login shell via `getent passwd`
- Passes common host env names (`TERM`, `DISPLAY`, `XDG_*`, …) via `pass_environment`
- Sets `HOME` / `USER` / `TZ` from substitution (`@{CONTAINER_HOME}`, `@{CONTAINER_USER}`, `@{TZ?}`)
- Mounts tmpfs on `/tmp` and `/run`
- Mounts named volume `@{CONTAINER_NAME}-home` at `/home`

Those behaviours are **not** hard-wired into the tool; they come from this profile. Custom profiles can omit the home volume, change init/enter behaviour, or use a different layout.

#### Minimal custom container profile

```toml
## ~/.config/tinkerbox/container/web.toml
description = "Web service box"
extends = ["default"]
passthrough = ["x11"]

[[publish]]
container_port = 8080
host_port = 8080
ip = "127.0.0.1"

[[volumes]]
source = "/home/me/src/project"
target = "/home/@{CONTAINER_USER}/project"
options = ["rw"]
```

```bash
tinkerbox container create -P web my-debian web
## CLI image/name still apply according to the create command; profile supplies the rest
```

#### Related variables (container create)

Container profile substitution includes the base set (host environment, `PROFILE_NAME`, `TZ`, …) plus:

| Variable | Meaning |
|----------|---------|
| `CONTAINER_NAME` | Profile `name`, if set |
| `CONTAINER_IMAGE` | Image name the container built from |

On create, variables from the **image** profile are merged in as well (e.g. `UID`, `GID`, `CONTAINER_USER`, `CONTAINER_HOME`, `IMAGE_FROM`, `IMAGE_NAME`), so default container env like `HOME = "@{CONTAINER_HOME}"` resolves correctly.

See [Variable substitution](#variable-substitution) for `@{VAR}`, `@{VAR?}`, and `@{VAR:-default}`.

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

# Nested / recursive expansion
home = "@{HOME}" # value would be assigned to `@{CONTAINER_HOME}`
environment = { PATH = "@{PATH}:@{CONTAINER_HOME}/.local/bin" }
```

Required variable that is missing:

```toml
# Raises ValueError: variable 'MISSING' is not defined
source = "@{MISSING}"
```

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

### Building an image

```bash
tinkerbox image build [OPTIONS] NAME
```

Useful flags:

- `--from` / `-f` – base image
- `--pull` / `-p` – pull policy (`missing`, …)
- `--user` / `-u`, `--home` – user settings
- `--add` / `-a` – add files (host path)
- `--run` / `-r` – run commands during build
- `--env` / `-e` – environment variables
- `--profile` / `-P` – profiles to extend

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
  --volume $HOME/projects:@{CONTAINER_HOME}/projects:rw \
  my-debian devbox
```


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

The old version written as a fish script available in the `fish` branch.

```bash
# Run from source
python -m tinkerbox ...
```

## License

MIT License – see [LICENSE](LICENSE).

