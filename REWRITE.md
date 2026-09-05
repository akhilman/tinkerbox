
## Subcommands
- [ ] ~~profile~~ move to image/container
	- [ ] container
		- [ ] ls
		- [ ] cat
	- [ ] image
		- [x] ls
		- [x] cat
		- [ ] ~~create~~
		- [ ] ~~edit~~
		- [ ] ~~rm~~
		- [ ] ~~rename~~
- [ ] image
	- [x] build
	- [ ] info
	- [ ] ls
	- [ ] rename
	- [ ] rm
	- [ ] tree
	- [ ] profile
		- [ ] ls
		- [ ] cat
		- [ ] extract <- same as cat, but dumps profile from image
- [ ] container
	- [ ] commit
	- [ ] create
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
		- [ ] ls
		- [ ] cat
		- [ ] dump <- same as cat, but dumps profile from image
- [ ] volume
	- [ ] ls
	- [ ] rm
	- [ ] info
- [ ] run <image> <command> - run task in ephemeral container and delete it immediately

Make container name in `container create` optional and use image name instead.

The option `profile` must take a name or a file path, maybe even url. There could be a generic function to read content from URI (resource|file|url).

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