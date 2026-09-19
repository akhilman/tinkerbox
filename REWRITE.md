## TODO
- [ ] Update container timezone.
- [ ] Add `--pull` to `image build`.
- [ ] Add `--replace` to `container create`.
- [ ] Make container name in `container create` optional and use image name instead.
- [ ] The option `profile` must take a name or a file path, maybe even url. There could be a generic function to read content from URI (resource|file|url).
- [ ] Expand `~` to the actual home path inside containers for the image's copy option.

### Subcommands
- [ ] image
	- [x] build
	- [ ] info
	- [ ] ls
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
	- [ ] ls
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
