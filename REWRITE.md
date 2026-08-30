
## Subcommands

- [ ] profile
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
	- [ ] build
	- [ ] info
	- [ ] ls
	- [ ] profile - cat profile
	- [ ] rename
	- [ ] rm
	- [ ] tree
- [ ] container
	- [ ] commit
	- [ ] create
	- [ ] enter
	- [ ] info
	- [ ] ls
	- [ ] profile - cat profile
	- [ ] rebase
	- [ ] recreate
	- [ ] rm
	- [ ] start
	- [ ] stop
- [ ] volume
	- [ ] ls
	- [ ] rm
	- [ ] info

The option `profile` must take a name or afile path, maybe even url. There could be a generic function to read content from URI (resource|file|url).

## Notes
### Enter to container
```sh
podman exec -it -u ildar slivoglot-dev /bin/sh -c 'exec $(getent passwd $(whoami) | cut -d: -f7)'
```

`pw-dump` to get current pipewire socket name


### Gpu
Try `--gpus`.
