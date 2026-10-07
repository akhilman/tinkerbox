## TODO
- [x] Update container timezone (see below).
- [ ] Add `--pull` to `image build`.
- [ ] Add `--replace` to `container create`.
- [ ] Add `--enter` to `container create` and stop container after creation if `--enter` is not specified.
- [ ] Make image name in `image build` optional.
- [ ] Make container name in `container create` optional.
- [ ] The option `profile` must take a name or a file path, maybe even url. There could be a generic function to read content from URI (resource|file|url).
- [ ] Expand `~` to the actual home path inside containers for the image's copy option.
- [ ] Add `ignore_failure` to container's exec option.
- [ ] Add `ignore_missing` to container's copy option.
- [ ] Deduplicate volumes and mounts.
- [ ] Support env variable expansion like `PATH=@{PATH}:/foo`, and then `PATH=@{PATH}:/bar`.
- [ ] Do we need `random_string` from `utils.py`?

### Subcommands
- [ ] image
	- [x] build
	- [ ] info
	- [x] ls
	- [ ] rename
	- [ ] rm
	- [ ] tree
	- [ ] profile
		- [x] ls
		- [x] cat
		- [x] extract - same as cat, but dumps profile from image
- [ ] container
	- [ ] commit
	- [x] create
	- [ ] enter
	- [ ] exec - executes single command in chosen container
	- [ ] info
	- [x] ls
	- [ ] rebase
	- [ ] recreate
	- [ ] rm
	- [ ] start
	- [ ] stop
	- [ ] profile
		- [x] ls
		- [x] cat
		- [x] extract - same as cat, but dumps profile from image
- [ ] volume
	- [ ] ls
	- [ ] rm
	- [ ] info
- [ ] create - shortcut to build an image and create an container with less control using only container profile (maybe use untagged images)
- [ ] ls - list containers and volumes
- [ ] upgrade - update an image and rebase the container, works only with containers without customized images
- [ ] stop - alias for container stop
- [ ] enter - alias for container enter
- [ ] rm - removes the container and removes the image if it is not customized and not used anywhere else


## Notes
### Enter to container
```sh
podman exec -it -u ildar slivoglot-dev /bin/sh -c 'exec $(getent passwd $(whoami) | cut -d: -f7)'
```

### Rebase and Recreate
Rebase steps:

- Create a new container.
- Copy /home/ with `--archive` excluding all volumes mounted in original container.
- Re-tag the new container to replace old one.

Do not allow rebase if:

- old container has a file or directory (not mountpoint) with same name as mountpoint in new container;
- mounted volume is not new named volume (potentially non empty).

Fail with an error and ask a user to rename files in the old container.

If the new container has a new or empty mountpoint in place of directory in the old one – just copy files from the old container to the volume/mountpoint.


### Passthrough
- Try `--gpus`.
- Try `pw-dump` to get current pipewire socket name

### Timezone

```
import os

def get_timezone_flags() -> list[str]:
    flags = []
    
    # 1. Проверяем и пробрасываем /etc/localtime (работает на всех дистрибутивах)
    if os.path.exists("/etc/localtime"):
        flags.extend(["-v", "/etc/localtime:/etc/localtime:ro"])
        
    # 2. Проверяем и пробрасываем /etc/timezone (нужно для Debian/Ubuntu образов)
    if os.path.exists("/etc/timezone"):
        flags.extend(["-v", "/etc/timezone:/etc/timezone:ro"])
        
    return flags
```

or

```
import os
import time

def get_timezone_env() -> list[str]:
    # time.tzname вернет системное имя таймзоны хоста (например, 'MSK' или 'UTC')
    # Но для Linux надежнее прочитать симлинк /etc/localtime, если он есть
    try:
        # Извлекаем что-то вроде "Europe/Moscow" из симлинка
        tz_path = os.readlink("/etc/localtime")
        tz_name = "/".join(tz_path.split("/")[-2:])
        return ["-e", f"TZ={tz_name}"]
    except Exception:
        # Фолбэк на стандартную переменную хоста или UTC
        tz_name = os.environ.get("TZ", "UTC")
        return ["-e", f"TZ={tz_name}"]
```

