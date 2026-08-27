
## Subcommands

- [ ] container
	- [ ] create
	- [ ] recreate
	- [ ] run
	- [ ] stop
	- [ ] rm
	- [ ] ls
	- [ ] commit
	- [ ] dump profile
	- [ ] show
- [ ] profile
	- [x] ls
	- [x] cat
	- [ ] ~~create~~
	- [ ] ~~edit~~
	- [ ] ~~rm~~
	- [ ] ~~rename~~
- [ ] volume
	- [ ] ls
	- [ ] rm
	- [ ] show
- [ ] image
	- [ ] build
	- [ ] ls
	- [ ] rm
	- [ ] tree
	- [ ] rename

The option `profile` must take a name or afile path, maybe even url. There could be a generic function to read content from URI (resource|file|url).

## Notes
### Enter to container
```sh
podman exec -it -u ildar slivoglot-dev /bin/sh -c 'exec $(getent passwd $(whoami) | cut -d: -f7)'
```

`pw-dump` to get current pipewire socket name


### Gpu
Try `--gpus`.
